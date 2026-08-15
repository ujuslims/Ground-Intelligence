# Ground Intelligence — Infrastructure Decisions

**Status:** Implementation decision, confirmed by PIGL/Product, 15 August 2026.
**Scope:** Deployment/hosting infrastructure only. Does not amend the application architecture approved in the MVP Implementation Design (Rev 1, Rev 2) or the PIGL Final Implementation Authorization. All architectural content of those documents not expressly addressed below remains unchanged and continues to apply.

## Decision

Three infrastructure platforms are approved for Ground Intelligence, each scoped narrowly:

| Platform | Role | Explicitly NOT used for |
|---|---|---|
| **GitHub** | Source control; CI/CD via GitHub Actions (migration + test verification on every push, per `.github/workflows/`) | Nothing excluded — this is a standard source-control/CI decision with no architectural implications. |
| **Netlify** | Hosting for the Next.js frontend only (`frontend/`), via `netlify.toml` | The FastAPI backend is never deployed to Netlify. Netlify's serverless/edge runtime is not designed for a persistent service holding its own Postgres connection pool and running Alembic migrations. |
| **Supabase** | Managed **PostgreSQL/PostGIS** (production/staging database) and managed **S3-compatible object storage**, accessed only through this application's existing abstractions (SQLAlchemy/Alembic for the database, `app.core.storage.StorageBackend` for files) | Supabase Auth, Supabase's PostgREST/client-SDK direct-database-access pattern, and Supabase Row Level Security as a substitute for this application's RBAC. None of these are used. |

## Why Supabase's scope is deliberately narrow

Supabase bundles two distinct things: (1) managed Postgres + S3-compatible storage, and (2) a client-facing auth/data-access layer (Supabase Auth, PostgREST, client SDKs) intended to let a frontend talk to the database with little or no backend in between.

Only (1) is approved. (2) is not used, for two specific reasons tied to decisions already made in the controlled baseline:

1. **Session storage.** Supabase Auth's default client pattern stores session tokens in browser storage. The PIGL Final Implementation Authorization (§11) explicitly prohibits storing authentication tokens in browser localStorage and requires HTTP-only, server-managed session cookies. The backend's existing session implementation (`app/auth/`, `app/core/deps.py`) already satisfies this and is not replaced.

2. **The governance chokepoint.** The Implementation Design's engineering-calculation activation gate, RBAC enforcement, and audit trail are deliberately enforced in exactly one place — the FastAPI service layer — specifically so no endpoint, UI, or tool call can bypass them (Implementation Design Rev 2 §J.1: "there is exactly one place in the codebase where this is decided"). Supabase's normal pattern of a frontend querying Postgres directly (via PostgREST or a client SDK, optionally gated by Row Level Security) would create a second, parallel path to the data that does not go through that chokepoint. This would not be a hosting change — it would undo a specific, already-approved governance design and would need to go back through PIGL review, not be adopted informally.

**Practical rule:** if a future change would have the Next.js frontend, or GeoBrain, talk to Supabase directly instead of talking to the FastAPI backend, that change is out of scope for "use Supabase as infrastructure" and requires a new PIGL/Product decision — it is not something to implement as a convenience.

## What changed in the codebase to reflect this

- `backend/app/core/config.py` — `database_url` documented as accepting a Supabase Postgres connection string (session pooler or direct connection), alongside the local-dev Postgres default. No code change beyond documentation/comments; the connection string was already environment-driven.
- `backend/app/core/config.py` / `backend/.env.example` — `storage_endpoint_url`/`storage_access_key`/`storage_secret_key` documented as accepting Supabase Storage's S3-compatible endpoint and generated S3 keys, alongside the local-dev MinIO default. `app/core/storage.py`'s `StorageBackend` abstraction is unchanged — Supabase Storage is just another S3-compatible endpoint to it.
- `.github/workflows/backend-ci.yml` — runs the Alembic migration and full pytest suite against a real `postgres:16` service container on every push/PR (not just SQLite), so CI verifies against genuine Postgres behavior even though Supabase itself isn't reachable from CI.
- `.github/workflows/frontend-ci.yml` — lints and builds the Next.js frontend on every push/PR.
- `netlify.toml` — builds and deploys only `frontend/`.
- `infra/docker-compose.yml` — local-dev Postgres + MinIO, so a developer never needs live Supabase credentials to run the platform locally.

## What did not change

The application architecture, module boundaries, RBAC model, audit model, and engineering-calculation activation gate designed in the MVP Implementation Design (Rev 1, Rev 2) and confirmed in the PIGL Final Implementation Authorization are unchanged. This is a hosting decision, not an architecture decision.
