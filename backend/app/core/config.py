"""
Application configuration.

Values are read from environment variables so nothing environment-specific
(database credentials, storage credentials, cookie security flags) is
hard-coded. See infra/docker-compose.yml and .env.example for local dev.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GI_", extra="ignore")

    # --- General ---
    environment: str = "development"  # development | production | test
    app_name: str = "Ground Intelligence"

    # --- Database ---
    # Production/staging target: Supabase-managed PostgreSQL (+ PostGIS
    # extension, enabled per-project in the Supabase dashboard, used
    # starting with the Investigation/Location phase). Supabase is
    # approved ONLY as managed Postgres/PostGIS infrastructure -- this
    # application still owns the schema (Alembic), all queries (SQLAlchemy,
    # through the service layer in each module), RBAC, audit and the
    # engineering-calculation gate. Nothing else connects to Supabase:
    # no direct client-side (frontend or GeoBrain) database access, no
    # PostgREST/Supabase client SDK, no Supabase Auth. See
    # docs/INFRASTRUCTURE_DECISIONS.md.
    #
    # database_url is the standard Postgres connection string Supabase
    # provides under Project Settings -> Database -> Connection string
    # (session pooler or direct connection; both are plain postgresql://,
    # no Supabase-specific driver required). SQLite is used only for the
    # Phase-1 automated test suite (see tests/conftest.py); it is never
    # used to serve real traffic.
    database_url: str = "postgresql+psycopg2://gi:gi@localhost:5432/ground_intelligence"

    # --- Sessions / auth ---
    # Server-managed sessions per Implementation Design Rev 2 §I.1:
    # HTTP-only cookie, Secure in production, SameSite=Lax, session state
    # persisted server-side (in the database), never a client-held JWT.
    session_cookie_name: str = "gi_session"
    session_ttl_minutes: int = 60 * 12  # 12 hours
    session_idle_timeout_minutes: int = 60 * 2  # 2 hours of inactivity
    cookie_secure: bool = False  # set True in production (HTTPS only)
    # SameSite=Lax is fine for local dev (browsers treat localhost leniently)
    # but breaks a real deployment where the frontend (Netlify) and backend
    # (Render) are on different domains: a Lax cookie is not sent on
    # cross-site fetch()/XHR requests, only on top-level navigations. Set
    # this to "none" in production -- which requires cookie_secure=True,
    # since browsers reject SameSite=None cookies that aren't Secure.
    cookie_samesite: str = "lax"

    # --- CORS ---
    # The frontend (Netlify) and backend (Render) are different origins in
    # any real deployment, so the backend must explicitly allow the
    # frontend's origin -- otherwise the browser blocks every request
    # before the app ever sees it, which is exactly what was happening
    # here (a blocked CORS request surfaces to the frontend as a generic
    # network failure, not a 401). allow_credentials requires an explicit
    # origin, not "*" -- browsers refuse wildcard origins when credentials
    # (cookies) are involved, so this must be the frontend's real URL.
    cors_allowed_origins: str = "http://localhost:3000"  # comma-separated if more than one

    # --- Object storage (S3-compatible abstraction, Rev 2 §I.2) ---
    # Approved providers behind this abstraction: AWS S3 (production
    # default per Rev 2 §I.2) or Supabase Storage's S3-compatible API
    # (approved as an alternative managed-infra choice -- see
    # docs/INFRASTRUCTURE_DECISIONS.md). Either way the application talks
    # only to app.core.storage.StorageBackend; no module imports boto3 or
    # a Supabase SDK directly. For Supabase Storage, storage_endpoint_url
    # is the project's S3-compatible endpoint
    # (https://<project-ref>.supabase.co/storage/v1/s3) and
    # storage_access_key/secret_key are the S3 access keys generated under
    # Storage -> S3 Connection in the Supabase dashboard.
    storage_provider: str = "s3"  # only supported value in MVP; abstraction allows others later
    storage_bucket: str = "ground-intelligence-dev"
    storage_endpoint_url: str | None = "http://localhost:9000"  # MinIO locally; Supabase/AWS endpoint in deployed envs
    storage_region: str = "us-east-1"
    storage_access_key: str | None = None
    storage_secret_key: str | None = None

    # --- GeoBrain LLM provider (abstraction; not wired to a live model in Phase 1) ---
    geobrain_llm_provider: str = "anthropic"
    geobrain_llm_model: str = "claude-sonnet-4-6"


@lru_cache
def get_settings() -> Settings:
    return Settings()
