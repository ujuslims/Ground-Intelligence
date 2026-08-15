"""Initial Ground Intelligence MVP schema (Phase 1 + Phase 2 entities)

Generated from the SQLAlchemy models in app/models/, which implement the
entity list confirmed in the MVP Data Model, its Controlled Revision, and
Implementation Design Rev 2 §A.1. Provenance columns (source, version,
status, created_by, created_at) are non-nullable from this first migration
per the Data Model Controlled Revision §3 safeguard.

Revision ID: 0001
Revises:
Create Date: 2026-08-15

NOTE ON HOW THIS MIGRATION IS WRITTEN: this environment has no live
PostgreSQL instance to run `alembic revision --autogenerate` against, so
this initial migration is written to call Base.metadata.create_all() /
drop_all() directly rather than hand-authoring 34 op.create_table() blocks
(which would risk drifting from app/models/ and re-introduce exactly the
"silently redefine the schema" risk the Controlled Specification Register
warns against). This is the correct and only migration written this way --
run `alembic revision --autogenerate -m "..."` for every migration after
this one, once `docker-compose up db` gives Alembic a real Postgres/PostGIS
connection to diff against.
"""
from alembic import op

from app.core.database import Base
from app import models  # noqa: F401

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
