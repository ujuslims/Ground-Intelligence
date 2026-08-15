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
