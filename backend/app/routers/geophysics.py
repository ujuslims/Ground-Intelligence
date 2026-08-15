from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.geophysics import VES, VESReading, VESLayer
from app.schemas.core import VESCreate, VESOut, VESReadingIn, VESLayerCreate, VESLayerOut
from app.services.audit import log_event

router = APIRouter(prefix="/api", tags=["geophysics"])


@router.post("/ves", response_model=VESOut)
def create_ves(payload: VESCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ves = VES(**payload.model_dump(), created_by=user.id)
    db.add(ves)
    db.commit()
    db.refresh(ves)
    log_event(db, user_id=user.id, action="VES_CREATED", object_type="VES", object_id=ves.id)
    return ves


@router.get("/locations/{location_id}/ves", response_model=list[VESOut])
def list_ves(location_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(VES).filter_by(location_id=location_id).all()


@router.post("/ves/{ves_id}/readings")
def import_ves_readings(ves_id: str, readings: list[VESReadingIn], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ves = db.get(VES, ves_id)
    if not ves:
        raise HTTPException(404, "VES survey not found")
    for r in readings:
        db.add(VESReading(ves_id=ves_id, electrode_spacing=r.electrode_spacing, apparent_resistivity=r.apparent_resistivity))
    ves.version += 1
    db.commit()
    log_event(db, user_id=user.id, action="VES_READINGS_IMPORTED", object_type="VES", object_id=ves_id,
              metadata={"reading_count": len(readings)})
    return {"imported": len(readings)}


@router.get("/ves/{ves_id}/readings")
def get_ves_readings(ves_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(VESReading).filter_by(ves_id=ves_id).order_by(VESReading.electrode_spacing).all()
    return [{"electrode_spacing": r.electrode_spacing, "apparent_resistivity": r.apparent_resistivity} for r in rows]


@router.post("/ves/{ves_id}/layers", response_model=VESLayerOut)
def add_ves_layer(ves_id: str, payload: VESLayerCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.ves_id != ves_id:
        raise HTTPException(400, "ves_id mismatch")
    layer = VESLayer(**payload.model_dump(), created_by=user.id)
    db.add(layer)
    ves = db.get(VES, ves_id)
    if ves:
        ves.interpretation_status = "INTERPRETED"
    db.commit()
    db.refresh(layer)
    log_event(db, user_id=user.id, action="VES_LAYER_ADDED", object_type="VES_LAYER", object_id=layer.id)
    return layer


@router.get("/ves/{ves_id}/layers", response_model=list[VESLayerOut])
def list_ves_layers(ves_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(VESLayer).filter_by(ves_id=ves_id).order_by(VESLayer.layer_number).all()
