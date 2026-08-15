from tests.conftest import make_user


def test_login_success_sets_session_cookie(client, db_session):
    make_user(db_session, email="alice@example.com", password="correcthorse")

    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "correcthorse"})

    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"
    assert "gi_session" in resp.cookies


def test_login_wrong_password_rejected(client, db_session):
    make_user(db_session, email="bob@example.com", password="correcthorse")

    resp = client.post("/auth/login", json={"email": "bob@example.com", "password": "wrongpassword"})

    assert resp.status_code == 401
    assert "gi_session" not in resp.cookies


def test_login_unknown_email_rejected_same_as_wrong_password(client, db_session):
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_me_requires_authentication(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_after_login(client, db_session):
    make_user(db_session, email="carol@example.com", password="correcthorse")
    client.post("/auth/login", json={"email": "carol@example.com", "password": "correcthorse"})

    resp = client.get("/auth/me")

    assert resp.status_code == 200
    assert resp.json()["email"] == "carol@example.com"


def test_logout_revokes_session(client, db_session):
    make_user(db_session, email="dave@example.com", password="correcthorse")
    client.post("/auth/login", json={"email": "dave@example.com", "password": "correcthorse"})
    assert client.get("/auth/me").status_code == 200

    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200

    resp_after_logout = client.get("/auth/me")
    assert resp_after_logout.status_code == 401


def test_disabled_user_cannot_authenticate(client, db_session):
    user = make_user(db_session, email="erin@example.com", password="correcthorse")
    user.status = "DISABLED"
    db_session.commit()

    resp = client.post("/auth/login", json={"email": "erin@example.com", "password": "correcthorse"})
    assert resp.status_code == 401
