"""
Password hashing and session token generation.

Rev 2 §I.1: password hashing via bcrypt; session identifiers are opaque random
tokens (never JWTs the client could decode/trust), stored server-side.
"""
import secrets

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(48)
