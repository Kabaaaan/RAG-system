from __future__ import annotations

import click
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.services.errors import AlreadyExistsError, NotFoundError, ServiceError, ValidationError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def handle_validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(AlreadyExistsError)
    async def handle_already_exists(_: Request, exc: AlreadyExistsError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(click.ClickException)
    async def handle_click_exception(_: Request, exc: click.ClickException) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(httpx.HTTPStatusError)
    async def handle_http_status_error(_: Request, exc: httpx.HTTPStatusError) -> JSONResponse:
        detail = exc.response.text or str(exc)
        return JSONResponse(status_code=exc.response.status_code, content={"detail": detail})

    @app.exception_handler(ServiceError)
    async def handle_service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
