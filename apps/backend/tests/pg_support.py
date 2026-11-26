"""Soporte de las pruebas contra PostgreSQL: configuración y ejecución concurrente."""
import os
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypeVar

from dotenv import dotenv_values

TEST_ENV_FILE = Path(__file__).resolve().parents[1] / ".env.test"
T = TypeVar("T")


def load_test_database_url() -> str | None:
    """TEST_DATABASE_URL del entorno o, si falta, de apps/backend/.env.test."""
    return os.environ.get("TEST_DATABASE_URL") or dotenv_values(TEST_ENV_FILE).get("TEST_DATABASE_URL") or None


def run_concurrently(tasks: list[Callable[[], T]], timeout: float = 30) -> list[T]:
    """Ejecuta cada callable en su propio hilo, liberándolos a la vez con una Barrier.

    Cada callable debe abrir su propia conexión. Reenvía la primera excepción y devuelve los resultados en orden.
    """
    barrier = threading.Barrier(len(tasks), timeout=timeout)

    def start(task: Callable[[], T]) -> T:
        barrier.wait()
        return task()

    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = [pool.submit(start, task) for task in tasks]
        return [future.result(timeout=timeout) for future in futures]


def seed_admin(engine, username: str = "root", password: str = "clave-segura-1") -> str:
    """Crea (y confirma) rol admin + usuario admin con el servicio real; devuelve el id del rol.

    Ya no hay arranque anónimo por la API: el primer admin se siembra fuera de ella (como hace el CLI).
    """
    from sqlalchemy.orm import Session

    from apps.backend.src.features.auth.dependencies import get_auth_service
    from apps.backend.src.features.auth.domain import schemas

    with Session(engine) as session:
        service = get_auth_service(session)
        role = service.create_role(schemas.RoleCreate(name="admin"))
        service.register_user(schemas.UserCreate(
            username=username, email=f"{username}@finca.com", full_name="Test",
            role_id=role.id, password=password))
        session.commit()
        return str(role.id)
