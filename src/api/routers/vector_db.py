from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, status

from src.api.schemas import ResourceStatusResponse, StatusResponse, VectorDbOperationResponse
from src.services import ResourceIndexingService
from src.task_storage import RedisClient
from src.vector_db import QdrantVectorClient

router = APIRouter(prefix="/vector-db", tags=["vector-db"])
resource_indexing_service = ResourceIndexingService()


@router.post("/rebuild", response_model=VectorDbOperationResponse, status_code=status.HTTP_202_ACCEPTED)
def rebuild_vector_db_endpoint() -> VectorDbOperationResponse:
    pass  # Enqueue a full vector database rebuild.
    return VectorDbOperationResponse(operation_id="string", status="queued")


@router.get("/status", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def get_vector_db_status_endpoint() -> StatusResponse:
    try:
        async with RedisClient() as redis_client:
            active_tasks = await redis_client.get_active_idx_count()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to determine vector DB status from Redis.",
        ) from exc
    return StatusResponse(status="updating" if active_tasks > 0 else "ready")


@router.get("/resource-status/{resource_id}", response_model=ResourceStatusResponse, status_code=status.HTTP_200_OK)
async def get_vector_db_resource_status_endpoint(
    resource_id: int = Path(..., description="Resource identifier."),
    create_embedding: bool = Query(default=False, description="Queue indexing when resource is absent in Qdrant."),
) -> ResourceStatusResponse:
    try:
        async with await QdrantVectorClient.connect() as qdrant_client:
            exists_in_qdrant = await qdrant_client.has_payload_value(key="resource_id", value=resource_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to determine resource status from Qdrant.",
        ) from exc

    if exists_in_qdrant:
        return ResourceStatusResponse(status="created")

    status_record = await resource_indexing_service.get_status(resource_id=resource_id)
    if status_record is not None:
        current_status = str(status_record.get("status", "not_found"))
        if current_status in {"queued", "processing"}:
            return ResourceStatusResponse(status=current_status)

    if create_embedding:
        try:
            await resource_indexing_service.enqueue(resource_id=resource_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to enqueue resource indexing task.",
            ) from exc
        return ResourceStatusResponse(status="queued")

    return ResourceStatusResponse(status="not_found")
