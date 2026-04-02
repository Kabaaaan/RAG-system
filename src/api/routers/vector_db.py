from __future__ import annotations

from fastapi import APIRouter, Query, status

from src.api.schemas import (
    OperationStatusResponse,
    ResourceStatusResponse,
    UpdateVectorDbResourceRequest,
    VectorDbOperationResponse,
)

router = APIRouter(prefix="/vector-db", tags=["vector-db"])


@router.post("/update", response_model=VectorDbOperationResponse, status_code=status.HTTP_202_ACCEPTED)
def update_vector_db_resource_endpoint(
    payload: UpdateVectorDbResourceRequest,
) -> VectorDbOperationResponse:
    pass  # Поставить в очередь задачу на обновление ресурса или на создание нового, если id не передан.
    return VectorDbOperationResponse(operation_id="string", status="queued")


@router.post("/rebuild", response_model=VectorDbOperationResponse, status_code=status.HTTP_202_ACCEPTED)
def rebuild_vector_db_endpoint() -> VectorDbOperationResponse:
    pass  # Полностью переиндексировать векторную БД.
    return VectorDbOperationResponse(operation_id="string", status="queued")


@router.get("/status", response_model=OperationStatusResponse, status_code=status.HTTP_200_OK)
def get_vector_db_status_endpoint() -> OperationStatusResponse:
    pass  # Получить статус векторной БД.
    return OperationStatusResponse(status="ready")


@router.get("/resource-status", response_model=ResourceStatusResponse, status_code=status.HTTP_200_OK)
def get_vector_db_resource_status_endpoint(
    resource_id: str = Query(..., description="ID ресурса"),
    resource_type: str = Query(..., description="Тип ресурса"),
) -> ResourceStatusResponse:
    pass  # Получить статус ресурса в векторной БД.
    return ResourceStatusResponse(status="not_found")
