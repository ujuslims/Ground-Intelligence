"""
Small, idempotent schema patches for changes made AFTER the original
Base.metadata.create_all() bootstrap (see module docstring in
seed_demo_data.py / alembic/versions/0001_initial_schema.py for why this
codebase bootstraps its schema that way instead of via `alembic upgrade
head`). create_all() only creates missing TABLES -- it never ALTERs an
existing table to add a column a model gained after that table already
existed live. This script is the narrow, deliberate exception: it applies
exactly the column additions below, each written so it is safe to run again
on every container start (IF NOT EXISTS / no-op if already applied).

Run BEFORE Base.metadata.create_all() in the startup sequence (see
seed_demo_data.seed(), called from the Dockerfile CMD) so a fresh database
gets the column from create_all() directly and an existing one gets it
patched in here.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.core.database import engine


def migrate():
    with engine.begin() as conn:
        # MethodologyVersion.organization_id -- added when methodology approval
        # became organization-scoped (a firm's technical reviewer approves a
        # methodology for THEIR OWN organization's use; one firm's approval
        # must never silently authorize another firm's calculations). Added
        # here because methodology_versions already existed live with one
        # APPROVED row (PIGL's Eurocode 7 square-pad v1.0) before this column
        # was introduced.
        conn.execute(text(
            "ALTER TABLE methodology_versions "
            "ADD COLUMN IF NOT EXISTS organization_id VARCHAR(36) REFERENCES organizations(id)"
        ))

        # Backfill: the one pre-existing APPROVED version in this deployment
        # was approved by and for PIGL -- attribute it to PIGL's organization
        # rather than leaving it org-less (which the new activation gate
        # would otherwise treat as usable by no one).
        conn.execute(text(
            "UPDATE methodology_versions SET organization_id = "
            "(SELECT id FROM organizations WHERE name = 'PIGL Demonstration Organization' LIMIT 1) "
            "WHERE organization_id IS NULL"
        ))
    print("Schema patch applied: methodology_versions.organization_id")


if __name__ == "__main__":
    migrate()
