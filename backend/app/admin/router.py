import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.admin.service import create_client, create_organization, create_user, grant_project_membership
from app.core.database import get_db
from app.core.deps import require_permission
from app.models.audit import AuditEvent
from app.models.rbac import Permission, Role
from app.schemas.auth import UserOut
from app.schemas.project import ClientCreate, ClientOut, OrganizationCreate, OrganizationOut
from app.schemas.rbac import PermissionOut, ProjectMembershipCreate, ProjectMembershipOut, RoleOut, UserCreate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=UserOut, status_code=201)
def create_user_route(
    payload: UserCreate, db: Session = Depends(get_db), user=Depends(require_permission("admin.manage_users"))
):
    return create_user(db, payload, created_by=user.id)


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), user=Depends(require_permission("admin.manage_users"))):
    return db.query(Role).all()


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(db: Session = Depends(get_db), user=Depends(require_permission("admin.manage_users"))):
    return db.query(Permission).all()


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization_route(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("admin.manage_users")),
):
    return create_organization(db, payload)


@router.post("/clients", response_model=ClientOut, status_code=201)
def create_client_route(
    payload: ClientCreate, db: Session = Depends(get_db), user=Depends(require_permission("admin.manage_users"))
):
    return create_client(db, payload)


@router.post("/projects/{project_id}/members", response_model=ProjectMembershipOut, status_code=201)
def grant_membership_route(
    project_id: uuid.UUID,
    payload: ProjectMembershipCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("admin.manage_users")),
):
    return grant_project_membership(db, project_id, payload, granted_by=user.id)


@router.get("/audit-events")
def list_audit_events(db: Session = Depends(get_db), user=Depends(require_permission("admin.manage_users"))):
    """
    Read-only. There is no corresponding POST -- AuditEvent rows are only
    ever written by app.core.audit.record_event() from within another
    module's own transaction (Implementation Design Rev 1 §17).
    """
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(200).all()
    return [
        {
            "id": str(e.id),
            "user_id": str(e.user_id) if e.user_id else None,
            "action": e.action,
            "object_type": e.object_type,
            "object_id": e.object_id,
            "timestamp": e.timestamp.isoformat(),
            "metadata": e.event_metadata,
        }
        for e in events
    ]
