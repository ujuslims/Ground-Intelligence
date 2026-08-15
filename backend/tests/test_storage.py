"""
IMPORTANT LIMITATION (reported honestly rather than glossed over):

This test suite runs in an environment with no live S3 or MinIO endpoint
reachable, so these tests verify only the storage ABSTRACTION -- that
get_storage_backend() wires up correctly and that an unsupported provider
is rejected. They do NOT verify that put_object/get_object/delete_object
actually work against a real S3-compatible service. That requires a MinIO
container (see infra/docker-compose.yml) and should be run as an
integration test before Phase 1 is considered fully verified, not just
unit-tested.
"""
import pytest

from app.core.config import Settings
from app.core.storage import S3StorageBackend, get_storage_backend


def test_s3_backend_constructs_without_network_call():
    backend = S3StorageBackend(
        bucket="test-bucket",
        endpoint_url="http://localhost:9000",
        region="us-east-1",
        access_key="test",
        secret_key="test",
    )
    assert backend.bucket == "test-bucket"


def test_get_storage_backend_rejects_unsupported_provider(monkeypatch):
    from app.core import storage as storage_module

    storage_module.get_storage_backend.cache_clear()

    bad_settings = Settings(storage_provider="azure_blob")
    monkeypatch.setattr(storage_module, "get_settings", lambda: bad_settings)

    with pytest.raises(ValueError):
        storage_module.get_storage_backend()

    storage_module.get_storage_backend.cache_clear()
