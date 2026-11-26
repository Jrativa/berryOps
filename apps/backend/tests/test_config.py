"""Validación de la configuración: se construye Settings sin leer el .env real."""
import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from apps.backend.src.core.config import Settings, parse_cors_origins

VALID = {
    "DB_USER": "u", "DB_PASSWORD": "p", "DB_HOST": "localhost", "DB_PORT": "5432", "DB_NAME": "db",
    "SECRET_KEY": "k" * 32, "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15", "REFRESH_TOKEN_EXPIRE_DAYS": "7",
}


def make(**overrides) -> Settings:
    return Settings(_env_file=None, **{**VALID, **overrides})


# ---------- SECRET_KEY ----------
def test_secret_key_of_32_characters_is_accepted():
    assert make(SECRET_KEY="k" * 32).SECRET_KEY == "k" * 32


def test_short_secret_key_fails_fast_without_leaking_the_value():
    short = "clave-corta-secreta"
    with pytest.raises(ValidationError) as exc:
        make(SECRET_KEY=short)
    text = str(exc.value)
    assert "SECRET_KEY" in text and "32" in text
    assert short not in text


# ---------- DATABASE_URL ----------
def test_database_url_round_trips_special_characters_in_the_password():
    password = "p@ss:w/rd%23#?&"
    url = make(DB_PASSWORD=password, DB_USER="us@er").DATABASE_URL
    parsed = make_url(url)
    assert parsed.password == password and parsed.username == "us@er"
    assert (parsed.host, parsed.port, parsed.database) == ("localhost", 5432, "db")
    assert parsed.drivername == "postgresql"


# ---------- CORS ----------
def test_cors_default_is_the_local_frontend():
    assert make().cors_origins == ["http://localhost:5173"]


def test_cors_origins_are_comma_separated_and_trimmed():
    assert make(CORS_ORIGINS=" https://a.com, https://b.com ,,").cors_origins == ["https://a.com", "https://b.com"]


def test_wildcard_origin_is_rejected_because_credentials_are_allowed():
    with pytest.raises(ValueError, match=r"\*"):
        parse_cors_origins("https://a.com,*")
    with pytest.raises(ValidationError):
        make(CORS_ORIGINS="*")
