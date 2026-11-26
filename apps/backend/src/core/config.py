# src/core/config.py
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# apps/backend/.env, sin depender del directorio desde el que se arranque
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

SECRET_KEY_MIN_LENGTH = 32
DEFAULT_CORS_ORIGINS = "http://localhost:5173"


def parse_cors_origins(raw: str) -> list[str]:
    """Orígenes separados por coma. Se rechaza `*` porque la API permite credenciales."""
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS no puede contener '*' porque la API permite credenciales")
    return origins


class Settings(BaseSettings):
    # hide_input_in_errors: un error de validación nunca debe imprimir valores (SECRET_KEY, DB_PASSWORD)
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", hide_input_in_errors=True)

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Nombres de rol (separados por coma, sin distinguir mayúsculas) con permisos de administrador
    ADMIN_ROLE_NAMES: str = "admin,administrador"

    # Orígenes CORS permitidos (separados por coma)
    CORS_ORIGINS: str = DEFAULT_CORS_ORIGINS

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_key_is_long_enough(cls, value: str) -> str:
        if len(value) < SECRET_KEY_MIN_LENGTH:
            raise ValueError(f"SECRET_KEY debe tener al menos {SECRET_KEY_MIN_LENGTH} caracteres")
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _cors_origins_are_valid(cls, value: str) -> str:
        parse_cors_origins(value)
        return value

    @property
    def cors_origins(self) -> list[str]:
        return parse_cors_origins(self.CORS_ORIGINS)

    @property
    def admin_roles(self) -> set[str]:
        return {r.strip().lower() for r in self.ADMIN_ROLE_NAMES.split(",") if r.strip()}

    @property
    def DATABASE_URL(self) -> str:
        """URL con la contraseña escapada (caracteres como @ : / % # funcionan)."""
        return URL.create(
            "postgresql", username=self.DB_USER, password=self.DB_PASSWORD,
            host=self.DB_HOST, port=int(self.DB_PORT), database=self.DB_NAME,
        ).render_as_string(hide_password=False)


settings = Settings()
