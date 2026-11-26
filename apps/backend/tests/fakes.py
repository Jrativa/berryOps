"""Repositorios en memoria que implementan los puertos del dominio."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace


class FakeRoleRepository:
    def __init__(self):
        self.items = {}

    def get_by_name(self, name):
        return next((r for r in self.items.values() if r.name == name), None)

    def get_by_id(self, role_id):
        return self.items.get(role_id)

    def create(self, role):
        obj = SimpleNamespace(id=uuid.uuid4(), name=role.name, description=role.description)
        self.items[obj.id] = obj
        return obj


class FakeUserRepository:
    def __init__(self, roles: FakeRoleRepository):
        self.roles = roles
        self.items = {}

    def get_by_email(self, email):
        return next((u for u in self.items.values() if u.email == email), None)

    def get_by_username(self, username):
        return next((u for u in self.items.values() if u.username == username), None)

    def get_by_id(self, user_id):
        return self.items.get(user_id)

    def exists_any(self):
        return bool(self.items)

    def create(self, user, hashed_password):
        obj = SimpleNamespace(
            id=uuid.uuid4(), username=user.username, email=user.email,
            password_hash=hashed_password, full_name=user.full_name,
            role_id=user.role_id, role=self.roles.get_by_id(user.role_id),
            is_active=True, created_at=datetime.now(timezone.utc),
            created_by=user.created_by,
        )
        self.items[obj.id] = obj
        return obj


class FakeSessionRepository:
    def __init__(self):
        self.items = []

    def create_session(self, user_id, token_hash, expires_at):
        obj = SimpleNamespace(
            id=uuid.uuid4(), user_id=user_id, refresh_token=token_hash,
            expires_at=expires_at, is_revoked=False,
        )
        self.items.append(obj)
        return obj

    def get_by_token_hash(self, token_hash):
        return next((s for s in self.items if s.refresh_token == token_hash), None)

    def revoke(self, session):
        session.is_revoked = True

    def revoke_all_for_user(self, user_id):
        for s in self.items:
            if s.user_id == user_id:
                s.is_revoked = True
