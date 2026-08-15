"""Audit trail service. Every mutating endpoint should call log_event()."""
import json

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def log_event(db: Session, *, user_id: str | None, action: str, object_type: str | None = None,
              object_id: str | None = None, metadata: dict | None = None) -> AuditEvent:
    event = AuditEvent(
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        event_metadata=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
