from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from apps.backend.src.features.auth.application import access_tokens
from apps.backend.src.features.auth.domain import schemas


def make_user(service, role, username="maria", password="clave-segura-1", email=None):
    return service.register_user(schemas.UserCreate(
        username=username, email=email or f"{username}@finca.com",
        full_name="Maria Perez", role_id=role.id, password=password,
    ))


def login(service, username="maria", password="clave-segura-1"):
    return service.login(schemas.LoginRequest(username=username, password=password))


def refresh_req(token):
    return schemas.RefreshTokenRequest(refresh_token=token)


def test_register_hashes_password_and_rejects_duplicate_email(service, worker_role):
    user = make_user(service, worker_role)
    assert user.password_hash != "clave-segura-1"
    with pytest.raises(ValueError, match="email"):
        make_user(service, worker_role, username="otra", email="maria@finca.com")


def test_login_ok_returns_tokens_and_role(service, worker_role):
    make_user(service, worker_role)
    data = login(service)
    assert data["role"] == "operario" and data["username"] == "maria"
    assert data["access_token"] and data["refresh_token"]


def test_login_wrong_password_and_unknown_user(service, worker_role):
    make_user(service, worker_role)
    with pytest.raises(ValueError, match="incorrectos"):
        login(service, password="mala-contrasena")
    with pytest.raises(ValueError, match="incorrectos"):
        login(service, username="nadie")


def test_login_inactive_user(service, worker_role, repos):
    user = make_user(service, worker_role)
    repos["users"].items[user.id].is_active = False
    with pytest.raises(ValueError, match="inactivo"):
        login(service)


def test_refresh_token_is_stored_hashed(service, worker_role, repos):
    make_user(service, worker_role)
    token = login(service)["refresh_token"]
    assert all(s.refresh_token != token for s in repos["sessions"].items)


def test_refresh_rotates_token(service, worker_role):
    make_user(service, worker_role)
    first = login(service)["refresh_token"]
    data = service.refresh_token(refresh_req(first))
    assert data["refresh_token"] != first
    assert data["username"] == "maria" and data["role"] == "operario"
    with pytest.raises(ValueError):  # el token usado ya no sirve
        service.refresh_token(refresh_req(first))


def test_reusing_revoked_token_revokes_all_sessions(service, worker_role):
    make_user(service, worker_role)
    first = login(service)["refresh_token"]
    second = service.refresh_token(refresh_req(first))["refresh_token"]
    with pytest.raises(ValueError):  # reutilizacion del primero
        service.refresh_token(refresh_req(first))
    with pytest.raises(ValueError):  # el legitimo tambien queda invalidado
        service.refresh_token(refresh_req(second))


def test_refresh_expired_and_unknown(service, worker_role, repos):
    make_user(service, worker_role)
    token = login(service)["refresh_token"]
    repos["sessions"].items[0].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with pytest.raises(ValueError):
        service.refresh_token(refresh_req(token))
    with pytest.raises(ValueError):
        service.refresh_token(refresh_req("inventado"))


def test_refresh_inactive_user_revokes_sessions(service, worker_role, repos):
    user = make_user(service, worker_role)
    token = login(service)["refresh_token"]
    repos["users"].items[user.id].is_active = False
    with pytest.raises(ValueError, match="inactivo"):
        service.refresh_token(refresh_req(token))
    assert all(s.is_revoked for s in repos["sessions"].items)


def test_logout_revokes_session_and_is_idempotent(service, worker_role):
    make_user(service, worker_role)
    token = login(service)["refresh_token"]
    service.logout(refresh_req(token))
    service.logout(refresh_req(token))  # no falla
    service.logout(refresh_req("desconocido"))
    with pytest.raises(ValueError):
        service.refresh_token(refresh_req(token))


def test_get_user_from_token(service, worker_role):
    user = make_user(service, worker_role)
    token = login(service)["access_token"]
    assert service.get_user_from_token(token).id == user.id
    with pytest.raises(ValueError):
        service.get_user_from_token("basura")


def test_expired_access_token_rejected(service, worker_role):
    user = make_user(service, worker_role)
    token = access_tokens.create_access_token({"sub": str(user.id)}, timedelta(seconds=-1))
    with pytest.raises(ValueError):
        service.get_user_from_token(token)


def test_is_admin_is_case_insensitive(service):
    assert service.is_admin(SimpleNamespace(role=SimpleNamespace(name="Admin")))
    assert service.is_admin(SimpleNamespace(role=SimpleNamespace(name="Administrador")))
    assert not service.is_admin(SimpleNamespace(role=SimpleNamespace(name="operario")))


def test_create_role_duplicate(service, worker_role):
    with pytest.raises(ValueError, match="existe"):
        service.create_role(schemas.RoleCreate(name="operario"))
