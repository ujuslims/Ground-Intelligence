"""
Minimal, data-driven Admin/RBAC capability (Rev 2 Amendment 4) — not a large
enterprise administration subsystem. Manages users, roles, permissions and
project membership as data.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permission
from app.core.security import hash_password
from app.models.identity import User, Role, ProjectMembership
from app.models.project import Project
from app.services.audit import log_event
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role_name: str
    project_id: str


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), user: User = Depends(require_permission("admin:manage_users"))):
    return [{"id": r.id, "name": r.name, "description": r.description} for r in db.query(Role).all()]


@router.post("/users")
def create_user(payload: CreateUserRequest, db: Session = Depends(get_db), admin: User = Depends(require_permission("admin:manage_users"))):
    role = db.query(Role).filter_by(name=payload.role_name).first()
    if not role:
        return {"error": f"Unknown role: {payload.role_name}"}

    # require_permission only confirms the admin holds admin:manage_users on
    # SOME project -- without the checks below, that admin could add a user
    # to ANY project_id across ANY organization, which is a cross-tenant
    # privilege-escalation path once more than one organization exists here.
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    admin_membership = db.query(ProjectMembership).filter_by(project_id=payload.project_id, user_id=admin.id).first()
    if not admin_membership:
        raise HTTPException(403, "You must be a member of the project you're adding this user to")

    new_user = User(
        email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password),
        organization_id=project.organization_id,
    )
    db.add(new_user)
    db.flush()
    db.add(ProjectMembership(project_id=payload.project_id, user_id=new_user.id, role_id=role.id))
    db.commit()
    log_event(db, user_id=admin.id, action="USER_CREATED", object_type="USER", object_id=new_user.id,
              metadata={"role": payload.role_name, "project_id": payload.project_id})
    return {"id": new_user.id, "email": new_user.email, "role": payload.role_name}
