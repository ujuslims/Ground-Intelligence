from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User, ProjectMembership, Role
from app.models.project import Project
from app.schemas.core import ProjectCreate, ProjectOut
from app.services.audit import log_event

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project_ids = [m.project_id for m in db.query(ProjectMembership).filter_by(user_id=user.id).all()]
    return db.query(Project).filter(Project.id.in_(project_ids)).all()


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    if not data.get("organization_id"):
        # No Organization ID field on the "New project" form -- this is the
        # normal path. Default to the creating user's own organization.
        if not user.organization_id:
            raise HTTPException(
                400,
                "Your account isn't assigned to an organization, so a project can't be created. "
                "Ask an administrator to set your organization.",
            )
        data["organization_id"] = user.organization_id
    project = Project(**data, created_by=user.id)
    db.add(project)
    db.flush()

    # Creator is auto-enrolled as ENGINEER on their own project so the
    # project isn't orphaned of any membership (ProjectMembership scoping,
    # Tech Spec §8). Admins may adjust membership afterward.
    engineer_role = db.query(Role).filter_by(name="ENGINEER").first()
    if engineer_role:
        db.add(ProjectMembership(project_id=project.id, user_id=user.id, role_id=engineer_role.id))

    db.commit()
    db.refresh(project)
    log_event(db, user_id=user.id, action="PROJECT_CREATED", object_type="PROJECT", object_id=project.id)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.query(ProjectMembership).filter_by(project_id=project_id, user_id=user.id).first()
    if not membership:
        raise HTTPException(403, "No membership on this project")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project
