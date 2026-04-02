from __future__ import annotations

from fastapi import APIRouter, Query, status

from src.api.schemas import (
    GenerateRecommendationRequest,
    GetRecommendationsResponse,
    RecommendationStatusResponse,
    RecommendationTaskResponse,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/generate", response_model=RecommendationTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_recommendation_endpoint(
    payload: GenerateRecommendationRequest,
) -> RecommendationTaskResponse:
    # Поставить в очередь задачу на генерацию рекомендации и отдать токен пользователю
    # + решить где и как хранить эти токены
    pass
    return RecommendationTaskResponse(token="string", status="queued")


@router.get("/status", response_model=RecommendationStatusResponse, status_code=status.HTTP_200_OK)
def get_recommendation_status_endpoint(
    token: str = Query(..., description="Токен рекомендации"),
) -> RecommendationStatusResponse:
    pass  # Получить статус рекомендации
    return RecommendationStatusResponse(status="queued")


@router.get("", response_model=GetRecommendationsResponse, status_code=status.HTTP_200_OK)
def get_recommendations_endpoint(
    lead_id: str = Query(..., description="Идентификатор пользователя"),
) -> GetRecommendationsResponse:
    pass  # Получить список рекомендаций для этого пользователя из нашей БД
    return GetRecommendationsResponse(lead_id=lead_id, recommendations=[])
