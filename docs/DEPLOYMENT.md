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

## What this document does NOT claim

- That a Render (or any) service currently exists for this project.
- That the migration has been run against a live Supabase database.
- That any of this has been exercised end-to-end outside CI's ephemeral Postgres container.

Those are live-infrastructure-verification steps, tracked separately, and require the manual setup checklist to be completed first.
