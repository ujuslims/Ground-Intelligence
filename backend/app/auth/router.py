from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth.service import authenticate, logout
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.rbac import User
from app.schemas.auth import LoginRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    user, token = authenticate(db, payload.email, payload.password)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_ttl_minutes * 60,
    )
    return user


@router.post("/logout")
def logout_route(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Takes Request directly (rather than the get_current_user dependency)
    because it needs the raw cookie token to revoke the matching session
    row, not just the resolved User.
    """
    settings = get_settings()
    user = get_current_user(request, db)  # raises 401 if not authenticated
    token = request.cookies.get(settings.session_cookie_name)
    logout(db, token, user.id)
    response.delete_cookie(settings.session_cookie_name)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
