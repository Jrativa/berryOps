# src/core/databases/__init__.py
from apps.backend.src.core.databases.postgres_db import SessionLocal

__all__ = ["SessionLocal"]
