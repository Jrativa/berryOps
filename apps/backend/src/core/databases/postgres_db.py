# src/core/databases/postgres_db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from apps.backend.src.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

