"""
S3-compatible object storage abstraction (Rev 2 §I.2).

Amazon S3 in production, MinIO (or equivalent) in local development -- both
speak the S3 API, so this is the ONLY module in the codebase that imports
boto3. Application code elsewhere calls StorageService methods and never
touches a provider-specific SDK directly.
"""
import uuid

import boto3
from botocore.client import Config as BotoConfig

from app.core.config import get_settings


class StorageService:
    def __init__(self):
        settings = get_settings()
        self._bucket = settings.STORAGE_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.STORAGE_ENDPOINT_URL,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
            region_name=settings.STORAGE_REGION,
            config=BotoConfig(signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            self._client.create_bucket(Bucket=self._bucket)

    def put_object(self, *, project_id: str, filename: str, content: bytes, content_type: str | None) -> tuple[str, str | None]:
        """Returns (storage_key, version_id)."""
        key = f"projects/{project_id}/{uuid.uuid4()}-{filename}"
        extra = {"ContentType": content_type} if content_type else {}
        resp = self._client.put_object(Bucket=self._bucket, Key=key, Body=content, **extra)
        return key, resp.get("VersionId")

    def get_object(self, storage_key: str, version_id: str | None = None) -> bytes:
        kwargs = {"Bucket": self._bucket, "Key": storage_key}
        if version_id:
            kwargs["VersionId"] = version_id
        return self._client.get_object(**kwargs)["Body"].read()

    def presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": storage_key}, ExpiresIn=expires_in
        )


from functools import lru_cache


@lru_cache
def get_storage_service() -> "StorageService":
    """Lazy singleton -- avoids requiring valid S3/MinIO connection details
    just to import the app (e.g. for schema-only tooling, migrations)."""
    return StorageService()
