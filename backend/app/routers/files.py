from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.authz import require_project_access
from app.models.identity import User
from app.models.files import File, Dataset
from app.services.audit import log_event
from app.services.storage import get_storage_service

router = APIRouter(prefix="/api", tags=["files"])


@router.post("/projects/{project_id}/files")
async def upload_file(project_id: str, upload: UploadFile = FastAPIFile(...),
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_project_access(db, user, project_id)
    content = await upload.read()
    storage_service = get_storage_service()
    storage_service.ensure_bucket()
    key, version_id = storage_service.put_object(
        project_id=project_id, filename=upload.filename, content=content, content_type=upload.content_type,
    )
    file_row = File(
        project_id=project_id,
        filename=upload.filename,
        storage_key=key,
        content_type=upload.content_type,
        size_bytes=len(content),
        storage_version_id=version_id,
        uploaded_by=user.id,
    )
    db.add(file_row)
    db.commit()
    db.refresh(file_row)
    log_event(db, user_id=user.id, action="FILE_UPLOADED", object_type="FILE", object_id=file_row.id,
              metadata={"filename": upload.filename, "size_bytes": len(content)})
    return {"id": file_row.id, "filename": file_row.filename, "size_bytes": file_row.size_bytes}


@router.get("/files/{file_id}/download-url")
def get_download_url(file_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    file_row = db.get(File, file_id)
    if not file_row:
        raise HTTPException(404, "File not found")
    require_project_access(db, user, file_row.project_id)
    return {"url": get_storage_service().presigned_url(file_row.storage_key)}
