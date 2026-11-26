# src/features/auth/dependencies.py
import importlib
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from apps.backend.src.core.config import settings
from apps.backend.src.core.databases import get_db

from apps.backend.src.features.auth.application.services import AuthService

# 1. Construimos la ruta del módulo dinámicamente según el motor del .env
# Si es "postgres" -> src.features.auth.infrastructure.postgres.repositories
# Si es "mongo"    -> src.features.auth.infrastructure.mongo.repositories
repo_module_path = f"src.features.auth.infrastructure.{settings.DB_ENGINE}.repositories"

# 2. Importamos el módulo UNA SOLA VEZ cuando arranca FastAPI
try:
    repos = importlib.import_module(repo_module_path)
except ImportError:
    raise NotImplementedError(f"Repositorios no implementados para el motor: {settings.DB_ENGINE}")

# 3. La fábrica ahora es 100% agnóstica y súper corta
def get_auth_service(db = Depends(get_db)) -> AuthService:
    """Fábrica dinámica que inyecta las dependencias correctas"""
    return AuthService(
        user_repo=repos.UserRepository(db),
        role_repo=repos.RoleRepository(db),
        session_repo=repos.SessionRepository(db)
    )

# 4. Autenticación por Bearer token
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

def require_admin_or_bootstrap(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Exige un usuario con rol de administrador. Mientras no exista ningún
    usuario se permite el acceso sin token (crear el rol y el admin inicial)."""
    if not auth_service.has_users():
        return None
    user = get_current_user(credentials, auth_service)
    if not auth_service.is_admin(user):
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return user