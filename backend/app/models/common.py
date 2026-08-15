"""
Shared enums and mixins.

Provenance / data-state vocabulary is fixed by the MVP Data Model (§21) and the
Controlled Revision (Amendment 3): RAW, IMPORTED, VALIDATED, PROCESSED, DERIVED,
INTERPRETED, APPROVED. These states must never be collapsed into one
undifferentiated "result" field, and provenance columns are non-nullable at the
schema level from the first migration (Data Model Controlled Revision §3).
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DataState(str, enum.Enum):
    RAW = "RAW"
    IMPORTED = "IMPORTED"
    VALIDATED = "VALIDATED"
    PROCESSED = "PROCESSED"
    DERIVED = "DERIVED"
    INTERPRETED = "INTERPRETED"
    APPROVED = "APPROVED"


class SourceType(str, enum.Enum):
    """PRD §7 — three source categories."""
    NATIVE_GROUND_INTELLIGENCE = "NATIVE_GROUND_INTELLIGENCE"
    PIGL_INTERNAL_EXTERNAL_PROCESSING = "PIGL_INTERNAL_EXTERNAL_PROCESSING"
    EXTERNAL_THIRD_PARTY = "EXTERNAL_THIRD_PARTY"


class ProvenanceMixin:
    """
    Mandatory provenance columns per Data Model Controlled Revision §3.
    Every entity carrying investigation/engineering data must record where it
    came from, who touched it, and what state it is in. These columns are
    intentionally NOT nullable — provenance is a first-class constraint, not
    optional metadata.
    """
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DataState.RAW.value)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
