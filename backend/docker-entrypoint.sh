#!/bin/sh
# Runs the Alembic migration, seeds roles/permissions/bootstrap admin, then
# starts the API server. This is the ONLY sanctioned way the production
# schema changes -- there is no create_all()/auto-sync path in application
# code (enforced by
# tests/test_architecture_boundaries.py::test_no_uncontrolled_schema_sync_in_application_code).
#
# If the migration fails, `set -e` stops the container from starting at
# all, rather than serving traffic against a schema Alembic doesn't
# recognize.
set -e

echo "Running Alembic migration against \$GI_DATABASE_URL host..."
alembic upgrade head

echo "Seeding roles/permissions and bootstrap administrator (idempotent -- see app/seed.py)..."
python -m app.seed

echo "Starting Ground Intelligence API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
