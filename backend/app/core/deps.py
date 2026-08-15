"""
Request-scoped dependencies: current user, RBAC permission checks, and
project-membership scoping.

Design principle (Rev 2 §E.2): permissions are data (Role/Permission/
RolePermission rows), so `require_permission("investigation:write")` below
never hard-codes which roles have which rights -- it looks the grant up.
ProjectMembership additionally scopes access to specific projects (Tech
Spec §8): holding ENGINEER globally does not grant access to a project the
user has no membership row for.
"""
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.identity import Session as SessionModel, User, ProjectMembership, RolePermission, Permission

settings = get_settings()


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    session = db.get(SessionModel, token)
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")

    now = datetime.now(timezone.utc)
    if session.expires_at.replace(tzinfo=timezone.utc) < now:
        db.delete(session)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    idle_limit = settings.SESSION_IDLE_TIMEOUT_MINUTES * 60
    last_seen = session.last_seen_at.replace(tzinfo=timezone.utc)
    if (now - last_seen).total_seconds() > idle_limit:
        db.delete(session)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session idle timeout")

    session.last_seen_at = now
    db.commit()

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def get_project_role(db: DBSession, user: User, project_id: str) -> str | None:
    membership = (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user.id)
        .first()
    )
    if not membership:
        return None
    return membership.role_id


def require_permission(permission_code: str, min_level: str = "full"):
    """
    Returns a FastAPI dependency that checks the current user holds
    `permission_code` (at `min_level` or better) in AT LEAST ONE project they
    are a member of. Route handlers that operate on a specific project should
    additionally re-check membership for that exact project_id -- this
    dependency alone is not a project-scoping guarantee, only a coarse
    "does this user have this capability anywhere" gate used for
    admin-style / project-creation endpoints.
    """
    level_rank = {"none": 0, "view": 1, "comment": 2, "full": 3}

    def _check(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)) -> User:
        memberships = db.query(ProjectMembership).filter(ProjectMembership.user_id == user.id).all()
        role_ids = {m.role_id for m in memberships}
        if not role_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No project membership grants this permission")

        grants = (
            db.query(RolePermission)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id.in_(role_ids), Permission.code == permission_code)
            .all()
        )
        if not grants or max(level_rank.get(g.level, 0) for g in grants) < level_rank.get(min_level, 3):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {permission_code}")
        return user

    return _check
