from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, new_session_token
from app.models.identity import User, Session as SessionModel
from app.schemas.auth import LoginRequest, UserOut
from app.services.audit import log_event

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = new_session_token()
    now = datetime.now(timezone.utc)
    session = SessionModel(
        id=token,
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(minutes=settings.SESSION_TTL_MINUTES),
    )
    db.add(session)
    db.commit()

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_TTL_MINUTES * 60,
    )
    log_event(db, user_id=user.id, action="LOGIN", object_type="USER", object_id=user.id)
    return user


@router.post("/logout")
def logout(response: Response, request_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    log_event(db, user_id=request_user.id, action="LOGOUT", object_type="USER", object_id=request_user.id)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
