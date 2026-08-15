from datetime import datetime

from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import gen_uuid, utcnow


class AuditEvent(Base):
    """Recorded for: login, project creation/modification, file upload, data
    import, validation, processing, calculation, review, approval, report
    generation, report revision (Architecture §23, Tech Spec §43)."""
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    object_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    event_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
