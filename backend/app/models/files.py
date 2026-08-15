"""
Dataset / File — provenance and object-storage records.

Dataset composes Project + Investigation + Source Type + Source File + Method +
Version + Processing Status + Validation Status + Approval Status (Architecture
§7). File records the S3-compatible object key; the actual bytes live in
object storage behind the storage abstraction (app/services/storage.py), never
referenced by a provider-specific path in application code.
"""
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import gen_uuid, utcnow


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    investigation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("files.id"), nullable=True)
    method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="RAW")
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVALIDATED")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNAPPROVED")
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)  # object key in the storage abstraction
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # S3 object version, if versioned
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
