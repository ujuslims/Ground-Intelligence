# Production image for the Ground Intelligence backend.
#
# Deliberately host-agnostic: this Dockerfile is what actually runs in
# production, regardless of which FastAPI-compatible host is chosen
# (Render, Fly.io, Railway, a plain VM, etc. -- see docs/DEPLOYMENT.md).
# Nothing in here is specific to any one platform.

FROM python:3.12-slim AS base

# Runs as a non-root user; psycopg2-binary and boto3 need no OS packages
# beyond what the slim base already has, so no build-essential layer is
# needed here.
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

USER appuser

EXPOSE 8000

# The entrypoint runs the Alembic migration BEFORE starting the server, so
# a deploy can never serve traffic against a schema Alembic hasn't
# stamped -- see docker-entrypoint.sh and PIGL Final Authorization item 6
# ("database migrations executed through Alembic and not an uncontrolled
# schema-sync mechanism").
ENTRYPOINT ["./docker-entrypoint.sh"]
