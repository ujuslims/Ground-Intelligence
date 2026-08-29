"""
File-upload + column-mapping import wizard endpoints (Tech Spec §17/§20
pipeline). Two-step flow, matching the mandated "user confirmation" gate:

  1. POST .../inspect  -- upload the raw file, store it (provenance artifact,
     versioned in S3), and return detected columns + a heuristic proposed
     mapping + a preview. Writes NO CPTReading/LaboratoryResult rows yet.
  2. POST .../confirm   -- caller supplies the file_id from step 1 plus a
     mapping (the proposed one, or the user's corrected version). Re-reads
     the stored file, parses with that exact mapping, validates, and only
     then imports. Returns row-level errors and imports nothing if the
     required columns are unmapped.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.authz import require_project_access
from app.models.identity import User
from app.models.files import File as FileModel, Dataset
from app.models.geotech import CPT, CPTReading, Sample, LaboratoryResult
from app.schemas.ingestion import InspectResponse, ConfirmImportRequest, ImportResultResponse
from app.services.audit import log_event
from app.services.storage import get_storage_service
from app.services.ingestion import inspect_cpt_csv, inspect_lab_csv, parse_cpt_csv, parse_lab_csv
from app.services.cpt_validation import validate_cpt_readings
from app.schemas.core import CPTReadingIn

router = APIRouter(prefix="/api", tags=["ingestion"])


def _store_upload(db: Session, *, project_id: str, upload: UploadFile, content: bytes, user_id: str) -> FileModel:
    storage_service = get_storage_service()
    storage_service.ensure_bucket()
    key, version_id = storage_service.put_object(
        project_id=project_id, filename=upload.filename, content=content, content_type=upload.content_type,
    )
    file_row = FileModel(
        project_id=project_id, filename=upload.filename, storage_key=key,
        content_type=upload.content_type, size_bytes=len(content),
        storage_version_id=version_id, uploaded_by=user_id,
    )
    db.add(file_row)
    db.commit()
    db.refresh(file_row)
    return file_row


# ---- CPT ----
@router.post("/cpts/{cpt_id}/import-file/inspect", response_model=InspectResponse)
async def inspect_cpt_file(cpt_id: str, project_id: str, upload: UploadFile = FastAPIFile(...),
                            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cpt = db.get(CPT, cpt_id)
    if not cpt:
        raise HTTPException(404, "CPT not found")
    require_project_access(db, user, project_id)

    content = await upload.read()
    file_row = _store_upload(db, project_id=project_id, upload=upload, content=content, user_id=user.id)
    log_event(db, user_id=user.id, action="FILE_UPLOADED", object_type="FILE", object_id=file_row.id,
              metadata={"purpose": "CPT_IMPORT", "cpt_id": cpt_id})

    result = inspect_cpt_csv(content)
    return InspectResponse(file_id=file_row.id, columns=result.columns, preview_rows=result.preview_rows,
                            proposed_mapping=result.proposed_mapping, row_count=result.row_count)


@router.post("/cpts/{cpt_id}/import-file/confirm", response_model=ImportResultResponse)
def confirm_cpt_import(cpt_id: str, payload: ConfirmImportRequest, project_id: str,
                        db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cpt = db.get(CPT, cpt_id)
    if not cpt:
        raise HTTPException(404, "CPT not found")
    require_project_access(db, user, project_id)
    file_row = db.get(FileModel, payload.file_id)
    if not file_row:
        raise HTTPException(404, "Uploaded file not found")

    content = get_storage_service().get_object(file_row.storage_key, file_row.storage_version_id)
    parsed = parse_cpt_csv(content, payload.mapping)
    if parsed.errors:
        return ImportResultResponse(imported=0, errors=parsed.errors)

    readings = [CPTReadingIn(**r) for r in parsed.rows]
    validation_errors = validate_cpt_readings(readings)
    if validation_errors:
        return ImportResultResponse(imported=0, errors=validation_errors)

    dataset = Dataset(
        project_id=project_id, source_type="EXTERNAL_THIRD_PARTY", source_file_id=file_row.id,
        method="CSV_COLUMN_MAPPING_IMPORT", processing_status="PROCESSED", validation_status="VALIDATED",
        approval_status="UNAPPROVED", created_by=user.id,
    )
    db.add(dataset)
    db.flush()

    for r in readings:
        db.add(CPTReading(cpt_id=cpt_id, depth=r.depth, qc=r.qc, fs=r.fs, u2=r.u2))
    cpt.dataset_id = dataset.id
    cpt.version += 1
    cpt.status = "VALIDATED"
    db.commit()

    log_event(db, user_id=user.id, action="CPT_IMPORTED", object_type="CPT", object_id=cpt_id,
              metadata={"reading_count": len(readings), "dataset_id": dataset.id, "file_id": file_row.id})
    return ImportResultResponse(imported=len(readings), errors=[], dataset_id=dataset.id)


# ---- Laboratory ----
@router.post("/laboratory/import-file/inspect", response_model=InspectResponse)
async def inspect_lab_file(project_id: str, upload: UploadFile = FastAPIFile(...),
                            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_project_access(db, user, project_id)
    content = await upload.read()
    file_row = _store_upload(db, project_id=project_id, upload=upload, content=content, user_id=user.id)
    log_event(db, user_id=user.id, action="FILE_UPLOADED", object_type="FILE", object_id=file_row.id,
              metadata={"purpose": "LAB_IMPORT"})

    result = inspect_lab_csv(content)
    return InspectResponse(file_id=file_row.id, columns=result.columns, preview_rows=result.preview_rows,
                            proposed_mapping=result.proposed_mapping, row_count=result.row_count)


@router.post("/laboratory/import-file/confirm", response_model=ImportResultResponse)
def confirm_lab_import(payload: ConfirmImportRequest, project_id: str,
                        db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Matches rows to existing Sample records by sample_id_label (Tech Spec's
    "sample matching" step). Unmatched sample labels are reported as errors
    and nothing for that row is imported -- the pipeline does not silently
    create a placeholder Sample just to force an import through.
    """
    require_project_access(db, user, project_id)
    file_row = db.get(FileModel, payload.file_id)
    if not file_row:
        raise HTTPException(404, "Uploaded file not found")

    content = get_storage_service().get_object(file_row.storage_key, file_row.storage_version_id)
    parsed = parse_lab_csv(content, payload.mapping)
    if parsed.errors:
        return ImportResultResponse(imported=0, errors=parsed.errors)

    dataset = Dataset(
        project_id=project_id, source_type="PIGL_INTERNAL_EXTERNAL_PROCESSING", source_file_id=file_row.id,
        method="CSV_COLUMN_MAPPING_IMPORT", processing_status="PROCESSED", validation_status="VALIDATED",
        approval_status="UNAPPROVED", created_by=user.id,
    )
    db.add(dataset)
    db.flush()

    imported = 0
    errors: list[str] = []
    for i, row in enumerate(parsed.rows):
        sample = db.query(Sample).filter_by(sample_id_label=row["sample_id_label"]).first()
        if not sample:
            errors.append(f"Row {i}: no matching Sample found for label '{row['sample_id_label']}'.")
            continue
        db.add(LaboratoryResult(
            sample_id=sample.id, dataset_id=dataset.id, result_type=row["result_type"],
            value=row["value"], unit=row["unit"], source="PIGL_INTERNAL_EXTERNAL_PROCESSING",
            status="IMPORTED", created_by=user.id,
        ))
        imported += 1

    db.commit()
    log_event(db, user_id=user.id, action="LAB_RESULTS_IMPORTED", object_type="DATASET", object_id=dataset.id,
              metadata={"imported": imported, "errors": len(errors), "file_id": file_row.id})
    return ImportResultResponse(imported=imported, errors=errors, dataset_id=dataset.id)
