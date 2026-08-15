import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.models.project import Project
from app.models.rbac import ProjectMembership
from app.schemas.project import ProjectCreate


def create_project(db: Session, payload: ProjectCreate, created_by: uuid.UUID, owner_role_id: uuid.UUID) -> Project:
    existing = db.query(Project).filter(Project.project_code == payload.project_code).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "project_code already exists")

    project = Project(
        project_code=payload.project_code,
        name=payload.name,
        client_id=payload.client_id,
        project_type=payload.project_type,
        description=payload.description,
        location=payload.location,
        created_by=created_by,
    )
    db.add(project)
    db.flush()  # populate project.id before using it below

    # The creator is automatically granted membership on the project they
    # created, using the role passed in by the caller (Phase 1: the
    # creating user's own role). Without this, a user could create a
    # project and then be immediately locked out of it by their own RBAC
    # enforcement.
    db.add(ProjectMembership(project_id=project.id, user_id=created_by, role_id=owner_role_id))

    record_event(db, user_id=created_by, action="CREATE_PROJECT", object_type="Project", object_id=str(project.id))
    db.commit()
    db.refresh(project)
    return project


def list_projects_for_user(db: Session, user_id: uuid.UUID) -> list[Project]:
    return (
        db.query(Project)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .filter(ProjectMembership.user_id == user_id)
        .all()
    )


def get_project_for_user(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
    membership = (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user_id)
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project
