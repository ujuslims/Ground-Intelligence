# Ground Intelligence — MVP (Phase 1–2 build)

Multidisciplinary subsurface and engineering intelligence platform for PIGL
(Polaris Integrated & Geosolutions Limited). This build implements the
**candidate baseline confirmed in MVP Implementation Design Revision 2**
(14–15 August 2026) — see `Ground Intelligence Controlled Specification
Register` in the project workspace for the full governance trail.

## What this is, precisely

This is a working application scaffold, not a finished product. It correctly
implements Phase 1 (Platform Foundation) end-to-end and a substantial slice
of Phase 2 (Investigation Data), plus the *structure* — deliberately not the
content — of Phases 5–7 (Engineering Framework, GeoBrain, Reporting), per the
phased sequence in the MVP Technical Specification §54 and the explicit
instruction that engineering-calculation *content* must not be built ahead of
PIGL Engineering approval.

### Implemented and tested

- **Data model**: all 34 entities from the MVP Data Model + Implementation
  Design Rev 2 §A.1 (Organization, Client, Project, Investigation,
  InvestigationLocation, Borehole, BoreholeStratum, SPT, CPT, CPTReading,
  Sample, LaboratoryResult, GroundwaterObservation, VES, VESReading,
  VESLayer, Dataset, File, Methodology, MethodologyVersion,
  MethodologyRequest, Calculation, CalculationVersion, Report,
  ReportTemplate, ReportSection, Review, AuditEvent, User, Role, Permission,
  RolePermission, ProjectMembership, Session). Provenance columns
  (`source`, `version`, `status`, `created_by`, `created_at`) are
  non-nullable from the first migration, per the Data Model Controlled
  Revision §3 safeguard.
- **Auth**: server-managed sessions, HTTP-only cookies, PostgreSQL-backed
  session store, bcrypt password hashing. No tokens in localStorage.
- **RBAC**: six seeded roles (ENGINEER, TECHNICAL_REVIEWER, LABORATORY_USER,
  PROJECT_MANAGER, ADMINISTRATOR, CLIENT_EXTERNAL_REVIEWER), data-driven
  Role/Permission/RolePermission, project-scoped via ProjectMembership.
- **Projects, Investigations, InvestigationLocations**: full CRUD, with the
  audit trail wired into every mutating action.
- **Boreholes, stratigraphy, SPT (observational-only), CPT (with import
  validation), groundwater, samples, laboratory results (Path B import),
  VES (readings + interpreted layers)**: CRUD + import endpoints.
- **File storage**: S3-compatible abstraction (`app/services/storage.py`) —
  MinIO locally, Amazon S3 in production — no provider-specific code
  anywhere else in the codebase.
- **Engineering calculation governance gate**
  (`app/services/calculation_engine.py`): the single place in the codebase
  that decides whether a calculation may produce a real result. It
  independently re-verifies methodology approval server-side and currently
  refuses **every** real `calculation_type` with an explicit
  `REFUSED_NO_APPROVED_METHODOLOGY` outcome, because zero
  `MethodologyVersion` rows are seeded with `status = APPROVED`. This is
  proven by automated tests, not just documented.
- **Methodology Registry + Request/Add Methodology workflow**: the governed
  intake pathway from Rev 2 §F.2.
- **GeoBrain's 15-tool contract** (`app/geobrain/tools.py`): all 15 tools
  from the authoritative CC-GB-01 list are implemented as real, DB-backed
  functions. `run_engineering_calculation` and `get_report_template` are
  governed/conditional exactly as CC-GB-01 requires. The LLM orchestration
  loop itself is intentionally **not** wired up yet — see "What's
  deliberately not built" below.
- **Draft Engineering Summary** report engine: assembles a report from real
  project data, always labelled `DRAFT — ENGINEER REVIEW REQUIRED`, no
  invented PIGL content or branding.
- **Frontend**: Next.js/TypeScript app — login, project dashboard, project
  detail page with a MapLibre investigation-location map, CPT import
  visualization (qc/fs/u2 vs depth), a live demonstration of the calculation
  gate refusing a shallow-foundation request, and draft-summary generation.
  `npm run build` passes with no type errors.
- **Synthetic demonstration data** (`scripts/seed_demo_data.py`): one demo
  project with a borehole, CPT, lab sample, groundwater observation and VES
  survey, every record labelled `DEMONSTRATION DATA — NOT REAL PIGL PROJECT
  DATA`.
- **Tests**: `backend/tests/` — 10 passing tests, including the two that
  matter most: proof that a shallow-foundation calculation is refused, and
  proof that the gate re-verifies server-side even if a caller supplies a
  DRAFT (unapproved) `methodology_version_id`.

### What's deliberately not built — and why

Per the Controlled Specification Register, these are **governance gates**,
not missing engineering effort:

