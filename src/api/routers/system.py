from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from src.api.schemas import HealthComponentResponse, SystemHealthResponse
from src.api_client import ApiClient
from src.config.settings import AppSettings, get_settings
from src.database import session_scope
from src.query_client import RAGTasksClient
from src.task_storage import RedisClient
from src.vector_db import QdrantVectorClient

router = APIRouter(prefix="/system", tags=["system"])


async def _measure_component(
    probe: Callable[[], Awaitable[HealthComponentResponse]],
    *,
    fallback_status: str,
    include_latency: bool = True,
    include_queue_depth: bool = False,
) -> HealthComponentResponse:
    started_at = perf_counter()
    try:
        component = await probe()
    except Exception:
        component = HealthComponentResponse(status=fallback_status)

    if include_latency:
        component.latency_ms = max(0, int((perf_counter() - started_at) * 1000))
    if include_queue_depth and component.queue_depth is None:
        component.queue_depth = 0
    return component


def _probe_staging_area_sync() -> None:
    with session_scope() as session:
        session.execute(text("SELECT 1"))


async def _probe_staging_area() -> HealthComponentResponse:
    await asyncio.to_thread(_probe_staging_area_sync)
    return HealthComponentResponse(status="ready")


async def _probe_vector_db(settings: AppSettings) -> HealthComponentResponse:
    client = await QdrantVectorClient.connect(settings=settings)
    try:
        collection_exists = await client.collection_exists()
    finally:
        await client.close()
    return HealthComponentResponse(status="ready" if collection_exists else "unhealthy")


async def _probe_queue(settings: AppSettings) -> HealthComponentResponse:
    nats_client = RAGTasksClient(settings=settings)
    try:
        await nats_client.connect()
        if nats_client.js is None:
            raise RuntimeError("JetStream context is not initialized.")
        stream_info = await nats_client.js.stream_info(nats_client.stream_name)
        queue_depth = int(getattr(getattr(stream_info, "state", None), "messages", 0))
        return HealthComponentResponse(status="healthy", queue_depth=queue_depth)
    finally:
        await nats_client.close()


async def _probe_http_service(
    client_factory: Callable[..., ApiClient],
    *,
    settings: AppSettings,
) -> HealthComponentResponse:
    async with client_factory(settings=settings, raise_for_status=False) as client:
        response = await client.get("")
    return HealthComponentResponse(status="available" if response.status_code < 500 else "unavailable")


async def _probe_redis(settings: AppSettings) -> HealthComponentResponse:
    async with RedisClient(settings=settings) as redis_client:
        is_alive = bool(await redis_client._client.ping())
    return HealthComponentResponse(status="healthy" if is_alive else "unhealthy")


@router.get("/health", response_model=SystemHealthResponse, status_code=status.HTTP_200_OK)
async def system_healthcheck_endpoint(request: Request, response: Response) -> SystemHealthResponse:
    settings = get_settings()
    components = await asyncio.gather(
        _measure_component(_probe_staging_area, fallback_status="unhealthy"),
        _measure_component(lambda: _probe_vector_db(settings), fallback_status="unhealthy"),
        _measure_component(
            lambda: _probe_queue(settings),
            fallback_status="unhealthy",
            include_latency=False,
            include_queue_depth=True,
        ),
        _measure_component(
            lambda: _probe_http_service(ApiClient.for_llm, settings=settings), fallback_status="unavailable"
        ),
        _measure_component(
            lambda: _probe_http_service(ApiClient.for_embeddings, settings=settings),
            fallback_status="unavailable",
        ),
        _measure_component(lambda: _probe_redis(settings), fallback_status="unhealthy"),
    )

    component_map = {
        "staging_area": components[0],
        "vector_db": components[1],
        "queue": components[2],
        "llm_service": components[3],
        "embedding_service": components[4],
        "redis": components[5],
    }
    overall_status = "healthy"
    for name, component in component_map.items():
        if name == "vector_db" and component.status == "updating":
            continue
        if component.status in {"unhealthy", "unavailable"}:
            overall_status = "unhealthy"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            break

    started_at = getattr(request.app.state, "started_at", datetime.now(UTC))
    uptime_seconds = max(0, int((datetime.now(UTC) - started_at).total_seconds()))
    return SystemHealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        components=component_map,
        uptime_seconds=uptime_seconds,
    )
