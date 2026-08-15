"""
Architecture-boundary tests.

These are deliberately NOT behavioral tests (they don't call an endpoint
and check a status code) -- they scan the codebase itself to catch a
specific class of regression: someone adding a dependency or import that
would quietly create a second path to the database/storage, bypassing the
single governance chokepoint the Implementation Design requires
(Rev 2 §J.1: "there is exactly one place in the codebase where this is
decided"). A behavioral test can't catch "a new file imported boto3
directly" -- only a structural check can, so that's what these are.

Honesty note (per PIGL's standing instruction not to overstate status):
these tests confirm the codebase *as committed* respects the boundary.
They cannot prove a live-deployed environment is configured correctly
(e.g. that no one manually wired a Supabase client into a Netlify
environment variable) -- that requires the live-infrastructure
verification stage, not a unit test.
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"
FRONTEND_DIR = REPO_ROOT / "frontend"


def _python_files(base: Path):
    return list(base.rglob("*.py"))


def test_boto3_is_only_imported_inside_storage_module():
    """
    Only app/core/storage.py may import boto3. If any other module needs
    object storage, it must go through StorageBackend / get_storage_backend
    -- not talk to S3/Supabase Storage/MinIO directly.
    """
    allowed_file = BACKEND_APP / "core" / "storage.py"
    offenders = []
    for path in _python_files(BACKEND_APP):
        if path == allowed_file:
            continue
        text = path.read_text()
        if re.search(r"^\s*(import boto3|from boto3)", text, re.MULTILINE):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"boto3 imported outside the storage abstraction: {offenders}"


def test_no_uncontrolled_schema_sync_in_application_code():
    """
    Migrations must go through Alembic (alembic/versions/), never through
    Base.metadata.create_all() at application runtime -- create_all() is
    only acceptable in the test suite itself, where it builds a throwaway
    in-memory SQLite schema per test run.
    """
    offenders = []
    for path in _python_files(BACKEND_APP):
        text = path.read_text()
        if "create_all(" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], (
        f"Base.metadata.create_all() found in application code (should only "
        f"appear in tests/conftest.py, which is outside app/): {offenders}"
    )


def test_database_engine_only_constructed_in_core_database_module():
    """
    Only app/core/database.py may call sqlalchemy.create_engine(). Every
    other module must obtain a session via the get_db dependency (or, in
    services, receive a Session parameter) -- never open its own
    connection, which would be a second, unaudited path to the database.
    """
    allowed_file = BACKEND_APP / "core" / "database.py"
    offenders = []
    for path in _python_files(BACKEND_APP):
        if path == allowed_file:
            continue
        text = path.read_text()
        if "create_engine(" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"create_engine() called outside app/core/database.py: {offenders}"


def test_frontend_has_no_direct_database_or_supabase_client_dependency():
    """
    The frontend must talk only to the FastAPI backend (see lib/api.ts).
    It must never depend on a Supabase client SDK, a Postgres driver, or
    any package that would let it query the database directly, bypassing
    RBAC/audit/the calculation gate.
    """
    package_json = FRONTEND_DIR / "package.json"
    data = json.loads(package_json.read_text())
    all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

    forbidden_substrings = ["supabase", "pg", "postgres", "@prisma/client", "knex", "mysql"]
    offenders = [
        name for name in all_deps
        if any(forbidden in name.lower() for forbidden in forbidden_substrings)
    ]
    assert offenders == [], f"frontend depends on a direct-database/Supabase package: {offenders}"


def test_frontend_api_client_always_targets_the_backend_env_var():
    """
    Confirms lib/api.ts reads its base URL from NEXT_PUBLIC_API_URL (the
    FastAPI backend) rather than a hard-coded Supabase project URL or any
    other data endpoint.

    Note: the file's doc-comment intentionally mentions "Supabase" in
    prose (explaining that it is NOT used here) -- that is documentation
    of the boundary, not a violation of it. This check therefore looks for
    actual client usage/URLs, not the bare word.
    """
    api_client = FRONTEND_DIR / "lib" / "api.ts"
    text = api_client.read_text()
    assert "NEXT_PUBLIC_API_URL" in text
    forbidden_patterns = ["createClient(", "supabase.co", "@supabase/", "SUPABASE_URL", "SUPABASE_ANON_KEY"]
    offenders = [pat for pat in forbidden_patterns if pat in text]
    assert offenders == [], f"lib/api.ts appears to reference a Supabase client directly: {offenders}"


def test_entrypoint_fails_fast_on_blank_database_url():
    """
    Regression test for a real production incident: the first live Render
    deploy crashed with a cryptic SQLAlchemy traceback
    ("Could not parse SQLAlchemy URL from given URL string") because
    GI_DATABASE_URL was blank when the container started. Root-caused by
    reproducing the exact error locally: an empty/whitespace-only string
    is what triggers that specific message, not the unencoded-special-
    character password originally suspected.

    docker-entrypoint.sh now checks for this before running Alembic at
    all, so the failure is a clear one-paragraph message instead of a
    Python stack trace. This test checks the guard clause is still
    present in the script (a change to docker-entrypoint.sh that quietly
    removed it wouldn't be caught by any Python-level test otherwise).
    """
    entrypoint = REPO_ROOT / "backend" / "docker-entrypoint.sh"
    text = entrypoint.read_text()
    assert 'if [ -z "$GI_DATABASE_URL" ]' in text
    assert "exit 1" in text


def test_cors_allows_configured_frontend_origin_and_rejects_others():
    """
    Regression test for a real production incident: login failed from the
    live Netlify frontend with a generic 'Login failed' message (not a
    'wrong password' message), because the backend had no CORS
    configuration at all -- the browser was blocking every cross-origin
    request before the app ever saw it. Verified directly by inspecting
    response headers with an Origin header set, the same way a browser's
    preflight/actual request would look, rather than assuming the fix
    works from reading the code.
    """
    import os

    os.environ["GI_CORS_ALLOWED_ORIGINS"] = "https://ground-intelligence.netlify.app"
    # FastAPI app is constructed at import time in app.main; the CORS
    # middleware reads settings via get_settings(), which is lru_cached,
    # so re-import in a subprocess-free way isn't reliable here. This test
    # instead builds a fresh app instance directly via create_app() after
    # clearing the settings cache, which is the supported way to test
    # config-dependent app construction.
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    from starlette.testclient import TestClient as StarletteTestClient

    client = StarletteTestClient(app)

    allowed = client.options(
        "/auth/login",
        headers={
            "Origin": "https://ground-intelligence.netlify.app",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "https://ground-intelligence.netlify.app"
    assert allowed.headers.get("access-control-allow-credentials") == "true"

    blocked = client.options(
        "/auth/login",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "POST"},
    )
    assert blocked.headers.get("access-control-allow-origin") is None

    get_settings.cache_clear()
    os.environ.pop("GI_CORS_ALLOWED_ORIGINS", None)


def test_geobrain_module_not_yet_present_boundary_still_documented():
    """
    GeoBrain (Phase 5-6 scope) does not exist in this codebase yet, so
    there is nothing to statically scan for a gate-bypass today. This test
    exists as a deliberate trip-wire: once app/geobrain/ is created, this
    test must be rewritten to assert that GeoBrain's tool functions call
    the same service-layer functions (e.g. app.projects.service,
    app.core.deps) as the REST routers do, rather than opening their own
    database session or importing app.core.storage's boto3 client
    directly. Leaving this documented now, rather than silently skipping
    it, is intentional -- it is easy to forget an architectural boundary
    test when the module it protects finally gets built under deadline
    pressure.
    """
    geobrain_dir = BACKEND_APP / "geobrain"
    if geobrain_dir.exists():
        raise AssertionError(
            "app/geobrain/ now exists but this boundary test was never "
            "rewritten to check it. Do not merge GeoBrain code without "
            "updating this test to verify it cannot bypass RBAC/audit/the "
            "calculation gate (see docstring)."
        )
