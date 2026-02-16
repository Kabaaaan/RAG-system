from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exception_handlers import register_exception_handlers
from src.api.routers import courses_router, db_router, recommendations_router, users_router
from src.config.settings import get_settings
from src.utils import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        yield

    app = FastAPI(
        title="RAG System API",
        description="API interface for the RAG recommendation system.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(db_router)
    app.include_router(courses_router)
    app.include_router(users_router)
    app.include_router(recommendations_router)

    register_exception_handlers(app)
    return app


app = create_app()
