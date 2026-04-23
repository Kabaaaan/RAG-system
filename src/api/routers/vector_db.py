from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import ResourceStatusResponse, StatusResponse, VectorDbOperationResponse
from src.services import ResourceIndexingService
from src.task_storage import RedisClient

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


@router.get("/resource-status", response_model=ResourceStatusResponse, status_code=status.HTTP_200_OK)
async def get_vector_db_resource_status_endpoint(
    resource_id: int = Query(..., description="Resource identifier."),
) -> ResourceStatusResponse:
    status_record = await resource_indexing_service.get_status(resource_id=resource_id)
    if status_record is None:
        return ResourceStatusResponse(status="not_found")
    return ResourceStatusResponse(status=str(status_record.get("status", "not_found")))
