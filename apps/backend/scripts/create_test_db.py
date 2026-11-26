"""Crea la BD de pruebas (una sola vez, idempotente).

Uso, desde la raíz del repo:  python -m apps.backend.scripts.create_test_db
Lee TEST_DATABASE_URL (entorno o apps/backend/.env.test). Rechaza cualquier BD que no sea `*_test`.
"""
import re
import sys

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import make_url

from apps.backend.tests.pg_guard import assert_safe_test_database, read_dev_target
from apps.backend.tests.pg_support import load_test_database_url

MAINTENANCE_DB = "postgres"
SAFE_NAME = re.compile(r"^[a-z0-9_]+$")


def create_test_database(url: str) -> bool:
    """Devuelve True si la creó, False si ya existía."""
    assert_safe_test_database(url, read_dev_target())
    parsed = make_url(url)
    if not SAFE_NAME.match(parsed.database):
        raise ValueError("Nombre de BD no permitido (solo a-z, 0-9 y _)")
    conn = psycopg2.connect(
        user=parsed.username, password=parsed.password, host=parsed.host,
        port=parsed.port or 5432, dbname=MAINTENANCE_DB,
    )
    conn.autocommit = True  # CREATE DATABASE no admite transacciones
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (parsed.database,))
            if cur.fetchone():
                return False
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(parsed.database)))
            return True
    finally:
        conn.close()


def main() -> int:
    url = load_test_database_url()
    if not url:
        print("Falta TEST_DATABASE_URL (ver apps/backend/.env.test.example)", file=sys.stderr)
        return 1
    created = create_test_database(url)
    print("BD de pruebas creada" if created else "La BD de pruebas ya existía")
    return 0


if __name__ == "__main__":
    sys.exit(main())
