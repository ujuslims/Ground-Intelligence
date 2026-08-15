# Ground Intelligence

Integrated multidisciplinary subsurface and engineering intelligence platform for Polaris Integrated & Geosolutions Limited (PIGL). See `docs/` for the governing specification set and `docs/INFRASTRUCTURE_DECISIONS.md` for hosting/infrastructure choices.

**Status: Phase 1 (platform foundation) — in progress.** See "What's actually implemented" below before assuming any capability exists.

## Repository structure

```
ground-intelligence/
  backend/     FastAPI application (Python) -- the sole application/service gateway.
               Owns the database schema, all business logic, RBAC, audit, and
               (in a later phase) the engineering-calculation governance gate.
  frontend/    Next.js/TypeScript frontend. Talks only to the backend API.
  infra/       Local-development infrastructure (docker-compose: Postgres + MinIO).
  docs/        Architecture and governance documents.
  .github/     CI workflows (backend tests, frontend build).
```

## Infrastructure

- **Database & file storage:** Supabase-managed PostgreSQL/PostGIS and S3-compatible storage in staging/production; local Postgres+MinIO via `infra/docker-compose.yml` for development. See `docs/INFRASTRUCTURE_DECISIONS.md`.
- **Backend hosting:** not yet decided/deployed (Netlify is not suitable for the FastAPI service — see infrastructure decisions doc).
- **Frontend hosting:** Netlify (`netlify.toml`), builds `frontend/` only.
- **Source control / CI:** GitHub, with Actions workflows in `.github/workflows/` running the backend test suite against a real Postgres container and the frontend lint+build on every push/PR.

## Local development

```bash
# 1. Start local Postgres + MinIO
cd infra && docker compose up -d

# 2. Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed        # seeds roles/permissions; set GI_BOOTSTRAP_ADMIN_PASSWORD first
uvicorn app.main:app --reload

# 3. Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## First login — how it actually gets created

There is no pre-existing account anywhere — not in this repo, not on any server. The first ("bootstrap") administrator account is created by `app/seed.py`, which runs automatically as part of `docker-entrypoint.sh` every time the backend container starts (migrate → seed → serve). It is **idempotent**: safe to run on every restart, and it does nothing if an account with that email already exists.

**You choose the credentials, not Claude.** Set these two environment variables wherever the backend runs (locally in `.env`, or in Render's dashboard for a real deployment):

```
GI_BOOTSTRAP_ADMIN_EMAIL=<a real email address>
GI_BOOTSTRAP_ADMIN_PASSWORD=<a real password you choose>
```

Whatever you set is what you log in with. If `GI_BOOTSTRAP_ADMIN_PASSWORD` is left unset, the seed step skips creating an admin (and logs a warning) rather than creating one with a guessable default — there is deliberately no fallback password anywhere in this codebase.

**One gotcha already fixed:** don't use a `.local`, `.test`, `.invalid`, or `.localhost` email domain (e.g. `admin@pigl.local`) — Pydantic's email validation rejects these as IANA special-use domains, and the very first login attempt would fail with a validation error before it even checked the password. Use a real domain (your actual PIGL email, or the `.env.example` placeholder `admin@pigl.example` for local testing only).

To test this locally right now, without any live infrastructure:
```bash
cd infra && docker compose up -d
cd ../backend
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # edit GI_BOOTSTRAP_ADMIN_EMAIL / _PASSWORD to your own values
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
# then POST {"email": ..., "password": ...} to http://localhost:8000/auth/login
```

## Testing

```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
cd frontend && npm run lint && npm run build
```

## Implementation status

Maintained using five distinct levels, per explicit instruction — a component is never described as more "done" than the strongest level it has actually reached:

1. **Implemented** — code exists and runs.
2. **Locally tested** — automated tests pass on a developer machine / this sandbox.
3. **CI-tested** — verified automatically on GitHub Actions (real ephemeral Postgres for the backend, real `npm ci`/build/lint for the frontend).
4. **Verified against live infrastructure** — actually exercised against a real deployed Supabase project, Netlify site, or backend host. **Nothing is at this level yet.**
5. **Production-ready** — deployed, verified, and fit to hold real PIGL project data. **Nothing is at this level yet.**

| Component | Status | Notes |
|---|---|---|
| Session auth (login/logout/me) | 1, 2, 3 | 28/28 backend tests pass locally; same suite runs in `backend-ci.yml` against a real Postgres container. |
| Data-driven RBAC (6 roles, project membership) | 1, 2, 3 | Includes the CLIENT_EXTERNAL_REVIEWER non-inheritance test. |
| Project/Org/Client CRUD | 1, 2, 3 | |
| Audit trail | 1, 2, 3 | Includes a test confirming there is no direct write endpoint. |
| Alembic migration (all Phase-1 tables) | 1, 2, 3 | Locally verified against SQLite (schema shape only); CI applies it to real Postgres and confirms it's reversible (`alembic downgrade base`). **Never yet applied to Supabase.** |
| Architecture boundary tests (no direct DB/storage access outside the service layer; frontend has no DB/Supabase client dependency; migrations-only schema changes) | 1, 2, 3 | New this stage — see `backend/tests/test_architecture_boundaries.py`. |
| Storage abstraction (S3-compatible) | 1 only | Interface-level tests only (constructs correctly, rejects bad config). **Never connected to a real S3-compatible endpoint of any kind** — not MinIO, not Supabase Storage, not AWS S3. |
| Next.js frontend (login, project list) | 1, 2, 3 | `npm run build`, `npm run lint`, and `npm ci` (exactly what CI runs) all verified locally. Never deployed anywhere. |
| Backend Dockerfile / entrypoint | 1, 2 (raised this turn) | The entrypoint originally ran only the migration, not the seed step — meaning a real deploy would have started successfully but had zero roles/permissions/admin account, locking everyone out with no way in. Fixed: `docker-entrypoint.sh` now runs `alembic upgrade head` → `python -m app.seed` → `uvicorn` on every start. The full migrate→seed→login→session→admin-endpoint→wrong-password-rejected flow was run live against a local SQLite database and confirmed working end to end. **Docker itself still isn't available in this sandbox, so the container image has never actually been built** — the flow was proven by running the same Python entrypoint logic directly, not by `docker build && docker run`. |
| Supabase integration (Postgres + Storage config) | 1 only | Config wired and documented (`docs/INFRASTRUCTURE_DECISIONS.md`, `.env.example`, `render.yaml`). **No Supabase project has been created; nothing has connected to one.** |
| Netlify deployment config | 1 only | `netlify.toml` present, `@netlify/plugin-nextjs` installed, build verified locally. **No Netlify site exists yet.** |
| Backend hosting (Render recommended) | 1 only | `render.yaml` blueprint written. **No Render (or other) service exists yet.** |
| GeoBrain governance boundary | Not implemented | GeoBrain doesn't exist yet (Phase 5–6). A trip-wire test (`test_geobrain_module_not_yet_present_boundary_still_documented`) fails on purpose if `app/geobrain/` is ever added without updating the boundary test — see that test's docstring. |



## Engineering-calculation governance

Not applicable yet — the calculation engine is Phase 5 scope and does not exist in this codebase. When it is built, it must satisfy the activation gate design in Implementation Design Rev 2 §J: no production calculation may execute for a calculation type lacking an APPROVED MethodologyVersion. The shallow-foundation bearing-capacity methodology remains unapproved by PIGL Engineering as of this commit.
