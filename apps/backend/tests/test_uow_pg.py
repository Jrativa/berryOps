"""Unidad de trabajo y envelope de errores de punta a punta (API real + PostgreSQL de pruebas)."""
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.src.core.uow import get_uow, open_unit_of_work
from apps.backend.src.features.auth.infrastructure.postgres.models import User, UserSession
from apps.backend.src.features.inventory.infrastructure.postgres import repositories as inventory_repos
from apps.backend.src.features.inventory.infrastructure.postgres.models import Plant, PlantObservation, Plot
from apps.backend.src.main import app
from apps.backend.tests.pg_support import run_concurrently, seed_admin

pytestmark = pytest.mark.pg

PASSWORD = "clave-segura-1"


@pytest.fixture
def api(pg_engine):
    factory = sessionmaker(bind=pg_engine, autoflush=False)

    def uow_on_test_db():
        yield from open_unit_of_work(factory)

    app.dependency_overrides[get_uow] = uow_on_test_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def user_body(role_id, username, email=None):
    return {"username": username, "email": email or f"{username}@finca.com", "full_name": "Test",
            "role_id": str(role_id), "password": PASSWORD}


@pytest.fixture
def admin(pg_engine, api):
    """Rol admin + usuario admin sembrados fuera de la API y su sesión iniciada."""
    role_id = seed_admin(pg_engine)
    login = api.post("/auth/login", json={"username": "root", "password": PASSWORD}).json()
    return {"role_id": role_id, "headers": bearer(login["access_token"]), "login": login}


def committed(pg_engine, statement):
    with Session(pg_engine) as other:  # conexión distinta: solo ve lo confirmado
        return other.scalar(statement)


def new_plot(api, admin, name="Norte"):
    r = api.post("/inventory/plots", headers=admin["headers"], json={"name": name, "variety": "Biloxi", "area_ha": 1})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------- una transacción, un commit ----------
def test_successful_multistep_operations_commit_once_and_are_visible_elsewhere(pg_engine, api, admin):
    plot_id = new_plot(api, admin)
    commits = []
    listener = lambda conn: commits.append(1)  # noqa: E731
    event.listen(pg_engine, "commit", listener)
    try:
        r = api.post(f"/inventory/plots/{plot_id}/plants/generate", headers=admin["headers"],
                     json={"rows": 2, "columns": 3})
    finally:
        event.remove(pg_engine, "commit", listener)
    assert r.status_code == 200 and r.json() == {"created": 6, "total": 6}
    assert len(commits) == 1
    assert committed(pg_engine, select(func.count()).select_from(Plant)) == 6
    assert committed(pg_engine, select(Plot.plant_count)) == 6


def test_observe_commits_observation_and_status_together(pg_engine, api, admin):
    plot_id = new_plot(api, admin)
    api.post(f"/inventory/plots/{plot_id}/plants/generate", headers=admin["headers"], json={"rows": 1, "columns": 1})
    plant_id = committed(pg_engine, select(Plant.id))
    r = api.post(f"/inventory/plants/{plant_id}/observations", headers=admin["headers"], json={"status": "dead"})
    assert r.status_code == 201 and r.json()["status"] == "dead"
    assert committed(pg_engine, select(func.count()).select_from(PlantObservation)) == 1
    assert committed(pg_engine, select(Plant.status)) == "dead"


def test_unhandled_error_rolls_back_the_whole_request(pg_engine, api, admin, monkeypatch):
    plot_id = new_plot(api, admin)

    def boom(self, plot, fields):
        raise RuntimeError("fallo forzado")

    monkeypatch.setattr(inventory_repos.PlotRepository, "update", boom)  # tras crear las plantas
    r = api.post(f"/inventory/plots/{plot_id}/plants/generate", headers=admin["headers"], json={"rows": 2, "columns": 2})
    assert r.status_code == 500
    assert committed(pg_engine, select(func.count()).select_from(Plant)) == 0


# ---------- conflictos de datos ----------
def test_concurrent_creation_of_same_plot_name_gives_one_201_and_one_handled_409(pg_engine, api, admin, monkeypatch):
    # Ambas peticiones pasan la comprobación "¿existe?" antes de que ninguna inserte: decide la BD
    both_checked = threading.Barrier(2, timeout=30)
    original = inventory_repos.PlotRepository.get_by_name

    def get_by_name_then_wait(self, owner_id, name):
        found = original(self, owner_id, name)
        both_checked.wait()
        return found

    monkeypatch.setattr(inventory_repos.PlotRepository, "get_by_name", get_by_name_then_wait)

    def create():
        client = TestClient(app, raise_server_exceptions=False)
        return client.post("/inventory/plots", headers=admin["headers"],
                           json={"name": "Duplicado", "variety": "Biloxi", "area_ha": 1})

    responses = run_concurrently([create, create])

    assert sorted(r.status_code for r in responses) == [201, 409]
    loser = next(r for r in responses if r.status_code == 409)
    assert loser.json()["code"] == "CONFLICT" and "detail" in loser.json()
    assert committed(pg_engine, select(func.count()).select_from(Plot)) == 1


