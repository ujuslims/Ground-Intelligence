from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.investigation import Investigation, InvestigationLocation
from app.schemas.core import InvestigationCreate, InvestigationOut, LocationCreate, LocationOut
from app.services.audit import log_event

router = APIRouter(prefix="/api", tags=["investigations"])


@router.get("/projects/{project_id}/investigations", response_model=list[InvestigationOut])
def list_investigations(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Investigation).filter_by(project_id=project_id).all()


@router.post("/investigations", response_model=InvestigationOut)
def create_investigation(payload: InvestigationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inv = Investigation(**payload.model_dump(), created_by=user.id)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    log_event(db, user_id=user.id, action="INVESTIGATION_CREATED", object_type="INVESTIGATION", object_id=inv.id)
    return inv


@router.get("/projects/{project_id}/locations", response_model=list[LocationOut])
def list_locations(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Drives the GIS/project map -- one common InvestigationLocation query
    regardless of discipline (Tech Spec §13, §48)."""
    return db.query(InvestigationLocation).filter_by(project_id=project_id).all()


@router.post("/locations", response_model=LocationOut)
def create_location(payload: LocationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    loc = InvestigationLocation(**payload.model_dump(), created_by=user.id)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    log_event(db, user_id=user.id, action="LOCATION_CREATED", object_type="INVESTIGATION_LOCATION", object_id=loc.id)
    return loc
