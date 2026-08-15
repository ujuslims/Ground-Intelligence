"""
Identity, RBAC and session models.

RBAC is data-driven (Role / Permission / RolePermission rows), NOT hard-coded
enums in application logic — per Implementation Design Rev 2 §E.2, so refining
role boundaries (e.g. CLIENT_EXTERNAL_REVIEWER) is a data change, not a
redeploy. ProjectMembership enforces project-level scoping: holding a role does
not by itself grant access to every project (Tech Spec §8).

Six MVP system roles (Rev 2 §E.1) — seeded by scripts/seed_rbac.py, not
hard-coded here: ENGINEER, TECHNICAL_REVIEWER, LABORATORY_USER,
PROJECT_MANAGER, ADMINISTRATOR, CLIENT_EXTERNAL_REVIEWER.

Sessions are server-managed and stored in PostgreSQL (Rev 2 §I.1) so they
survive a backend restart — never client-held tokens, never localStorage.
"""
from datetime import datetime

from sqlalchemy import String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import gen_uuid, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    memberships: Mapped[list["ProjectMembership"]] = relationship(back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)  # e.g. "investigation:write"
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id"), nullable=False)
    # "none" | "view" | "comment" | "full" — lets one permission code carry a graded level
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="full")

    role: Mapped["Role"] = relationship(back_populates="permissions")


class ProjectMembership(Base):
    """Project-level scoping: a role only grants access within projects where
    a membership row exists (Tech Spec §8)."""
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="memberships")
    role: Mapped["Role"] = relationship()


class Session(Base):
    """Server-side session store (Rev 2 §I.1). The cookie only carries this id."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # opaque random token
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
