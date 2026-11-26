"""Límite de contraseña: bcrypt solo usa 72 BYTES, así que se mide en bytes UTF-8, no en caracteres."""
import pytest
from pydantic import ValidationError

from apps.backend.src.features.auth.domain import schemas
from apps.backend.tests.test_api import auth, seeded, user_payload  # noqa: F401  (fixture)


def create(password):
    return schemas.UserCreate(**user_payload("00000000-0000-0000-0000-000000000001", password=password))


def login(password):
    return schemas.LoginRequest(username="maria", password=password)


@pytest.mark.parametrize("build", [create, login])
def test_exactly_72_bytes_is_accepted(build):
    assert build("a" * 72).password == "a" * 72
    assert len((("€" * 24)).encode()) == 72
    assert build("€" * 24)  # 24 caracteres x 3 bytes


@pytest.mark.parametrize("build", [create, login])
def test_more_than_72_bytes_is_rejected_even_when_few_characters(build):
    with pytest.raises(ValidationError, match="72"):
        build("€" * 25)  # 25 caracteres = 75 bytes
    with pytest.raises(ValidationError):
        build("a" * 73)


@pytest.mark.parametrize("build", [create, login])
def test_minimum_of_8_is_kept(build):
    with pytest.raises(ValidationError):
        build("a" * 7)


def test_api_rejects_a_long_password_with_422(client, seeded):
    payload = user_payload(seeded["worker_role"].id, "nuevo1", password="€" * 25)
    r = client.post("/auth/users/", json=payload, headers=auth(seeded["admin"]["access_token"]))
    assert r.status_code == 422
