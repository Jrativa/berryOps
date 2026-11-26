# src/features/auth/domain/schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Union

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
    password: str = Field(min_length=8)

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
    password: str = Field(min_length=8, description="Contraseña del usuario")