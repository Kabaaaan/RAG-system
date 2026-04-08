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
def generate_recommendation_endpoint(payload: GenerateRecommendationRequest) -> RecommendationTaskResponse:
    # Enqueue recommendation generation and return a tracking token.
    pass
    return RecommendationTaskResponse(token="string", status="queued")


@router.get("/status", response_model=RecommendationStatusResponse, status_code=status.HTTP_200_OK)
def get_recommendation_status_endpoint(
    token: str = Query(..., description="Recommendation task token."),
) -> RecommendationStatusResponse:
    _ = token
    pass  # Return the current recommendation generation status.
    return RecommendationStatusResponse(status="queued")


@router.get("", response_model=GetRecommendationsResponse, status_code=status.HTTP_200_OK)
def get_recommendations_endpoint(
    lead_id: str = Query(..., description="Lead identifier."),
) -> GetRecommendationsResponse:
    pass  # Return persisted recommendations for the requested lead.
    return GetRecommendationsResponse(lead_id=lead_id, recommendations=[])
