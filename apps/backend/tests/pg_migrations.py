"""Alembic sobre la BD de pruebas: toda ejecucion pasa por el guard antes de tocar nada."""
from pathlib import Path

from alembic.config import Config
from sqlalchemy import MetaData, create_engine

from apps.backend.tests.pg_guard import assert_safe_test_database, read_dev_target

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def alembic_config(url: str) -> Config:
    """Config de Alembic apuntando a `url`; rechaza cualquier BD que no sea la de pruebas."""
    assert_safe_test_database(url, read_dev_target())
    config = Config(str(ALEMBIC_INI))
    config.attributes["sqlalchemy_url"] = url
    return config


def reset_schema(url: str) -> None:
    """Elimina TODAS las tablas de la BD de pruebas (incluida alembic_version)."""
    assert_safe_test_database(url, read_dev_target())
    engine = create_engine(url)
    try:
        metadata = MetaData()
        metadata.reflect(bind=engine)
        metadata.drop_all(bind=engine)
    finally:
        engine.dispose()
