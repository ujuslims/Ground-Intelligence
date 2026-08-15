"""
Methodology Registry + Request/Add Methodology workflow (Rev 2 §F).

GET /methodologies?calculation_type=... is filtered to Methodology rows with
at least one APPROVED MethodologyVersion (Rev 2 §F.3). Because this codebase
seeds zero APPROVED methodology content (see scripts/seed_demo_data.py), this
endpoint returns an empty list for every calculation_type today -- that is
the correct, expected behaviour, not a bug.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.engineering import Methodology, MethodologyVersion, MethodologyRequest, MethodologyStatus
from app.schemas.engineering import MethodologyOut, MethodologyRequestCreate, MethodologyRequestOut
from app.services.audit import log_event

router = APIRouter(prefix="/api", tags=["engineering"])


@router.get("/methodologies", response_model=list[MethodologyOut])
def list_methodologies(calculation_type: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Methodology)
    if calculation_type:
        q = q.filter(Methodology.engineering_domain == calculation_type)
    methodologies = q.all()

    # Only expose methodologies that have at least one APPROVED version.
    result = []
    for m in methodologies:
        has_approved = (
            db.query(MethodologyVersion)
            .filter_by(methodology_id=m.id, status=MethodologyStatus.APPROVED.value)
            .first()
        )
        if has_approved:
            result.append(m)
    return result


@router.post("/methodology-requests", response_model=MethodologyRequestOut)
def submit_methodology_request(payload: MethodologyRequestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Request/Add Methodology intake (Rev 2 §F.2). This is DATA, never an
    authorization to use the requested methodology in a calculation."""
    req = MethodologyRequest(**payload.model_dump(), requested_by=user.id)
    db.add(req)
    db.commit()
    db.refresh(req)
    log_event(db, user_id=user.id, action="METHODOLOGY_REQUESTED", object_type="METHODOLOGY_REQUEST", object_id=req.id,
              metadata={"requested_name": req.requested_name})
    return req


@router.get("/methodology-requests", response_model=list[MethodologyRequestOut])
def list_methodology_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(MethodologyRequest).all()
