"""Entorno de Alembic. Unico lugar que decide la URL de la BD y el metadata de los modelos."""
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

# `apps.backend...` debe poder importarse sea cual sea el directorio de trabajo
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from apps.backend.src.core.databases.postgres_db import Base  # noqa: E402
from apps.backend.src.features.auth.infrastructure.postgres import models as _auth  # noqa: E402,F401
from apps.backend.src.features.inventory.infrastructure.postgres import models as _inv  # noqa: E402,F401

URL_ATTRIBUTE = "sqlalchemy_url"
config = context.config
target_metadata = Base.metadata


def resolve_url() -> str:
    """URL explicita puesta en `config.attributes` (tests) o, si no, la de la aplicacion."""
    explicit = config.attributes.get(URL_ATTRIBUTE)
    if explicit:
        return explicit
    from apps.backend.src.core.config import settings
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(url=resolve_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(resolve_url())
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
