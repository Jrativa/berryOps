# src/core/databases/postgres_db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from apps.backend.src.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Inicializa la base de datos específica para Postgres."""
    from apps.backend.src.features.auth.infrastructure.postgres import models  # noqa: F401
    from apps.backend.src.features.inventory.infrastructure.postgres import models as inventory_models  # noqa: F401

    Base.metadata.create_all(bind=engine)