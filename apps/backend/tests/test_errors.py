"""Envelope de errores: `detail` (contrato del frontend) + `code`; mapeo de IntegrityError sin filtrar SQL."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from apps.backend.src.core.errors import register_error_handlers
from apps.backend.src.main import app as main_app


class FakeDbError(Exception):
    """Imita la excepción de psycopg2: lleva `pgcode`."""
    def __init__(self, pgcode):
        super().__init__("duplicate key value violates unique constraint uq_secret on table users")
        self.pgcode = pgcode


class Body(BaseModel):
    n: int


def integrity(pgcode):
    return IntegrityError("INSERT INTO users (password_hash) VALUES (%(h)s)", {"h": "s3cret-hash"}, FakeDbError(pgcode))


@pytest.fixture
def client():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/integrity/{pgcode}")
    def raise_integrity(pgcode: str):
        raise integrity(None if pgcode == "none" else pgcode)

    @app.get("/unauthorized")
    def unauthorized():
        raise HTTPException(status_code=401, detail="No autenticado", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/missing")
    def missing():
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    @app.post("/validated")
    def validated(body: Body):
        return body

    @app.get("/bug")
    def bug():
        raise RuntimeError("bug de programación")

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("pgcode, status, code", [
    ("23505", 409, "CONFLICT"),
    ("23503", 422, "INVALID_REFERENCE"),
    ("23514", 422, "CONSTRAINT_VIOLATION"),
    ("23502", 409, "CONFLICT"),   # otro 23xxx: respaldo seguro
    ("none", 409, "CONFLICT"),    # sin pgcode (otro driver): respaldo seguro
])
def test_integrity_error_maps_by_pgcode_without_leaking_internals(client, pgcode, status, code):
    r = client.get(f"/integrity/{pgcode}")
    assert r.status_code == status
    body = r.json()
    assert body["code"] == code and isinstance(body["detail"], str) and body["detail"]
    for leaked in ("INSERT", "users", "s3cret", "uq_secret", "password_hash", "duplicate key"):
        assert leaked not in r.text


def test_http_exception_keeps_detail_and_headers_and_gains_a_code(client):
    r = client.get("/unauthorized")
    assert r.status_code == 401
    assert r.json() == {"detail": "No autenticado", "code": "UNAUTHORIZED"}
    assert r.headers["www-authenticate"] == "Bearer"
    r = client.get("/missing")
    assert r.status_code == 404 and r.json() == {"detail": "Lote no encontrado", "code": "NOT_FOUND"}


def test_validation_errors_keep_the_fastapi_shape(client):
    r = client.post("/validated", json={"n": "no-es-numero"})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], list) and r.json()["detail"][0]["loc"] == ["body", "n"]


def test_programming_errors_are_not_masked_as_client_errors(client):
    assert client.get("/bug").status_code == 500


def test_main_app_registers_the_handlers():
    assert IntegrityError in main_app.exception_handlers
