import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import utcnow


class AuditEvent(Base):
    """
    Rev 1 §17 / PIGL Final Authorization §8: append-only audit trail.
    Rows are written only by app.core.audit.record_event(); there is no
    API path that lets a client POST an AuditEvent directly (see
    app/admin/router.py -- audit is exposed read-only).
    """
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    object_type: Mapped[str] = mapped_column(String(128), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
