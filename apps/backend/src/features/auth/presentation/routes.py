# src/features/auth/presentation/routes.py
from fastapi import APIRouter, Depends, HTTPException, Response
from apps.backend.src.core.uow import UnitOfWork
from apps.backend.src.features.auth.domain import schemas
from apps.backend.src.features.auth.application.services import AuthService
from apps.backend.src.features.auth.dependencies import (
    get_auth_service,
    get_current_user,
    require_admin,
)

router = APIRouter()

@router.post("/roles/", response_model=schemas.RoleResponse)
def create_role(
    role: schemas.RoleCreate,
    auth_service: AuthService = Depends(get_auth_service),
    _current_user = Depends(require_admin),
):
    try:
        return auth_service.create_role(role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/users/", response_model=schemas.UserResponse)
def create_user(
    user: schemas.UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    _current_user = Depends(require_admin),
):
    try:
        return auth_service.register_user(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{username}", response_model=schemas.UserResponse)
def get_user(
    username: str,
    auth_service: AuthService = Depends(get_auth_service),
    current_user = Depends(get_current_user),
):
    # Solo el propio perfil; cualquier otro nombre (exista o no) da la misma respuesta (sin enumeración)
    user = auth_service.user_repo.get_by_username(username) if username == current_user.username else None
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@router.post("/login", response_model=schemas.LoginResponse) # Actualizamos el response_model
def login(
    login_data: schemas.LoginRequest, 
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        return auth_service.login(login_data)
    except ValueError as e:
        if str(e) == "Usuario inactivo":
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/refresh", response_model=schemas.LoginResponse)
def refresh_token(
    request: schemas.RefreshTokenRequest,
    uow: UnitOfWork,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return auth_service.refresh_token(request)
    except ValueError as e:
        # Única excepción a "rollback ante cualquier error": la detección de reutilización (o de usuario
        # inactivo) revoca todas las sesiones y responde 401; esa revocación debe persistir. Si el fallo
        # no escribió nada, este commit no hace nada.
        uow.commit()
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout", status_code=204)
def logout(
    request: schemas.RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    auth_service.logout(request)
    return Response(status_code=204)
