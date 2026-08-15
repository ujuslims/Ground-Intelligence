"""
Test fixtures.

Uses an in-memory SQLite database per test (via StaticPool so the same
in-memory DB is shared across connections within one test). This is a
Phase-1 test-only substitute for Postgres -- see app/core/config.py's
comment on database_url. No Postgres-only features (PostGIS, etc.) are
used by any Phase-1 model, so this is a faithful test of the schema.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  ensure all models are registered
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.rbac import Role, User
from app.seed import seed


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db_session):
    """Seeds roles/permissions/matrix (not the bootstrap admin, which needs env vars)."""
    seed(db_session)
    return db_session


def make_user(db_session, email="user@example.com", password="testpass123", global_role_code=None):
    global_role_id = None
    if global_role_code:
        role = db_session.query(Role).filter(Role.code == global_role_code).first()
        global_role_id = role.id
    user = User(email=email, name="Test User", password_hash=hash_password(password), global_role_id=global_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def role_id(db_session, code) -> uuid.UUID:
    return db_session.query(Role).filter(Role.code == code).first().id
