"""enable_rls_phase1_tables

Revision ID: 00611254f57b
Revises: 53f517af86be
Create Date: 2026-08-15 12:24:34.703822

Enables Postgres Row Level Security on every Phase-1 table, with no
policies attached. This is a Postgres-only concept (irrelevant to plain
SQLite, which the test suite uses via Base.metadata.create_all rather than
this migration -- see tests/conftest.py) so this migration no-ops on any
non-Postgres dialect rather than failing, in case someone runs
`alembic upgrade head` against a local SQLite database for a quick check.

Context: Ground Intelligence's Supabase project is a managed
Postgres/PostGIS instance reused alongside an unrelated pre-existing
application (see docs/INFRASTRUCTURE_DECISIONS.md). Supabase exposes every
public-schema table through PostgREST/GraphQL to the `anon` and
`authenticated` API roles by default. Ground Intelligence never uses that
API layer -- FastAPI connects directly via a Postgres connection string
(SQLAlchemy/psycopg2), never through Supabase's client SDK or PostgREST --
so enabling RLS with zero policies fully blocks that unintended public API
surface without affecting FastAPI's own access at all. This was originally
applied directly against the live Supabase project (with explicit user
confirmation) as an urgent fix once discovered; this migration makes that
change reproducible for any future environment instead of leaving it as a
manual, untracked exception.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00611254f57b'
down_revision: Union[str, Sequence[str], None] = '53f517af86be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "alembic_version", "organizations", "permissions", "roles", "clients",
    "role_permissions", "users", "audit_events", "projects",
    "user_sessions", "project_memberships",
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        print(f"Skipping RLS migration on non-Postgres dialect: {bind.dialect.name}")
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
