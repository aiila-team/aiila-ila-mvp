"""
Global API error schema: {"error": "...", "detail": "..."}
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, str):
            detail = exc.detail
        else:
            detail = str(exc.detail)
        body = {"error": "http_error", "detail": detail}
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            body["error"] = "unauthorized"
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            body["error"] = "forbidden"
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            body["error"] = "not_found"
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "validation_error", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error: {}", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
        )
