from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.api.auth import require_api_auth
from src.api.exception_handlers import register_exception_handlers
from src.api.routers import (
    auth_router,
    recommendations_router,
    staging_area_router,
    system_router,
    vector_db_router,
)
from src.config.settings import get_settings
from src.utils import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # from src.query_client.nats_client import nats_client
        # try:
        #     await nats_client.connect()
        #     print("NATS клиент успешно подключён при старте API")
        # except Exception as e:
        #     print(f"Не удалось подключиться к NATS: {e}")

        configure_logging(settings.log_level)
        yield

    app = FastAPI(
        title="RAG System API",
        description="API interface for the RAG recommendation system.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(auth_router)
    app.include_router(system_router)
    app.include_router(staging_area_router, dependencies=[Depends(require_api_auth)])
    app.include_router(recommendations_router, dependencies=[Depends(require_api_auth)])
    app.include_router(vector_db_router, dependencies=[Depends(require_api_auth)])

    register_exception_handlers(app)
    return app


app = create_app()