1. **Any real bearing-capacity (or other) calculation logic.** No formula,
   factor, soil model, or standard reference appears anywhere in this
   codebase. `app/services/calculation_engine.py` has an empty
   implementation registry for every real `calculation_type`. This stays
   empty until PIGL Engineering supplies and approves a methodology.
2. **PIGL's actual Draft Engineering Summary content/branding.**
   `ReportTemplate` rows are not populated; the report engine assembles
   sections from real data but the template metadata itself is a PIGL
   deliverable.
3. **GeoBrain's production system instructions / orchestration loop.** The
   15-tool contract is real and callable; the LLM conversation loop that
   would call those tools autonomously is not wired up, because doing so
   convincingly requires PIGL's existing custom-GPT configuration material
   (per the Build Prompt Controlled Revision's explicit "do not recreate
   from memory" gate). `app/geobrain/llm_provider.py` has the
   Anthropic-Claude-behind-an-abstraction-layer plumbing ready for that
   wiring once the source material arrives.
4. **Admin/RBAC frontend screen.** The backend endpoints
   (`app/routers/admin.py`) exist; a UI for them was not built in this pass
   to keep this build's scope defensible — add a `/admin` page against
   `POST /api/admin/users` and `GET /api/admin/roles` when needed.
5. **Laboratory/CPT/VES *file upload* → column-mapping wizard.** The import
   *endpoints* exist and validate (see `app/services/cpt_validation.py` for
   the CPT rules), but they currently accept already-structured JSON rather
   than parsing an uploaded spreadsheet with a column-mapping UI. That
   wizard (file → format detection → column mapping → user confirmation) is
   the next piece of Phase 2/3 work.
6. **PostGIS-specific spatial queries.** `InvestigationLocation` currently
   stores plain `latitude`/`longitude` floats rather than a PostGIS
   `geometry` column. This was a scope call to keep the schema portable for
   this sandbox's testing (no live Postgres was available to validate
   PostGIS types against). Migrating to a real `geometry(Point, 4326)`
   column with a GiST index is a small, contained change before spatial
   queries (radius search, polygon clipping) are needed.

## Architecture

```
backend/
  app/
    core/        settings, DB session, auth/session dependencies, password hashing
    models/      SQLAlchemy models — one file per domain area
    schemas/     Pydantic request/response schemas
    routers/     FastAPI routers — one file per domain area
    services/    audit trail, S3-compatible storage, CPT validation,
                 the calculation-engine gate, the report engine
    geobrain/    the 15-tool contract + model-abstraction layer
  alembic/       migrations (see note in 0001_initial_schema.py)
  scripts/       seed_rbac.py, seed_demo_data.py
  tests/         pytest suite (sqlite-backed, no external services needed)
frontend/
  app/           Next.js App Router pages (login, dashboard, project detail)
  components/    MapView (MapLibre), CptChart (Recharts)
  lib/api.ts     typed fetch wrapper, cookie-based auth
docker-compose.yml   Postgres+PostGIS, MinIO, backend, frontend
```

## Running it locally

You'll need Docker. From the repo root:

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

This brings up Postgres/PostGIS, MinIO, the FastAPI backend (with Alembic
migrations and RBAC seeding run automatically), and the Next.js frontend at
http://localhost:3000. Seed demonstration data with:

```bash
docker compose exec backend python -m scripts.seed_demo_data
```

Then log in at http://localhost:3000/login with
`demo.engineer@pigl.example` / `DemoPass123!`.

### Running the backend tests

The test suite runs against an in-memory-equivalent sqlite file and needs no
Docker services:

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL="sqlite:///./test.db" python -m pytest tests/ -v
```

### A note on the first Alembic migration

This sandbox had no live Postgres instance to run
`alembic revision --autogenerate` against, so `0001_initial_schema.py` calls
`Base.metadata.create_all()` directly rather than hand-authoring 34
`op.create_table()` blocks (see the comment at the top of that file for the
full reasoning). **Every migration after this one should use real
autogenerate** against `docker compose up db`, so schema drift between
`app/models/` and the migration history gets caught the normal way.

## Next steps (in priority order)

1. Confirm this build against MVP Implementation Design Rev 2 — if PIGL
   wants any deviation from what's described above, that's the moment to
   flag it.
2. Give `docker compose up` a real run and regenerate the Alembic migration
   from a live Postgres connection.
3. Build the laboratory/CPT/VES file-upload + column-mapping wizard (item 5
   above) — this is the highest-value next increment for actually getting
   real project data in.
4. When PIGL Engineering approves the first methodology: add its
   specification as a `MethodologyVersion` row with `status = APPROVED`,
   register a calculation-implementation class in
   `calculation_engine._IMPLEMENTATIONS`, and add the reference-case,
   regression and boundary tests the Build Prompt requires. Nothing else in
   the gate needs to change.
5. When PIGL supplies GeoBrain's existing GPT configuration and the Draft
   Engineering Summary template: wire the orchestration loop in
   `app/geobrain/` and populate `ReportTemplate` content.
