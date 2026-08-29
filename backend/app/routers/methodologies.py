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
from app.core.authz import require_project_access
from app.models.identity import User, ProjectMembership
from app.models.engineering import Methodology, MethodologyVersion, MethodologyRequest, MethodologyStatus
from app.schemas.engineering import MethodologyOut, MethodologyVersionOut, MethodologyRequestCreate, MethodologyRequestOut
from app.services.audit import log_event

router = APIRouter(prefix="/api", tags=["engineering"])


@router.get("/methodologies", response_model=list[MethodologyOut])
def list_methodologies(calculation_type: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Methodology)
    if calculation_type:
        q = q.filter(Methodology.engineering_domain == calculation_type)
    methodologies = q.all()

    # Only expose methodologies with at least one version APPROVED for the
    # requesting user's OWN organization -- another organization having
    # approved the same methodology name doesn't make it usable here (see
    # calculation_engine.py's organization-scoping check, which independently
    # re-verifies this regardless of what this endpoint returns).
    result = []
    for m in methodologies:
        has_approved = (
            db.query(MethodologyVersion)
            .filter_by(methodology_id=m.id, status=MethodologyStatus.APPROVED.value, organization_id=user.organization_id)
            .first()
        )
        if has_approved:
            result.append(m)
    return result


@router.get("/methodologies/{methodology_id}/versions", response_model=list[MethodologyVersionOut])
def list_methodology_versions(methodology_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Only versions APPROVED for the requesting user's own organization are
    exposed -- consistent with the governance gate in
    app/services/calculation_engine.py, which independently re-verifies both
    status and organization_id regardless of what this endpoint returns."""
    return (
        db.query(MethodologyVersion)
        .filter_by(methodology_id=methodology_id, status=MethodologyStatus.APPROVED.value, organization_id=user.organization_id)
        .all()
    )


@router.post("/methodology-requests", response_model=MethodologyRequestOut)
def submit_methodology_request(payload: MethodologyRequestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Request/Add Methodology intake (Rev 2 §F.2). This is DATA, never an
    authorization to use the requested methodology in a calculation."""
    if payload.project_id:
        require_project_access(db, user, payload.project_id)
    req = MethodologyRequest(**payload.model_dump(), requested_by=user.id)
    db.add(req)
    db.commit()
    db.refresh(req)
    log_event(db, user_id=user.id, action="METHODOLOGY_REQUESTED", object_type="METHODOLOGY_REQUEST", object_id=req.id,
              metadata={"requested_name": req.requested_name})
    return req


@router.get("/methodology-requests", response_model=list[MethodologyRequestOut])
def list_methodology_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Scoped to requests the requesting user could plausibly see: requests
    tied to a project they're a member of, plus their own requests (which may
    have no project_id at all). Without this, any authenticated user could
    read every organization's methodology requests -- a cross-tenant leak of
    what firms are working on, not just calculation data."""
    project_ids = [m.project_id for m in db.query(ProjectMembership).filter_by(user_id=user.id).all()]
    return (
        db.query(MethodologyRequest)
        .filter(
            MethodologyRequest.project_id.in_(project_ids) | (MethodologyRequest.requested_by == user.id)
        )
        .all()
    )
