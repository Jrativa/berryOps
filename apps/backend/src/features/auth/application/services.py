# src/features/auth/application/services.py
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID
from fastapi import HTTPException # Usamos HTTPException o creamos excepciones personalizadas de negocio
from apps.backend.src.core.config import settings
from apps.backend.src.features.auth.application import access_tokens
from apps.backend.src.features.auth.domain import schemas
from apps.backend.src.features.auth.domain.repository_ports import UserRepository, RoleRepository, SessionRepository
from apps.backend.src.features.auth.application import passwords_handler

class AuthService:
    """
    Servicio de autenticación que implementa la lógica de negocio.
    Recibe los puertos (repositorios) a través del constructor.
    """
    def __init__(
        self, 
        user_repo: UserRepository, 
        role_repo: RoleRepository,
        session_repo: SessionRepository
    ):
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.session_repo = session_repo

    # --- LÓGICA DE ROLES ---
    def create_role(self, role_data: schemas.RoleCreate) -> schemas.RoleResponse:
        if self.role_repo.get_by_name(role_data.name):
            raise ValueError("El rol ya existe") # Excepción pura de Python
        return self.role_repo.create(role_data)

    # --- LÓGICA DE REGISTRO DE USUARIO ---
    def register_user(self, user_data: schemas.UserCreate) -> schemas.UserResponse:
        # 1. Regla: No duplicados
        if self.user_repo.get_by_email(user_data.email):
            raise ValueError("El email ya está registrado")
        
        # 2. Utilidad: Hashear la contraseña usando tu passwords_handler[cite: 2]
        hashed_password = passwords_handler.hash_password(user_data.password)
        
        # 3. Guardar: Usamos el puerto[cite: 4]
        return self.user_repo.create(user_data, hashed_password)

    # --- LÓGICA DE LOGIN ---
    def login(self, login_data: schemas.LoginRequest) -> dict:
        # 1. Buscar usuario SOLO por username
        user = self.user_repo.get_by_username(login_data.username)
        
        # 2. Verificar existencia y contraseña
        if not user or not passwords_handler.verify_password(login_data.password, user.password_hash):
            raise ValueError("Usuario o contraseña incorrectos")
        
        # 3. Verificar si está activo
        if not user.is_active:
            raise ValueError("Usuario inactivo")

        # 4. Generar Access Token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = access_tokens.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # 5. Generar Refresh Token y guardarlo (solo su hash)
        refresh_token = self._issue_refresh_token(user.id)

        # 6. Devolver la respuesta completa requerida por el frontend
        return {
            "access_token": access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": user.username,
            "role": user.role.name
        }

    # --- LÓGICA DE REFRESH TOKEN ---
    def refresh_token(self, request: schemas.RefreshTokenRequest) -> dict:
        """Rota el refresh token: el usado queda revocado y se emite uno nuevo.
        Si llega un token ya revocado se asume robo/reutilización y se cierran
        todas las sesiones del usuario."""
        session = self.session_repo.get_by_token_hash(self._hash_token(request.refresh_token))

        if not session:
            raise ValueError("Refresh token inválido o expirado")

        if session.is_revoked:
            self.session_repo.revoke_all_for_user(session.user_id)
            raise ValueError("Refresh token inválido o expirado")

        if session.expires_at <= datetime.now(timezone.utc):
            raise ValueError("Refresh token inválido o expirado")

        user = self.user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            self.session_repo.revoke_all_for_user(session.user_id)
            raise ValueError("Usuario inactivo")

        self.session_repo.revoke(session)
        new_refresh_token = self._issue_refresh_token(user.id)

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = access_tokens.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "username": user.username,
            "role": user.role.name
        }

    # --- USUARIO ACTUAL A PARTIR DEL ACCESS TOKEN ---
    def get_user_from_token(self, token: str):
        payload = access_tokens.decode_access_token(token)
        try:
            user_id = UUID(payload.get("sub", ""))
        except ValueError:
            raise ValueError("Token inválido o expirado")
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Token inválido o expirado")
        return user

    @staticmethod
    def is_admin(user) -> bool:
        return user.role.name.strip().lower() in settings.admin_roles

    # --- LOGOUT ---
    def logout(self, request: schemas.RefreshTokenRequest) -> None:
        """Revoca la sesión asociada al refresh token. Idempotente: un token
        desconocido o ya revocado no produce error."""
        session = self.session_repo.get_by_token_hash(self._hash_token(request.refresh_token))
        if session and not session.is_revoked:
            self.session_repo.revoke(session)

    # --- UTILIDADES PRIVADAS ---
    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _issue_refresh_token(self, user_id) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.session_repo.create_session(user_id, self._hash_token(token), expires_at)
        return token