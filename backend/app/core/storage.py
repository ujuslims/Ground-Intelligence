"""
Storage abstraction (Implementation Design Rev 2 §I.2).

StorageBackend is the interface every other module is expected to depend
on. S3StorageBackend is the only implementation in the MVP (targets AWS S3
in production, MinIO locally, both via the same S3-compatible boto3
client) -- but no calling code should import boto3 directly; it should
depend on get_storage_backend()/StorageBackend so a different provider
could be substituted later without touching callers.

Not yet wired into any domain module in Phase 1 (no file-upload endpoints
exist yet -- that starts with the Files module in a later phase). This
file exists now so the interface is fixed before any module starts
depending on it, per the module boundary in Implementation Design Rev 1 §3.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig

from app.core.config import get_settings


@dataclass
class StoredObjectMetadata:
    key: str
    bucket: str
    size: int
    checksum: str | None = None


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str | None = None) -> StoredObjectMetadata: ...

    @abc.abstractmethod
    def get_object(self, key: str) -> bytes: ...

    @abc.abstractmethod
    def delete_object(self, key: str) -> None: ...

    @abc.abstractmethod
    def object_exists(self, key: str) -> bool: ...


class S3StorageBackend(StorageBackend):
    def __init__(self, bucket: str, endpoint_url: str | None, region: str,
                 access_key: str | None, secret_key: str | None):
        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
        )

    def put_object(self, key: str, data: bytes, content_type: str | None = None) -> StoredObjectMetadata:
        kwargs = {"Bucket": self.bucket, "Key": key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        self._client.put_object(**kwargs)
        return StoredObjectMetadata(key=key, bucket=self.bucket, size=len(data))

    def get_object(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def object_exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self._client.exceptions.ClientError:
            return False


@lru_cache
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_provider != "s3":
        raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")
    return S3StorageBackend(
        bucket=settings.storage_bucket,
        endpoint_url=settings.storage_endpoint_url,
        region=settings.storage_region,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key,
    )
