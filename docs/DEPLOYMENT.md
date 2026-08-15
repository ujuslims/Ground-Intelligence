# Ground Intelligence — Backend Deployment

**Status of this document: configuration finalized, NOT yet exercised against a live host.** Everything below describes what will run once a host is actually connected; it is not a claim that a deployment has happened.

## Cost — MVP configuration (zero budget)

`render.yaml` is configured with `plan: free`. Render's free web-service tier requires **no credit card** and gives 750 hours/month — enough for one instance running continuously, all month, for $0. The trade-off: the instance sleeps after 15 minutes of inactivity, and the first request after sleep takes 30–60 seconds to respond. For an MVP with no traffic yet and no budget, this is the right trade to make — do not upgrade to a paid plan until there's an actual reason to (real users who'd notice the cold-start delay, or a budget approved for it).

**If Render still prompts for a credit card despite `plan: free`:** this has been reported by some users even on genuinely free usage — it appears to be an account-level fraud check on Render's side in some cases, not a hidden cost. If it happens, don't enter a card; tell me and we'll move to one of the zero-cost fallbacks below rather than assume you have to pay.

**Zero-cost fallbacks, if Render's free tier doesn't work out:**
- **Fly.io** — has a free usage allowance, but requires a card on file even to stay within it (it just won't charge you if you stay under the limit). Not recommended here specifically because your stated constraint is avoiding payment friction entirely, not just avoiding charges.
- **Self-hosting** — run the Docker container on your own always-on machine, exposed via a free Cloudflare Tunnel (no card, no time limit, but the app is only "live" while your machine is on and connected). A legitimate zero-cost option for an internal MVP demo, not a real production posture.

The rest of this document (Dockerfile, migration-on-deploy behavior, required environment variables) is unchanged by the plan choice.

## Recommended host: Render

**Why Render over the alternatives (Fly.io, Railway, a plain VM):**

| | Render | Fly.io | Railway | Plain VM |
|---|---|---|---|---|
| Runs a persistent Docker container (required — Netlify/serverless cannot host FastAPI, see `docs/INFRASTRUCTURE_DECISIONS.md`) | Yes | Yes | Yes | Yes |
| Setup complexity for a small team | Low — connect repo, confirm blueprint | Medium — CLI-driven, more knobs | Low | High — you manage the OS |
| Built-in health checks, zero-downtime deploys | Yes | Yes (needs config) | Yes | Manual |
| Cost at MVP/pilot scale | **$0 on the free tier** (750 hrs/mo, no card required, sleeps after 15 min idle — see cost note below); ~$7–25/mo once you outgrow it | Requires a card on file even for free usage | ~$5–20/mo, free trial credit only ($5, expires) | Variable, plus your time |
| Matches "avoid unnecessary infrastructure complexity" (PIGL Development Discipline) | Yes | More moving parts than needed here | Yes | No — most complexity of all three |

Render is the recommendation. Railway is a reasonable second choice if you specifically prefer its UI. Fly.io and a plain VM are not recommended for this project — more operational surface than an MVP with a small team needs.

## What ships to the host

- `backend/Dockerfile` — production image. Runs as non-root, installs pinned dependencies from `requirements.txt`.
- `backend/docker-entrypoint.sh` — runs `alembic upgrade head`, then starts `uvicorn`. **This is the only way the production schema changes.** There is no `create_all()`/auto-sync path anywhere in application code — enforced by an automated test (`tests/test_architecture_boundaries.py::test_no_uncontrolled_schema_sync_in_application_code`), not just by convention.
- `render.yaml` — Render Blueprint describing the service shape. Contains **no secret values** — every credential is marked `sync: false`, meaning Render prompts for it in the dashboard and stores it encrypted; nothing is written to this file or committed to Git.

## Required environment variables (set in the host's dashboard, never in source)

| Variable | What it is | Source |
|---|---|---|
| `GI_DATABASE_URL` | Supabase Postgres connection string | Supabase dashboard → Project Settings → Database → Connection string |
| `GI_COOKIE_SECURE` | `true` in production (HTTPS-only cookies) | Fixed value |
| `GI_STORAGE_BUCKET`, `GI_STORAGE_ENDPOINT_URL`, `GI_STORAGE_REGION`, `GI_STORAGE_ACCESS_KEY`, `GI_STORAGE_SECRET_KEY` | Supabase Storage S3-compatible credentials | Supabase dashboard → Storage → S3 Connection |
| `GI_BOOTSTRAP_ADMIN_EMAIL`, `GI_BOOTSTRAP_ADMIN_PASSWORD` | First administrator account, created by `app/seed.py` | Chosen by whoever runs the first deploy |

Full variable reference with inline explanation: `backend/.env.example`.

## Deploy flow (once a host is connected)

1. Push to `main` on GitHub.
2. `.github/workflows/backend-ci.yml` runs the Alembic migration and full test suite against a real ephemeral Postgres container. This must pass before anyone deploys — it is a correctness gate, not a deployment step itself.
3. The host (Render or whichever is chosen) builds `backend/Dockerfile` and starts the container.
4. `docker-entrypoint.sh` runs `alembic upgrade head` against the real `GI_DATABASE_URL` (Supabase), then starts serving traffic. If the migration fails, the container does not start — it cannot silently serve against a stale schema.
5. `GET /health` is the host's health-check endpoint.

## Known incident: CORS and cross-site cookies (frontend on Netlify, backend on Render)

**What happened:** logging in from the live Netlify frontend showed a generic "Login failed" message rather than a specific error.

**Root cause, confirmed by direct reproduction, not guessed:** the backend had no CORS configuration at all. Verified by sending a request with an `Origin` header set (the same way a browser does) and inspecting the response headers directly — no `Access-Control-Allow-Origin` header was present, which means the browser blocks the request client-side before the app's response is ever read. That surfaces to `fetch()` as a generic network failure, which is exactly the frontend's fallback "Login failed" message (see `frontend/app/login/page.tsx`) — not the specific "Invalid email or password" the backend would have sent if the request had actually reached it.

**Fix applied:**
- `app/main.py` now adds `CORSMiddleware`, restricted to the exact origin(s) in `GI_CORS_ALLOWED_ORIGINS` (required, since `allow_credentials=True` means a wildcard `*` origin is not permitted by browsers). Verified directly: a request with the configured origin gets the CORS header back; a request with a different origin does not. Covered by `tests/test_architecture_boundaries.py::test_cors_allows_configured_frontend_origin_and_rejects_others`.
- **A second, related issue that would have surfaced immediately after fixing CORS:** the session cookie was configured with `SameSite=Lax`, which browsers only send on top-level navigations for cross-site requests — not on the `fetch()`/XHR calls this frontend makes. Login would have appeared to succeed (a `Set-Cookie` response is received) but every subsequent request (`/auth/me`, `/projects`) would silently fail with 401, because the cookie would never actually be sent back. Fixed by setting `GI_COOKIE_SAMESITE=none` in `render.yaml` (this requires `GI_COOKIE_SECURE=true`, which was already set).

**Required environment variables added this stage:**
| Variable | Where | Value |
|---|---|---|
| `GI_CORS_ALLOWED_ORIGINS` | Render | Your Netlify site's exact URL, no trailing slash |
| `GI_COOKIE_SAMESITE` | Render | `none` (changed from `lax`) |

**If your Render service was created before this fix:** these won't apply automatically — `render.yaml` changes only affect new deploys/blueprint syncs. Go to Render → your service → Environment tab, add `GI_CORS_ALLOWED_ORIGINS` manually, change `GI_COOKIE_SAMESITE` to `none`, save, then trigger Manual Deploy.

## Known incident: Row Level Security disabled on a shared Supabase project

**What happened:** the Supabase project used for Ground Intelligence is shared with a pre-existing, unrelated production application (a consumer delivery app, reused due to Supabase's free-tier project limits — see `docs/INFRASTRUCTURE_DECISIONS.md`). Supabase's security advisor flagged, at `ERROR` severity, that all 11 Ground Intelligence tables had Row Level Security disabled while being exposed through Supabase's PostgREST/GraphQL API to the `anon` and `authenticated` roles — meaning anyone with the project's public API key could have read or written `users`, `audit_events`, `roles`, etc. directly, bypassing FastAPI entirely.

**Root cause:** Ground Intelligence's Alembic migrations create tables but never touch Postgres's RLS settings, and Supabase enables PostgREST/GraphQL access to every `public` schema table by default regardless of whether the owning application intends to use that API layer. Ground Intelligence never does — FastAPI connects directly via a plain Postgres connection string — so this was pure unintended exposure, not something anyone configured on purpose.

**Fix applied (with explicit user confirmation before execution):**
1. `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` was applied immediately to the live Supabase project for all 11 tables, with zero policies attached — this fully blocks anon/authenticated API access while having no effect on FastAPI's direct connection. Verified via Supabase's own advisor before/after: the 11 `ERROR`-level "RLS Disabled" findings became `INFO`-level "RLS Enabled No Policy" (expected and correct), and table row counts were confirmed unchanged.
2. The same change was added as a proper, reversible Alembic migration (`00611254f57b_enable_rls_phase1_tables.py`) rather than left as an untracked manual exception, so it's applied automatically to any future environment. It safely no-ops on non-Postgres dialects (e.g. the SQLite test suite).

**Residual, lower-severity items intentionally left alone:** Supabase's advisor also flagged `WARN`-level GraphQL schema-visibility notices and a `SECURITY DEFINER` function warning (`handle_new_user`) — the latter belongs to the pre-existing unrelated application, not Ground Intelligence, and was not touched.

## Known incident: blank `GI_DATABASE_URL` on first Render Blueprint deploy

**What happened:** the first live deploy attempt failed at container start with `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string`.

**Root cause, confirmed by direct reproduction (not guessed):** that specific error message is produced by SQLAlchemy's URL parser only when the input is empty, whitespace-only, or unset. Several other plausible causes were tested and ruled out — unencoded special characters in a Supabase-generated password (`@`, `!`, `#`) all parsed correctly in this SQLAlchemy version. The actual cause was that `GI_DATABASE_URL` was blank when the container started, most likely because Render's Blueprint flow created and started the service before the secret values entered in the initial setup form were fully attached to it — a known rough edge with Render Blueprints, not a mistake in what was typed.

**Fix applied:** `docker-entrypoint.sh` now checks for a blank `GI_DATABASE_URL` before attempting anything else, and fails with a one-paragraph actionable message instead of a Python stack trace. Covered by `tests/test_architecture_boundaries.py::test_entrypoint_fails_fast_on_blank_database_url`.

**If you hit this:** go to Render → your service → **Environment** tab (not the initial Blueprint setup form — the tab on the running service), confirm `GI_DATABASE_URL` actually has a value, re-enter it if blank, save, then trigger **Manual Deploy**.

## What this document does NOT claim
- That a Render (or any) service currently exists for this project.
- That the migration has been run against a live Supabase database.
- That any of this has been exercised end-to-end outside CI's ephemeral Postgres container.

Those are live-infrastructure-verification steps, tracked separately, and require the manual setup checklist to be completed first.
