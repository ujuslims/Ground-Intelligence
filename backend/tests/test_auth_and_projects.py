def test_login_and_me(client, seeded):
    r = client.post("/api/auth/login", json={"email": "engineer@example.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["email"] == "engineer@example.com"

    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200


def test_login_wrong_password(client, seeded):
    r = client.post("/api/auth/login", json={"email": "engineer@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_unauthenticated_request_rejected(client, seeded):
    r = client.get("/api/projects")
    assert r.status_code == 401


def test_project_list_scoped_to_membership(client, seeded):
    client.post("/api/auth/login", json={"email": "engineer@example.com", "password": "password123"})
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Demo Project"


def test_create_project_auto_enrolls_creator(client, seeded, db_session):
    client.post("/api/auth/login", json={"email": "engineer@example.com", "password": "password123"})
    org_id = seeded["org"].id
    r = client.post("/api/projects", json={"organization_id": org_id, "name": "Second Project"})
    assert r.status_code == 200
    r2 = client.get("/api/projects")
    assert len(r2.json()) == 2
