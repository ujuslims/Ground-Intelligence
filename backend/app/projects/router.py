import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission, require_project_permission
from app.models.rbac import Role
from app.projects.service import create_project, get_project_for_user, list_projects_for_user
from app.schemas.project import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project_route(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.create")),
):
    # The creator's membership on the new project uses the PROJECT_MANAGER
    # role by default in Phase 1 (the person authorized to create a
    # project at the org level is treated as its manager unless/until
    # membership is edited). This is a documented implementation default,
    # not a hard-coded permission bypass -- it is still an ordinary
    # ProjectMembership row, editable like any other.
    manager_role = db.query(Role).filter(Role.code == "PROJECT_MANAGER").first()
    project = create_project(db, payload, created_by=user.id, owner_role_id=manager_role.id)
    return project


@router.get("", response_model=list[ProjectOut])
def list_my_projects(db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Inherently self-scoped (returns only projects this user has a
    # ProjectMembership on), so it requires authentication but no
    # additional permission check -- there is nothing to authorize beyond
    # "this is your own membership list."
    return list_projects_for_user(db, user.id)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project_route(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_project_permission("project.read")),
):
    return get_project_for_user(db, project_id, user.id)
