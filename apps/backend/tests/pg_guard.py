"""Guard de la BD de pruebas: único lugar que decide si una URL es segura para tests/DDL.

Funciones puras (sin conexión). Se invocan antes de abrir cualquier conexión.
"""
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

TEST_SUFFIX = "_test"
DEV_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class UnsafeDatabaseError(RuntimeError):
    """La URL apunta a una BD que no puede usarse como BD de pruebas."""


@dataclass(frozen=True)
class DbTarget:
    host: str
    port: int
    name: str


def read_dev_target(env_file: Path = DEV_ENV_FILE) -> DbTarget | None:
    """BD de desarrollo según el .env (se lee del archivo, no del entorno, que los tests sobrescriben)."""
    values = dotenv_values(env_file)
    if not values.get("DB_NAME"):
        return None
    return DbTarget(values.get("DB_HOST") or "", int(values.get("DB_PORT") or 5432), values["DB_NAME"])


def assert_safe_test_database(url: str, dev: DbTarget | None) -> None:
    """Lanza UnsafeDatabaseError salvo que `url` sea PostgreSQL, termine en `_test` y no sea la BD de desarrollo."""
    try:
        parsed = make_url(url)
    except ArgumentError:
        raise UnsafeDatabaseError("URL de BD de pruebas inválida") from None
    name = parsed.database or ""
    if not parsed.drivername.startswith("postgresql"):
        raise UnsafeDatabaseError("La BD de pruebas debe ser PostgreSQL")
    if not name.endswith(TEST_SUFFIX):
        raise UnsafeDatabaseError(f"Rechazada: la BD '{name}' no termina en '{TEST_SUFFIX}'")
    if dev is not None and name == dev.name:
        raise UnsafeDatabaseError(f"Rechazada: '{name}' es la BD de desarrollo")
