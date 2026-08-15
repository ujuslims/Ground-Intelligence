import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.core.config import get_settings
from app.core.security import (
    generate_session_token,
    hash_token,
    new_expiry,
    verify_password,
)
from app.models.rbac import User, UserSession


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    """
    Returns (user, raw_session_token) on success. Raises 401 on failure.
    Intentionally returns the same error for 'no such user' and 'wrong
    password' so login does not leak which emails are registered.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None or user.status != "ACTIVE" or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    settings = get_settings()
    token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=new_expiry(settings.session_ttl_minutes),
    )
    db.add(session)
    record_event(db, user_id=user.id, action="LOGIN", object_type="User", object_id=str(user.id))
    db.commit()
    return user, token


def logout(db: Session, raw_token: str, user_id: uuid.UUID) -> None:
    token_hash = hash_token(raw_token)
    session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    if session is not None:
        session.revoked = True
    record_event(db, user_id=user_id, action="LOGOUT", object_type="User", object_id=str(user_id))
    db.commit()
