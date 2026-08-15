"""
Password hashing and session-token helpers.

Session tokens: a random 256-bit token is generated, its SHA-256 hash is
stored in user_sessions.token_hash, and only the raw token is placed in the
cookie. This mirrors normal server-session hygiene (never store the
usable secret; store a hash you can compare against) and means a database
read alone can't be replayed as a valid session cookie.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_expiry(minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
