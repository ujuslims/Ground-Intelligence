"""Borehole / stratigraphy / SPT / CPT / groundwater / lab CRUD."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.geotech import (
    Borehole, BoreholeStratum, SPT, CPT, CPTReading, Sample, LaboratoryResult, GroundwaterObservation,
)
from app.schemas.core import (
    BoreholeCreate, BoreholeOut, StratumCreate, StratumOut, SPTCreate, SPTOut,
    CPTCreate, CPTOut, CPTImportRequest, CPTReadingOut,
    GroundwaterCreate, GroundwaterOut, SampleCreate, SampleOut, LabResultCreate, LabResultOut,
)
from app.services.audit import log_event
from app.services.cpt_validation import validate_cpt_readings

router = APIRouter(prefix="/api", tags=["geotech"])


# ---- Borehole ----
@router.post("/boreholes", response_model=BoreholeOut)
def create_borehole(payload: BoreholeCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bh = Borehole(**payload.model_dump(), created_by=user.id)
    db.add(bh)
    db.commit()
    db.refresh(bh)
    log_event(db, user_id=user.id, action="BOREHOLE_CREATED", object_type="BOREHOLE", object_id=bh.id)
    return bh


@router.get("/locations/{location_id}/boreholes", response_model=list[BoreholeOut])
def list_boreholes(location_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Borehole).filter_by(location_id=location_id).all()


@router.post("/boreholes/{borehole_id}/strata", response_model=StratumOut)
def add_stratum(borehole_id: str, payload: StratumCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.borehole_id != borehole_id:
        raise HTTPException(400, "borehole_id mismatch")
    stratum = BoreholeStratum(**payload.model_dump(), created_by=user.id)
    db.add(stratum)
    db.commit()
    db.refresh(stratum)
    log_event(db, user_id=user.id, action="STRATUM_ADDED", object_type="BOREHOLE_STRATUM", object_id=stratum.id)
    return stratum


@router.get("/boreholes/{borehole_id}/strata", response_model=list[StratumOut])
def list_strata(borehole_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(BoreholeStratum).filter_by(borehole_id=borehole_id).order_by(BoreholeStratum.depth_from).all()


@router.post("/boreholes/{borehole_id}/spt", response_model=SPTOut)
def add_spt(borehole_id: str, payload: SPTCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Observational-only per Rev 2 Amendment 1 -- n_value is stored exactly as
    recorded. No energy/overburden/rod correction is applied or inferred."""
    if payload.borehole_id != borehole_id:
        raise HTTPException(400, "borehole_id mismatch")
    spt = SPT(**payload.model_dump(), created_by=user.id)
    db.add(spt)
    db.commit()
    db.refresh(spt)
    log_event(db, user_id=user.id, action="SPT_ADDED", object_type="SPT", object_id=spt.id)
    return spt


# ---- CPT ----
@router.post("/cpts", response_model=CPTOut)
def create_cpt(payload: CPTCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cpt = CPT(**payload.model_dump(), created_by=user.id)
    db.add(cpt)
    db.commit()
    db.refresh(cpt)
    log_event(db, user_id=user.id, action="CPT_CREATED", object_type="CPT", object_id=cpt.id)
    return cpt


@router.get("/locations/{location_id}/cpts", response_model=list[CPTOut])
def list_cpts(location_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(CPT).filter_by(location_id=location_id).all()


@router.post("/cpts/{cpt_id}/import")
def import_cpt_readings(cpt_id: str, payload: CPTImportRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    CPT import/validation pipeline (Tech Spec §17): missing required columns,
    non-numeric values, missing/duplicate depth, invalid depth ordering,
    missing qc/fs/u2, invalid coordinates and unit inconsistencies are all
    checked BEFORE any row is written. Invalid data is never silently
    converted to valid data -- the import is rejected wholesale with the
    specific errors, and the caller must resubmit corrected data.
    """
    cpt = db.get(CPT, cpt_id)
    if not cpt:
        raise HTTPException(404, "CPT not found")

    errors = validate_cpt_readings(payload.readings)
    if errors:
        raise HTTPException(422, {"message": "CPT validation failed", "errors": errors})

    for r in payload.readings:
        db.add(CPTReading(cpt_id=cpt_id, depth=r.depth, qc=r.qc, fs=r.fs, u2=r.u2))
    cpt.version += 1
    cpt.status = "VALIDATED"
    db.commit()
    log_event(db, user_id=user.id, action="CPT_IMPORTED", object_type="CPT", object_id=cpt_id,
              metadata={"reading_count": len(payload.readings)})
    return {"imported": len(payload.readings), "cpt_version": cpt.version}


@router.get("/cpts/{cpt_id}/readings", response_model=list[CPTReadingOut])
def get_cpt_readings(cpt_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Depth-ordered readings, ready for qc-vs-depth / fs-vs-depth / friction-
    ratio plotting on the frontend (Tech Spec §18)."""
    return db.query(CPTReading).filter_by(cpt_id=cpt_id).order_by(CPTReading.depth).all()


# ---- Groundwater ----
@router.post("/groundwater", response_model=GroundwaterOut)
def add_groundwater(payload: GroundwaterCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    gw = GroundwaterObservation(**payload.model_dump(), created_by=user.id)
    db.add(gw)
    db.commit()
    db.refresh(gw)
    log_event(db, user_id=user.id, action="GROUNDWATER_OBSERVATION_ADDED", object_type="GROUNDWATER_OBSERVATION", object_id=gw.id)
    return gw


@router.get("/locations/{location_id}/groundwater", response_model=list[GroundwaterOut])
def list_groundwater(location_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(GroundwaterObservation).filter_by(location_id=location_id).order_by(GroundwaterObservation.observation_date).all()


# ---- Laboratory (Path B -- externally processed summary import, MVP priority) ----
@router.post("/samples", response_model=SampleOut)
def create_sample(payload: SampleCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sample = Sample(**payload.model_dump(), created_by=user.id)
    db.add(sample)
    db.commit()
    db.refresh(sample)
    log_event(db, user_id=user.id, action="SAMPLE_CREATED", object_type="SAMPLE", object_id=sample.id)
    return sample


@router.post("/laboratory-results", response_model=LabResultOut)
def add_lab_result(payload: LabResultCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    MVP result types (Tech Spec §21): MOISTURE_CONTENT, LIQUID_LIMIT,
    PLASTIC_LIMIT, PLASTICITY_INDEX, PARTICLE_SIZE_DISTRIBUTION, CBR.
    Default status is IMPORTED (Path B) -- the system must never claim Ground
    Intelligence calculated a result it only imported (Tech Spec §22).
    """
    result = LaboratoryResult(**payload.model_dump(), created_by=user.id)
    db.add(result)
    db.commit()
    db.refresh(result)
    log_event(db, user_id=user.id, action="LAB_RESULT_ADDED", object_type="LABORATORY_RESULT", object_id=result.id)
    return result


@router.get("/samples/{sample_id}/laboratory-results", response_model=list[LabResultOut])
def list_lab_results(sample_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(LaboratoryResult).filter_by(sample_id=sample_id).all()
