"""
The single most important test in this codebase: proves that, with zero
APPROVED MethodologyVersion rows in the database (the current, correct state
per the PIGL Engineering governance gate), a calculation request for a real
engineering calculation_type is REFUSED with an explicit message -- never a
plausible-looking fabricated result.
"""
from app.models.engineering import Calculation


def _login(client):
    client.post("/api/auth/login", json={"email": "engineer@example.com", "password": "password123"})


def test_shallow_foundation_calculation_is_refused(client, seeded, db_session):
    _login(client)
    project_id = seeded["project"].id

    r = client.post("/api/calculations", json={
        "project_id": project_id,
        "calculation_type": "SHALLOW_FOUNDATION_BEARING_CAPACITY",
    })
    assert r.status_code == 200
    calc_id = r.json()["id"]

    run = client.post(f"/api/calculations/{calc_id}/run", json={"inputs": {"width_m": 2.0, "depth_m": 1.5}})
    assert run.status_code == 200
    body = run.json()
    assert body["outcome"] == "REFUSED_NO_APPROVED_METHODOLOGY"
    assert body["result"] is None


def test_calculation_with_unapproved_methodology_still_refused(client, seeded, db_session):
    """Even if a Methodology/MethodologyVersion row exists but is DRAFT (not
    APPROVED), the Runner must still refuse -- proves the gate re-verifies
    server-side rather than trusting a supplied methodology_version_id."""
    from app.models.engineering import Methodology, MethodologyVersion

    m = Methodology(name="Candidate Bearing Capacity Method", engineering_domain="SHALLOW_FOUNDATION_BEARING_CAPACITY", status="DRAFT")
    db_session.add(m)
    db_session.flush()
    v = MethodologyVersion(methodology_id=m.id, version="0.1", status="DRAFT")
    db_session.add(v)
    db_session.commit()

    _login(client)
    project_id = seeded["project"].id

    r = client.post("/api/calculations", json={
        "project_id": project_id,
        "calculation_type": "SHALLOW_FOUNDATION_BEARING_CAPACITY",
        "methodology_id": m.id,
        "methodology_version_id": v.id,
    })
    calc_id = r.json()["id"]

    run = client.post(f"/api/calculations/{calc_id}/run", json={"inputs": {}})
    assert run.json()["outcome"] == "REFUSED_NO_APPROVED_METHODOLOGY"


def test_framework_test_mock_pipeline_runs_end_to_end(client, seeded, db_session):
    """The non-production pipeline test IS allowed to execute -- proving the
    pipeline works -- but returns an obviously synthetic, clearly-labelled
    result, never anything resembling a real engineering number."""
    _login(client)
    project_id = seeded["project"].id

    r = client.post("/api/calculations", json={"project_id": project_id, "calculation_type": "FRAMEWORK_TEST_MOCK"})
    calc_id = r.json()["id"]

    run = client.post(f"/api/calculations/{calc_id}/run", json={"inputs": {"x": 1}})
    body = run.json()
    assert body["outcome"] == "FRAMEWORK_TEST_MOCK"
    assert "NOT AN ENGINEERING RESULT" in body["result"]["note"]


def test_methodology_list_empty_for_unapproved_domain(client, seeded, db_session):
    _login(client)
    r = client.get("/api/methodologies", params={"calculation_type": "SHALLOW_FOUNDATION_BEARING_CAPACITY"})
    assert r.status_code == 200
    assert r.json() == []


def test_methodology_request_workflow(client, seeded, db_session):
    _login(client)
    r = client.post("/api/methodology-requests", json={
        "requested_name": "Candidate bearing capacity method",
        "reference": "Some standard",
        "reason": "Needed for upcoming project",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "REQUESTED"