def test_duplicate_username_is_409_conflict_without_leaking_sql(api, admin):
    r = api.post("/auth/users/", headers=admin["headers"],
                 json=user_body(admin["role_id"], "root", email="otro@finca.com"))
    assert r.status_code == 409
    assert r.json()["code"] == "CONFLICT"
    assert not any(word in r.text.lower() for word in ("insert", "users_", "uq_", "otro@finca.com", "psycopg"))


def test_duplicate_email_keeps_its_existing_400_message(api, admin):
    r = api.post("/auth/users/", headers=admin["headers"],
                 json=user_body(admin["role_id"], "otro", email="root@finca.com"))
    assert r.status_code == 400 and r.json()["detail"] == "El email ya está registrado"


def test_unknown_role_id_is_422_invalid_reference(api, admin):
    r = api.post("/auth/users/", headers=admin["headers"],
                 json=user_body("00000000-0000-0000-0000-000000000001", "nuevo"))
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_REFERENCE"
    assert "insert" not in r.text.lower() and "foreign" not in r.text.lower()


def test_failed_request_leaves_the_connection_pool_usable(api, admin):
    api.post("/auth/users/", headers=admin["headers"], json=user_body(admin["role_id"], "root", "x@finca.com"))
    assert api.get("/inventory/plots", headers=admin["headers"]).status_code == 200


# ---------- reutilización del refresh token ----------
def all_sessions_revoked(pg_engine):
    with Session(pg_engine) as s:
        rows = s.scalars(select(UserSession.is_revoked)).all()
    return bool(rows) and all(rows)


def test_refresh_token_reuse_returns_401_and_keeps_every_session_revoked(pg_engine, api, admin):
    first = admin["login"]["refresh_token"]
    rotated = api.post("/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    second_device = api.post("/auth/login", json={"username": "root", "password": PASSWORD}).json()
    assert not all_sessions_revoked(pg_engine)

    reused = api.post("/auth/refresh", json={"refresh_token": first})  # token ya rotado: robo
    assert reused.status_code == 401
    assert reused.json()["detail"] == "Refresh token inválido o expirado"
    assert all_sessions_revoked(pg_engine)  # la revocación sobrevive al 401
    for token in (rotated.json()["refresh_token"], second_device["refresh_token"]):
        assert api.post("/auth/refresh", json={"refresh_token": token}).status_code == 401


def test_refresh_for_inactive_user_returns_401_and_keeps_sessions_revoked(pg_engine, api, admin):
    with Session(pg_engine) as s:
        s.execute(text("UPDATE users SET is_active = false"))
        s.commit()
    r = api.post("/auth/refresh", json={"refresh_token": admin["login"]["refresh_token"]})
    assert r.status_code == 401 and r.json()["detail"] == "Usuario inactivo"
    assert all_sessions_revoked(pg_engine)


def test_normal_rotation_and_idempotent_logout_persist(pg_engine, api, admin):
    token = admin["login"]["refresh_token"]
    rotated = api.post("/auth/refresh", json={"refresh_token": token}).json()["refresh_token"]
    assert committed(pg_engine, select(func.count()).select_from(UserSession)) == 2
    assert api.post("/auth/logout", json={"refresh_token": rotated}).status_code == 204
    assert api.post("/auth/logout", json={"refresh_token": rotated}).status_code == 204
    assert api.post("/auth/logout", json={"refresh_token": "desconocido"}).status_code == 204
    assert all_sessions_revoked(pg_engine)
    assert committed(pg_engine, select(func.count()).select_from(User)) == 1


# ---------- el commit ocurre ANTES de enviar la respuesta ----------
class FlakyCommitSession(Session):
    """Session cuyo commit falla a demanda (simula p. ej. una restricción diferida)."""
    failure = None

    def commit(self):
        if FlakyCommitSession.failure is not None:
            raise FlakyCommitSession.failure
        super().commit()


@pytest.fixture
def flaky_api(pg_engine):
    factory = sessionmaker(bind=pg_engine, autoflush=False, class_=FlakyCommitSession)

    def uow_on_test_db():
        yield from open_unit_of_work(factory)

    app.dependency_overrides[get_uow] = uow_on_test_db
    yield TestClient(app, raise_server_exceptions=False)
    FlakyCommitSession.failure = None
    app.dependency_overrides.clear()


def _admin_on(client, pg_engine):
    seed_admin(pg_engine)
    token = client.post("/auth/login", json={"username": "root", "password": PASSWORD}).json()["access_token"]
    return bearer(token)


def test_integrity_error_at_commit_is_a_handled_409_not_a_2xx(pg_engine, flaky_api):
    from sqlalchemy.exc import IntegrityError

    class Orig(Exception):
        pgcode = "23505"

    headers = _admin_on(flaky_api, pg_engine)
    FlakyCommitSession.failure = IntegrityError("INSERT INTO secret", {"p": "s3cret"}, Orig("dup"))
    r = flaky_api.get("/inventory/plots", headers=headers)
    assert r.status_code == 409 and r.json()["code"] == "CONFLICT"
    assert "secret" not in r.text.lower() and "insert" not in r.text.lower()


def test_any_other_commit_failure_is_a_generic_500_not_a_2xx(pg_engine, flaky_api):
    headers = _admin_on(flaky_api, pg_engine)
    FlakyCommitSession.failure = RuntimeError("disco lleno en /secreto")
    r = flaky_api.get("/inventory/plots", headers=headers)
    assert r.status_code == 500 and "secreto" not in r.text
