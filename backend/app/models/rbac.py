"""
Data-driven RBAC models, per Implementation Design Rev 2 §E.

Role/Permission/RolePermission are ROWS, not application-code enums, so the
five... now six... system roles (ENGINEER, TECHNICAL_REVIEWER,
LABORATORY_USER, PROJECT_MANAGER, ADMINISTRATOR, CLIENT_EXTERNAL_REVIEWER)
and their permission sets can be refined by editing data, not redeploying
code. See app/seed.py for the seeded roles/permissions/default matrix.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin, utcnow


class Role(UUIDPKMixin, Base):
    __tablename__ = "roles"

    # Fixed set of six codes seeded at migration time (Rev 2 §E.1). The
    # *permissions* attached to a role are data-driven and editable; the
    # existence of these six codes is a controlled/approved decision, so
    # code is uniquely constrained but is still just a row, not an enum
    # baked into application logic.
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role")


class Permission(UUIDPKMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id"), nullable=False)

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship()


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")  # ACTIVE | DISABLED

    # Global (org-level, not project-scoped) role -- solves the bootstrap
    # problem of "no user can create the first project because
    # project.create is only granted through a ProjectMembership, which
    # requires a project to already exist." Only ADMINISTRATOR-type
    # accounts are expected to carry a global_role_id in practice; ordinary
    # ENGINEER/TECHNICAL_REVIEWER/etc. access remains project-scoped via
    # ProjectMembership, per Implementation Design Rev 2 §E.2.
    global_role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"), nullable=True)

    memberships: Mapped[list["ProjectMembership"]] = relationship(
        back_populates="user", foreign_keys="ProjectMembership.user_id"
    )
    global_role: Mapped["Role | None"] = relationship(foreign_keys=[global_role_id])


class ProjectMembership(Base):
    """
    Enforces project-level access (Tech Spec §8): holding a Role does not
    grant access to every project, only to projects with a membership row.
    """
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="memberships", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship()


class UserSession(Base):
    """
    Server-side session store backing the HTTP-only session cookie
    (Implementation Design Rev 2 §I.1). The cookie holds only an opaque
    session token; all session state -- including expiry and idle timeout
    -- lives here, so a session can be revoked server-side at any time.
    """
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship()
