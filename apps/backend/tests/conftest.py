import os

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
    return TestClient(app)


@pytest.fixture
def admin_role(service):
    return service.role_repo.create(schemas.RoleCreate(name="admin"))


@pytest.fixture
def worker_role(service):
    return service.role_repo.create(schemas.RoleCreate(name="operario"))
