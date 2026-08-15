"""
Import every model module here so that Base.metadata (used by tests and by
`alembic revision --autogenerate`) discovers all tables.
"""
from app.models.org import Client, Organization  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.rbac import (  # noqa: F401
    Permission,
    ProjectMembership,
    Role,
    RolePermission,
    User,
    UserSession,
)
from app.models.audit import AuditEvent  # noqa: F401
