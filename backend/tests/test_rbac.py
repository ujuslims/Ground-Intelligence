from app.models.org import Client, Organization
from app.models.project import Project
from app.models.rbac import ProjectMembership
from tests.conftest import make_user, role_id


def _login(client, email, password):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp


def _make_project(db_session, code="PRJ-001"):
    org = Organization(name="Polaris Integrated & Geosolutions Limited")
    db_session.add(org)
    db_session.flush()
    c = Client(name="Demo Client", organization_id=org.id)
    db_session.add(c)
    db_session.flush()
    project = Project(project_code=code, name="Demo Project", client_id=c.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_user_without_global_role_cannot_create_project(client, db_session, seeded):
    make_user(db_session, email="engineer@example.com", password="testpass123")
    _login(client, "engineer@example.com", "testpass123")

    resp = client.post(
        "/projects",
        json={"project_code": "NEW-1", "name": "New Project", "client_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert resp.status_code == 403


def test_administrator_can_create_project(client, db_session, seeded):
    admin = make_user(db_session, email="admin@example.com", password="testpass123", global_role_code="ADMINISTRATOR")
    org = Organization(name="Org")
    db_session.add(org)
    db_session.flush()
    c = Client(name="Client", organization_id=org.id)
    db_session.add(c)
    db_session.commit()
    _login(client, "admin@example.com", "testpass123")

    resp = client.post("/projects", json={"project_code": "ADM-1", "name": "Admin Project", "client_id": str(c.id)})

    assert resp.status_code == 201, resp.text
    assert resp.json()["project_code"] == "ADM-1"


def test_project_creator_automatically_gets_membership(client, db_session, seeded):
    make_user(db_session, email="admin2@example.com", password="testpass123", global_role_code="ADMINISTRATOR")
    org = Organization(name="Org2")
    db_session.add(org)
    db_session.flush()
    c = Client(name="Client2", organization_id=org.id)
    db_session.add(c)
    db_session.commit()
    _login(client, "admin2@example.com", "testpass123")

    create_resp = client.post("/projects", json={"project_code": "ADM-2", "name": "P", "client_id": str(c.id)})
    project_id = create_resp.json()["id"]

    get_resp = client.get(f"/projects/{project_id}")
    assert get_resp.status_code == 200

    list_resp = client.get("/projects")
    assert list_resp.status_code == 200
    assert any(p["id"] == project_id for p in list_resp.json())


def test_user_without_membership_cannot_read_project(client, db_session, seeded):
    project = _make_project(db_session)
    make_user(db_session, email="outsider@example.com", password="testpass123")
    _login(client, "outsider@example.com", "testpass123")

    resp = client.get(f"/projects/{project.id}")

    assert resp.status_code == 404  # membership check surfaces as not-found, not 403 -- avoids confirming existence


def test_engineer_with_membership_can_read_project(client, db_session, seeded):
    project = _make_project(db_session, code="PRJ-002")
    engineer = make_user(db_session, email="eng2@example.com", password="testpass123")
    db_session.add(
        ProjectMembership(project_id=project.id, user_id=engineer.id, role_id=role_id(db_session, "ENGINEER"))
    )
    db_session.commit()
    _login(client, "eng2@example.com", "testpass123")

    resp = client.get(f"/projects/{project.id}")

    assert resp.status_code == 200
    assert resp.json()["project_code"] == "PRJ-002"


def test_client_external_reviewer_does_not_inherit_technical_reviewer_permissions(db_session, seeded):
    """
    Explicit PIGL/Product instruction (Rev 2 §E.1): CLIENT_EXTERNAL_REVIEWER
    must not inherit Technical Reviewer or Project Manager permissions by
    default. Verified directly against the seeded permission matrix rather
    than through a not-yet-built endpoint, since no Phase-1 endpoint is
    TECHNICAL_REVIEWER/PROJECT_MANAGER-exclusive yet other than
    project.create (PROJECT_MANAGER + ADMINISTRATOR only).
    """
    from app.models.rbac import Permission, Role, RolePermission

    def permission_codes_for(role_code):
        role = db_session.query(Role).filter(Role.code == role_code).first()
        rows = (
            db_session.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == role.id)
            .all()
        )
        return {r[0] for r in rows}

    client_reviewer_perms = permission_codes_for("CLIENT_EXTERNAL_REVIEWER")
    project_manager_perms = permission_codes_for("PROJECT_MANAGER")

    assert "project.create" not in client_reviewer_perms
    assert client_reviewer_perms != project_manager_perms
    assert client_reviewer_perms.issubset({"project.read"})


def test_non_admin_cannot_reach_admin_endpoints(client, db_session, seeded):
    make_user(db_session, email="plainuser@example.com", password="testpass123")
    _login(client, "plainuser@example.com", "testpass123")

    resp = client.get("/admin/audit-events")

    assert resp.status_code == 403


def test_admin_can_read_audit_events(client, db_session, seeded):
    make_user(db_session, email="admin3@example.com", password="testpass123", global_role_code="ADMINISTRATOR")
    _login(client, "admin3@example.com", "testpass123")

    resp = client.get("/admin/audit-events")

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
