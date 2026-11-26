# src/features/auth/domain/schemas.py
from pydantic import AfterValidator, BaseModel, EmailStr, ConfigDict, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Annotated, Optional, Union

# bcrypt solo usa los primeros 72 BYTES: se rechaza lo que se truncaría en silencio
BCRYPT_MAX_BYTES = 72


def _fits_bcrypt(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"La contraseña no puede superar {BCRYPT_MAX_BYTES} bytes (UTF-8)")
    return password


Password = Annotated[str, Field(min_length=8), AfterValidator(_fits_bcrypt)]

# -------------------------
# Role schemas
# -------------------------
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# -------------------------
# User schemas
# -------------------------
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role_id: UUID
    created_by: Optional[str] = None

class UserCreate(UserBase):
    password: Password

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -------------------------
# Auth / Token schemas
# -------------------------
class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    username: str
    role: str 

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LoginRequest(BaseModel):
    # Solo pedimos username, con una validación simple
    username: str = Field(min_length=3, description="Nombre de usuario")
    password: Password