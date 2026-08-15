"""
Shared ORM mixins.

ProvenanceMixin/TimestampMixin are used by every Phase-1 entity that the
Implementation Design requires to carry provenance/audit fields. Entities
belonging to later phases (Investigation, Dataset, Calculation, etc.) are
not defined yet -- they are out of Phase-1 scope and will get their own
mixins (VersionedMixin, source-type fields) when Phase 2+ begins.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
