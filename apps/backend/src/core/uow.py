# src/core/uow.py
"""Unidad de trabajo: UNA transacción de base de datos por petición.

`get_uow` es la única forma de obtener una Session (reemplaza al antiguo `get_db`). Commit si la petición
termina bien, rollback ante cualquier excepción. Los repositorios solo hacen `flush()`; los servicios no
saben nada de commits. Cualquier preparación de la transacción (p. ej. contexto de tenant) irá aquí, antes
del `yield`.
"""
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from apps.backend.src.core.databases.postgres_db import SessionLocal


def open_unit_of_work(session_factory: Callable[[], Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def get_uow() -> Iterator[Session]:
    yield from open_unit_of_work(SessionLocal)


# REGLA: el UoW se obtiene SIEMPRE con este alias (scope="function"). Con el scope por defecto el commit
# corre DESPUÉS de enviar la respuesta: un fallo de commit no podría ser un error y la petición siguiente
# podría no ver lo escrito. Con "function" el commit ocurre antes de enviarla.
UnitOfWork = Annotated[Session, Depends(get_uow, scope="function")]
