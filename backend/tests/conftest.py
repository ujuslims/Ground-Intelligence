import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine, SessionLocal
from app import models  # noqa: F401
from app.main import app
from app.core.security import hash_password
from app.models.identity import User, Role, Permission, RolePermission, ProjectMembership
from app.models.project import Organization, Project


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def seeded(db_session):
    """Seeds one ENGINEER role/permission, one org, one user, one project
    with the user already a member -- the minimum fixture for auth + project
    + calculation-gate tests."""
    from scripts.seed_rbac import seed
    seed()

    org = Organization(name="PIGL Demo Org")
    db_session.add(org)
    db_session.flush()

    user = User(email="engineer@example.com", full_name="Demo Engineer", password_hash=hash_password("password123"))
    user.organization_id = org.id
    db_session.add(user)
    db_session.flush()

    engineer_role = db_session.query(Role).filter_by(name="ENGINEER").first()

    project = Project(organization_id=org.id, name="Demo Project", created_by=user.id)
    db_session.add(project)
    db_session.flush()
    db_session.add(ProjectMembership(project_id=project.id, user_id=user.id, role_id=engineer_role.id))
    db_session.commit()

    return {"org": org, "user": user, "project": project}
