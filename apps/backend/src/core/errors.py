# src/core/errors.py
"""Envelope de errores de la API: `{"detail": str, "code": str, "details"?: ...}`.

`detail` se conserva (el frontend lo lee); `code` es el identificador legible por máquina.
Los errores de validación de FastAPI (422) mantienen su forma original.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE",
}

# pgcode de PostgreSQL -> (status HTTP, code, mensaje genérico). Nunca se expone el texto de la BD.
_INTEGRITY_BY_PGCODE = {
    "23505": (409, "CONFLICT", "Ya existe un registro con esos datos"),
    "23503": (422, "INVALID_REFERENCE", "Referencia a un recurso que no existe o que sigue en uso"),
    "23514": (422, "CONSTRAINT_VIOLATION", "Los datos no cumplen una restricción de integridad"),
}
_INTEGRITY_FALLBACK = (409, "CONFLICT", "La operación entra en conflicto con los datos existentes")


def error_body(detail, code: str, details=None) -> dict:
    body = {"detail": detail, "code": code}
    if details is not None:
        body["details"] = details
    return body


def http_error(e: Exception) -> HTTPException:
    """Error de dominio -> HTTP: LookupError = recurso inexistente (o ajeno) 404; ValueError = regla de negocio 400."""
    status = 404 if isinstance(e, LookupError) else 400
    return HTTPException(status_code=status, detail=str(e.args[0]) if e.args else str(e))


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _CODE_BY_STATUS.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(error_body(exc.detail, code), status_code=exc.status_code, headers=exc.headers)


async def _integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    pgcode = getattr(exc.orig, "pgcode", None)
    status, code, message = _INTEGRITY_BY_PGCODE.get(pgcode, _INTEGRITY_FALLBACK)
    # Solo metadatos: ni el SQL ni los parámetros (podrían contener PII o secretos)
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    logger.warning("IntegrityError pgcode=%s constraint=%s", pgcode, constraint)
    return JSONResponse(error_body(message, code), status_code=status)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
