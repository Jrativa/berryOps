# src/features/auth/dependencies.py
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from apps.backend.src.core.uow import UnitOfWork

from apps.backend.src.features.auth.application.services import AuthService
from apps.backend.src.features.auth.infrastructure.postgres import repositories as repos

def get_auth_service(db: UnitOfWork) -> AuthService:
    """Fábrica que inyecta los repositorios Postgres"""
    return AuthService(
        user_repo=repos.UserRepository(db),
        role_repo=repos.RoleRepository(db),
        session_repo=repos.SessionRepository(db)
    )

# Autenticación por Bearer token
bearer_scheme = HTTPBearer(auto_error=False)

def _unauthorized(detail: str = "No autenticado") -> HTTPException:
    return HTTPException(
        status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"}
    )

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Exige un access token válido y devuelve el usuario autenticado."""
    if credentials is None:
        raise _unauthorized()
    try:
        return auth_service.get_user_from_token(credentials.credentials)
    except ValueError as e:
        raise _unauthorized(str(e))

def require_admin(user=Depends(get_current_user), auth_service: AuthService = Depends(get_auth_service)):
    """Exige un usuario autenticado con rol de administrador (sin excepciones de arranque:
    el primer admin se crea con el CLI, `python -m apps.backend.src.cli bootstrap`)."""
    if not auth_service.is_admin(user):
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return user
