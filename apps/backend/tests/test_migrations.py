"""Migraciones Alembic sobre la BD de pruebas (la unica que el guard permite tocar)."""
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from apps.backend.src.core.databases.postgres_db import Base
from apps.backend.tests.pg_migrations import alembic_config, reset_schema
from apps.backend.tests.pg_support import load_test_database_url
from apps.backend.tests.test_wiring import EXPECTED_TABLES

pytestmark = pytest.mark.pg


@pytest.fixture
def empty_db(pg_engine):
    """BD de pruebas sin tablas; al terminar se deja migrada a head para el resto de la sesion."""
    url = load_test_database_url()
    pg_engine.dispose()
    reset_schema(url)
    yield url
    reset_schema(url)
    command.upgrade(alembic_config(url), "head")


def table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_head_creates_exactly_the_model_tables(empty_db):
    command.upgrade(alembic_config(empty_db), "head")
    assert table_names(empty_db) == EXPECTED_TABLES | {"alembic_version"}


def test_upgrade_downgrade_upgrade_cycle(empty_db):
    config = alembic_config(empty_db)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert table_names(empty_db) == {"alembic_version"}
    command.upgrade(config, "head")
    assert table_names(empty_db) == EXPECTED_TABLES | {"alembic_version"}


def test_migrated_schema_has_no_drift_from_models(empty_db):
    command.upgrade(alembic_config(empty_db), "head")
    engine = create_engine(empty_db)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(
                conn, opts={"compare_type": True, "compare_server_default": True})
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()
