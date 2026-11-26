import os
from types import SimpleNamespace

# Las pruebas no usan Postgres ni el .env real: se fijan valores antes de importar `src`.
for key, value in {
    "DB_USER": "test", "DB_PASSWORD": "test", "DB_HOST": "localhost",
    "DB_PORT": "5432", "DB_NAME": "test",
    "SECRET_KEY": "test-secret-key-with-at-least-32-bytes!!",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
}.items():
    os.environ[key] = value

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.backend.src.core.uow import get_uow
from apps.backend.src.features.auth.application.services import AuthService
from apps.backend.src.features.auth.dependencies import get_auth_service
from apps.backend.src.features.auth.domain import schemas
from apps.backend.src.features.auth.presentation.routes import router
from apps.backend.tests.fakes import FakeRoleRepository, FakeSessionRepository, FakeUserRepository


@pytest.fixture
def repos():
    roles = FakeRoleRepository()
    return {
        "roles": roles,
        "users": FakeUserRepository(roles),
        "sessions": FakeSessionRepository(),
    }


@pytest.fixture
def service(repos):
    return AuthService(repos["users"], repos["roles"], repos["sessions"])


@pytest.fixture
def client(service):
    """API real (routers + dependencias) sobre repositorios en memoria."""
    app = FastAPI()
    app.include_router(router, prefix="/auth")
    app.dependency_overrides[get_auth_service] = lambda: service
    app.dependency_overrides[get_uow] = lambda: SimpleNamespace(commit=lambda: None)  # los fakes no tienen transacción
    return TestClient(app)


@pytest.fixture
def admin_role(service):
    return service.role_repo.create(schemas.RoleCreate(name="admin"))


@pytest.fixture
def worker_role(service):
    return service.role_repo.create(schemas.RoleCreate(name="operario"))


# --- Arnés PostgreSQL (tests marcados `pg`) ---------------------------------------------------
# Decisión: los tests `pg` se incluyen en la ejecución normal cuando TEST_DATABASE_URL está
# disponible; si no, se SALTAN y el resumen final lo advierte en voz alta. `-m pg` los selecciona.
# Aislamiento: TRUNCATE ... RESTART IDENTITY CASCADE de todas las tablas antes de cada test
# (funciona también con varias conexiones/hilos, a diferencia de un rollback).
from alembic import command
from sqlalchemy import create_engine, text

from apps.backend.src.core.databases.postgres_db import Base
from apps.backend.tests.pg_guard import assert_safe_test_database, read_dev_target
from apps.backend.tests.pg_migrations import alembic_config, reset_schema
from apps.backend.tests.pg_support import load_test_database_url

PG_SKIP_REASONS: list[str] = []


def pytest_collection_modifyitems(items):
    """Todo test que use el engine PostgreSQL queda marcado `pg` (una sola decisión, aquí)."""
    for item in items:
        if "pg_engine" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.pg)


def pytest_terminal_summary(terminalreporter):
    if PG_SKIP_REASONS:
        terminalreporter.write_sep("!", "ATENCION: PRUEBAS POSTGRESQL (pg) NO EJECUTADAS", red=True, bold=True)
        terminalreporter.write_line(f"Motivo: {PG_SKIP_REASONS[0]}", red=True)
        terminalreporter.write_line("Un salto NO es un exito: la cobertura contra PostgreSQL esta sin verificar.", red=True)


def _import_all_models():
    from apps.backend.src.features.auth.infrastructure.postgres import models  # noqa: F401
    from apps.backend.src.features.inventory.infrastructure.postgres import models as _inv  # noqa: F401


@pytest.fixture(scope="session")
def pg_engine():
    url = load_test_database_url()
    if not url:
        PG_SKIP_REASONS.append("TEST_DATABASE_URL no definido (ver apps/backend/.env.test.example)")
        pytest.skip(PG_SKIP_REASONS[0])
    assert_safe_test_database(url, read_dev_target())  # antes de cualquier conexión; falla en voz alta
    engine = create_engine(url, pool_pre_ping=True)
    try:
        engine.connect().close()
    except Exception as exc:
        engine.dispose()
        PG_SKIP_REASONS.append(f"BD de pruebas inaccesible ({type(exc).__name__})")
        pytest.skip(PG_SKIP_REASONS[0])
    _import_all_models()
    reset_schema(url)
    command.upgrade(alembic_config(url), "head")  # el esquema de pruebas sale de las migraciones
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _pg_clean(request):
    """Vacía la BD de pruebas antes de cada test pg (solo si el test usa pg_engine)."""
    if "pg_engine" not in request.fixturenames:
        return
    engine = request.getfixturevalue("pg_engine")
    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
