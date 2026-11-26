# src/features/auth/infrastructure/postgres/postgres_repositories.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime

# Importar modelos de Postgres
from apps.backend.src.features.auth.infrastructure.postgres import models
# Importar esquemas y puertos del Dominio
from apps.backend.src.features.auth.domain import schemas
from apps.backend.src.features.auth.domain import repository_ports

class RoleRepository(repository_ports.RoleRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str):
        return self.db.query(models.Role).filter(models.Role.name == name).first()

    def create(self, role: schemas.RoleCreate):
        db_role = models.Role(name=role.name, description=role.description)
        self.db.add(db_role)
        self.db.flush()
        self.db.refresh(db_role)
        return db_role

class UserRepository(repository_ports.UserRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str):
        return self.db.query(models.User).filter(models.User.email == email).first()

    def get_by_username(self, username: str):
        return self.db.query(models.User).filter(models.User.username == username).first()

    def get_by_id(self, user_id):
        return self.db.query(models.User).filter(models.User.id == user_id).first()

    def exists_any(self) -> bool:
        return self.db.query(models.User.id).first() is not None

    def get_by_login_id(self, user_identifier: str):
        return self.db.query(models.User).filter(
            or_(
                models.User.email == user_identifier,
                models.User.username == user_identifier
            )
        ).first()

    def create(self, user: schemas.UserCreate, hashed_password: str):
        db_user = models.User(
            username=user.username,
            email=user.email,
            password_hash=hashed_password, 
            full_name=user.full_name,
            role_id=user.role_id,
            created_by=user.created_by
        )
        self.db.add(db_user)
        self.db.flush()
        self.db.refresh(db_user)
        return db_user

class SessionRepository(repository_ports.SessionRepository):
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id, token_hash: str, expires_at: datetime):
        db_session = models.UserSession(
            user_id=user_id,
            refresh_token=token_hash,
            expires_at=expires_at
        )
        self.db.add(db_session)
        self.db.flush()
        self.db.refresh(db_session)
        return db_session

    def get_by_token_hash(self, token_hash: str):
        return self.db.query(models.UserSession).filter(
            models.UserSession.refresh_token == token_hash
        ).first()

    def revoke(self, session) -> None:
        session.is_revoked = True
        self.db.flush()

    def revoke_all_for_user(self, user_id) -> None:
        self.db.query(models.UserSession).filter(
            models.UserSession.user_id == user_id,
            models.UserSession.is_revoked == False
        ).update({"is_revoked": True})
        self.db.flush()