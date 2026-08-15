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

# Fail fast with a clear, actionable message rather than a raw SQLAlchemy
# stack trace. This exact check would have caught the very first live
# deploy failure (GI_DATABASE_URL was blank -- a known rough edge where
# Render Blueprints can create the service before secret values entered in
# the setup form are fully attached to it): the fix in that case is to go
# to Render -> your service -> Environment tab, confirm/re-enter the
# value, save, and trigger a Manual Deploy.
if [ -z "$GI_DATABASE_URL" ]; then
  echo "=================================================================="
  echo "FATAL: GI_DATABASE_URL is not set (or is blank)."
  echo "The container cannot start without it -- there is no fallback"
  echo "database, on purpose (see docs/INFRASTRUCTURE_DECISIONS.md)."
  echo ""
  echo "Fix: on Render, go to your service -> Environment tab, confirm"
  echo "GI_DATABASE_URL actually has a value (not blank), save, then"
  echo "trigger a Manual Deploy. This is a known rough edge where a"
  echo "Blueprint's first deploy can start before secret values entered"
  echo "in the setup form are fully attached to the service."
  echo "=================================================================="
  exit 1
fi

echo "Running Alembic migration against \$GI_DATABASE_URL host..."
alembic upgrade head

echo "Seeding roles/permissions and bootstrap administrator (idempotent -- see app/seed.py)..."
python -m app.seed

echo "Starting Ground Intelligence API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
