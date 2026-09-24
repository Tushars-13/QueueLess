"""Application exception hierarchy and a structured error response model."""

from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class AppError(Exception):
    """Base application error with an HTTP status code and a stable code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str, *, code: str = "not_found") -> None:
        super().__init__(message, code=code, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, message: str, *, code: str = "conflict") -> None:
        super().__init__(message, code=code, status_code=status.HTTP_409_CONFLICT)


class AuthenticationError(AppError):
    def __init__(
        self, message: str, *, code: str = "authentication_error"
    ) -> None:
        super().__init__(
            message, code=code, status_code=status.HTTP_401_UNAUTHORIZED
        )


class DatabaseError(AppError):
    def __init__(self, message: str = "Database error") -> None:
        super().__init__(
            message,
            code="database_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _error_body(code: str, message: str, details: Optional[Any] = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON exception handlers for the application to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "validation_error",
                "Request validation failed",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        # Do not leak driver internals to the client in production.
        message = (
            "Database error"
            if not settings_debug()
            else f"Database error: {exc}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("database_error", message),
        )


def settings_debug() -> bool:
    from app.core.config import get_settings

    return get_settings().app_debug
