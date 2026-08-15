"""
Shared audit-event writer.

Every mutating service call in every module is expected to call
record_event() as part of its own transaction (same db session, so the
audit row commits atomically with the change it describes). This keeps
audit writing centralized in one function, per Implementation Design Rev 1
§17 ("written internally... never posted directly by API clients").
"""
import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def record_event(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: str | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        event_metadata=metadata,
    )
    db.add(event)
    return event
