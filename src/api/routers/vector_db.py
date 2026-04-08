from __future__ import annotations

from fastapi import APIRouter, Query, status

from src.api.schemas import ResourceStatusResponse, StatusResponse, VectorDbOperationResponse

router = APIRouter(prefix="/vector-db", tags=["vector-db"])


@router.post("/rebuild", response_model=VectorDbOperationResponse, status_code=status.HTTP_202_ACCEPTED)
def rebuild_vector_db_endpoint() -> VectorDbOperationResponse:
    pass  # Enqueue a full vector database rebuild.
    return VectorDbOperationResponse(operation_id="string", status="queued")


@router.get("/status", response_model=StatusResponse, status_code=status.HTTP_200_OK)
def get_vector_db_status_endpoint() -> StatusResponse:
    pass  # Return the current vector database status.
    return StatusResponse(status="ready")


@router.get("/resource-status", response_model=ResourceStatusResponse, status_code=status.HTTP_200_OK)
def get_vector_db_resource_status_endpoint(
    resource_id: str = Query(..., description="Resource identifier."),
) -> ResourceStatusResponse:
    _ = resource_id
    pass  # Return the resource status in the vector database.
    return ResourceStatusResponse(status="not_found")
