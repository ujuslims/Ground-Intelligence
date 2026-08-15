import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.core.security import hash_password
from app.models.org import Client, Organization
from app.models.rbac import ProjectMembership, User
from app.schemas.project import ClientCreate, OrganizationCreate
from app.schemas.rbac import ProjectMembershipCreate, UserCreate


def create_user(db: Session, payload: UserCreate, created_by: uuid.UUID | None) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    user = User(email=payload.email, name=payload.name, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    record_event(db, user_id=created_by, action="CREATE_USER", object_type="User", object_id=str(user.id))
    db.commit()
    db.refresh(user)
    return user


def grant_project_membership(
    db: Session, project_id: uuid.UUID, payload: ProjectMembershipCreate, granted_by: uuid.UUID
) -> ProjectMembership:
    existing = (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id, ProjectMembership.user_id == payload.user_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "user already has membership on this project")

    membership = ProjectMembership(
        project_id=project_id, user_id=payload.user_id, role_id=payload.role_id, granted_by=granted_by
    )
    db.add(membership)
    record_event(
        db,
        user_id=granted_by,
        action="GRANT_PROJECT_MEMBERSHIP",
        object_type="ProjectMembership",
        object_id=str(project_id),
        metadata={"user_id": str(payload.user_id), "role_id": str(payload.role_id)},
    )
    db.commit()
    db.refresh(membership)
    return membership


def create_organization(db: Session, payload: OrganizationCreate) -> Organization:
    org = Organization(name=payload.name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def create_client(db: Session, payload: ClientCreate) -> Client:
    client = Client(name=payload.name, organization_id=payload.organization_id)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client
