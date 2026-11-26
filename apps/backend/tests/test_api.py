import pytest

from apps.backend.src.features.auth.domain import schemas


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def user_payload(role_id, username="maria", password="clave-segura-1"):
    return {"username": username, "email": f"{username}@finca.com", "full_name": "Maria",
            "role_id": str(role_id), "password": password}


def do_login(client, username, password="clave-segura-1"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def seeded(client, service, admin_role, worker_role):
    """Un admin y un operario ya creados; devuelve sus datos de login."""
    service.register_user(schemas.UserCreate(**user_payload(admin_role.id, "admin1")))
    service.register_user(schemas.UserCreate(**user_payload(worker_role.id, "operario1")))
    return {"admin": do_login(client, "admin1"), "worker": do_login(client, "operario1"),
            "admin_role": admin_role, "worker_role": worker_role}


# ---------- sin arranque anonimo ----------
def test_no_anonymous_bootstrap_even_with_zero_users(client, admin_role):
    assert client.post("/auth/roles/", json={"name": "otro"}).status_code == 401
    assert client.post("/auth/users/", json=user_payload(admin_role.id, "root")).status_code == 401


def test_zero_admins_non_admin_token_is_403(client, service, worker_role):
    service.register_user(schemas.UserCreate(**user_payload(worker_role.id, "operario1")))
    token = do_login(client, "operario1")["access_token"]
    assert client.post("/auth/roles/", json={"name": "x"}, headers=auth(token)).status_code == 403


# ---------- roles solo admin ----------
def test_create_role_requires_token(client, seeded):
    assert client.post("/auth/roles/", json={"name": "nuevo"}).status_code == 401


def test_create_role_forbidden_for_non_admin(client, seeded):
    r = client.post("/auth/roles/", json={"name": "nuevo"}, headers=auth(seeded["worker"]["access_token"]))
    assert r.status_code == 403


def test_create_role_ok_for_admin(client, seeded):
    r = client.post("/auth/roles/", json={"name": "nuevo"}, headers=auth(seeded["admin"]["access_token"]))
    assert r.status_code == 200 and r.json()["name"] == "nuevo"


def test_create_role_duplicate_is_400(client, seeded):
    r = client.post("/auth/roles/", json={"name": "admin"}, headers=auth(seeded["admin"]["access_token"]))
    assert r.status_code == 400


def test_create_user_admin_only(client, seeded):
    payload = user_payload(seeded["worker_role"].id, "nuevo1")
    assert client.post("/auth/users/", json=payload,
                       headers=auth(seeded["worker"]["access_token"])).status_code == 403
    assert client.post("/auth/users/", json=payload,
                       headers=auth(seeded["admin"]["access_token"])).status_code == 200


def test_get_user_requires_auth(client, seeded):
    assert client.get("/auth/users/operario1").status_code == 401


def test_get_user_returns_only_own_profile(client, seeded):
    r = client.get("/auth/users/operario1", headers=auth(seeded["worker"]["access_token"]))
    assert r.status_code == 200 and r.json()["username"] == "operario1" and "password" not in r.text


def test_get_other_user_is_same_404_as_unknown_user(client, seeded):
    headers = auth(seeded["worker"]["access_token"])
    existing = client.get("/auth/users/admin1", headers=headers)
    unknown = client.get("/auth/users/nadie", headers=headers)
    assert existing.status_code == unknown.status_code == 404
    assert existing.json() == unknown.json()


def test_invalid_token_is_401(client, seeded):
    assert client.get("/auth/users/admin1", headers=auth("basura")).status_code == 401


# ---------- login ----------
def test_login_errors(client, seeded):
    assert client.post("/auth/login", json={"username": "admin1", "password": "incorrecta1"}).status_code == 401
    assert client.post("/auth/login", json={"username": "ab", "password": "x"}).status_code == 422


# ---------- refresh + logout ----------
def test_refresh_rotation_over_http(client, seeded):
    old = seeded["worker"]["refresh_token"]
    r = client.post("/auth/refresh", json={"refresh_token": old})
    assert r.status_code == 200
    body = r.json()
    assert body["refresh_token"] != old and body["username"] == "operario1" and body["role"] == "operario"
    assert client.post("/auth/refresh", json={"refresh_token": old}).status_code == 401  # reuso
    # la reutilizacion revoco tambien la sesion nueva
    assert client.post("/auth/refresh", json={"refresh_token": body["refresh_token"]}).status_code == 401


def test_refresh_requires_body(client):
    assert client.post("/auth/refresh", json={}).status_code == 422


def test_logout_revokes_refresh_token(client, seeded):
    token = seeded["worker"]["refresh_token"]
    assert client.post("/auth/logout", json={"refresh_token": token}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": token}).status_code == 401
    assert client.post("/auth/logout", json={"refresh_token": token}).status_code == 204  # idempotente


def test_logout_only_affects_that_session(client, seeded):
    other = do_login(client, "operario1")
    client.post("/auth/logout", json={"refresh_token": seeded["worker"]["refresh_token"]})
    assert client.post("/auth/refresh", json={"refresh_token": other["refresh_token"]}).status_code == 200
