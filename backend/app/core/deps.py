"""
FastAPI dependencies for authentication and RBAC enforcement.

get_current_user resolves the session cookie -> UserSession -> User, doing
the server-side validation the Implementation Design requires (expiry,
idle timeout, revocation) rather than trusting the cookie's mere presence.

require_permission / require_project_permission are dependency factories
used by every module's router to enforce the data-driven RBAC model
(Rev 2 §E): a user's *global* permissions come from their Role's
RolePermission rows; project-scoped actions additionally require a
ProjectMembership row for that specific project.
"""
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_token
from app.models.rbac import Permission, ProjectMembership, Role, RolePermission, User, UserSession


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    token_hash = hash_token(token)
    session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    now = datetime.now(timezone.utc)

    if session is None or session.revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    if session.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    idle_cutoff = session.last_seen_at.replace(tzinfo=timezone.utc)
    idle_limit_minutes = settings.session_idle_timeout_minutes
    if (now - idle_cutoff).total_seconds() > idle_limit_minutes * 60:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session idle timeout")

    user = db.get(User, session.user_id)
    if user is None or user.status != "ACTIVE":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive")

    session.last_seen_at = now
    db.commit()
    return user


def _user_global_permission_codes(db: Session, user: User) -> set[str]:
    """
    A user's global (non-project-scoped) permission set is the union of:
      (a) permissions granted by the user's global_role_id, if any
          (typically ADMINISTRATOR -- see User.global_role_id docstring), and
      (b) permissions granted by every Role attached to the user through
          any ProjectMembership.
    This is used for actions that aren't scoped to one specific project,
    such as "can create a new project at all" or "can manage users."
    Project-scoped actions use require_project_permission instead, which
    checks membership on the specific project_id in the path.
    """
    codes: set[str] = set()

    if user.global_role_id is not None:
        global_rows = (
            db.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == user.global_role_id)
            .all()
        )
        codes.update(r[0] for r in global_rows)

    membership_rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(ProjectMembership, ProjectMembership.role_id == Role.id)
        .filter(ProjectMembership.user_id == user.id)
        .distinct()
        .all()
    )
    codes.update(r[0] for r in membership_rows)
    return codes


def require_permission(permission_code: str):
    """Dependency factory: require a permission the user holds in ANY project (e.g. admin actions)."""

    def _check(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        codes = _user_global_permission_codes(db, user)
        if permission_code not in codes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {permission_code}")
        return user

    return _check


def require_project_permission(permission_code: str):
    """
    Dependency factory for project-scoped endpoints. Expects a `project_id`
    path parameter. Enforces both: (a) the user has a ProjectMembership for
    this specific project, and (b) that membership's role grants the
    requested permission.
    """

    def _check(
        project_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        membership = (
            db.query(ProjectMembership)
            .filter(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user.id)
            .first()
        )
        if membership is None:
            # 404, not 403: a user with no relationship to this project
            # should not be able to distinguish "project doesn't exist"
            # from "project exists but you have no membership" by response
            # code. A user who IS a member but lacks the specific
            # permission gets 403 below instead, which is fine to reveal.
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

        has_permission = (
            db.query(RolePermission)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id == membership.role_id, Permission.code == permission_code)
            .first()
        )
        if has_permission is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Role does not grant permission: {permission_code}"
            )
        return user

    return _check
