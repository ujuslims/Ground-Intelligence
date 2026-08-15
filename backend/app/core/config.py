"""
Application configuration.

Per Ground Intelligence MVP Implementation Design Rev 2, §I:
- Auth: server-managed sessions (HTTP-only cookies), PostgreSQL-backed session store.
- Storage: S3-compatible (Amazon S3 in production, MinIO in local dev) behind an
  internal storage abstraction (see app/services/storage.py). No provider-specific
  calls elsewhere in the application.
- Default GeoBrain LLM provider: Anthropic Claude, Sonnet-class, behind a model
  abstraction layer (see app/geobrain/llm_provider.py). This is a configuration
  value, not a hard-coded constant.

None of these values encode any engineering methodology, standard, or calculation
content. Configuration only.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Ground Intelligence"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+psycopg2://gi:gi@localhost:5432/ground_intelligence"

    SESSION_COOKIE_NAME: str = "gi_session"
    SESSION_TTL_MINUTES: int = 12 * 60
    SESSION_IDLE_TIMEOUT_MINUTES: int = 60
    SESSION_COOKIE_SECURE: bool = False  # set True in production (HTTPS only)
    SESSION_COOKIE_SAMESITE: str = "lax"
    SECRET_KEY: str = "change-me-in-production"

    # Storage abstraction (S3-compatible). Amazon S3 in production, MinIO locally.
    STORAGE_ENDPOINT_URL: str | None = "http://localhost:9000"
    STORAGE_BUCKET: str = "ground-intelligence-files"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_REGION: str = "us-east-1"

    # GeoBrain default model provider — configuration value, not hard-coded logic.
    # Provider independence is preserved by the abstraction layer in geobrain/llm_provider.py.
    GEOBRAIN_LLM_PROVIDER: str = "anthropic"
    GEOBRAIN_LLM_MODEL: str = "claude-sonnet-4-5"
    ANTHROPIC_API_KEY: str | None = None

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
