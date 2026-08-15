from app.models.audit import AuditEvent
from tests.conftest import make_user


def test_login_writes_audit_event(client, db_session):
    make_user(db_session, email="audit1@example.com", password="testpass123")

    client.post("/auth/login", json={"email": "audit1@example.com", "password": "testpass123"})

    events = db_session.query(AuditEvent).filter(AuditEvent.action == "LOGIN").all()
    assert len(events) == 1
    assert events[0].object_type == "User"


def test_failed_login_does_not_write_audit_event(client, db_session):
    make_user(db_session, email="audit2@example.com", password="testpass123")

    client.post("/auth/login", json={"email": "audit2@example.com", "password": "wrongpassword"})

    events = db_session.query(AuditEvent).filter(AuditEvent.action == "LOGIN").all()
    assert len(events) == 0


def test_logout_writes_audit_event(client, db_session):
    make_user(db_session, email="audit3@example.com", password="testpass123")
    client.post("/auth/login", json={"email": "audit3@example.com", "password": "testpass123"})

    client.post("/auth/logout")

    events = db_session.query(AuditEvent).filter(AuditEvent.action == "LOGOUT").all()
    assert len(events) == 1


def test_project_creation_writes_audit_event(client, db_session, seeded):
    from app.models.org import Client, Organization

    make_user(db_session, email="audit4@example.com", password="testpass123", global_role_code="ADMINISTRATOR")
    org = Organization(name="Org")
    db_session.add(org)
    db_session.flush()
    c = Client(name="Client", organization_id=org.id)
    db_session.add(c)
    db_session.commit()
    client.post("/auth/login", json={"email": "audit4@example.com", "password": "testpass123"})

    resp = client.post("/projects", json={"project_code": "AUD-1", "name": "P", "client_id": str(c.id)})
    project_id = resp.json()["id"]

    events = db_session.query(AuditEvent).filter(AuditEvent.action == "CREATE_PROJECT").all()
    assert len(events) == 1
    assert events[0].object_id == project_id


def test_audit_events_have_no_direct_write_endpoint(client, db_session):
    """
    Confirms the design rule (Rev 1 §17): AuditEvent has no POST endpoint
    anywhere in the API. It can only be produced as a side effect of
    another module's own service call.
    """
    make_user(db_session, email="audit5@example.com", password="testpass123")
    client.post("/auth/login", json={"email": "audit5@example.com", "password": "testpass123"})

    resp = client.post("/admin/audit-events", json={"action": "FAKE"})

    assert resp.status_code in (404, 405)
