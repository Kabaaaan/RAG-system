from __future__ import annotations

from fastapi import APIRouter, Path, Query, status

from src.api.schemas import (
    GenerateRecommendationRequest,
    GetRecommendationsResponse,
    LeadActionsResponse,
    RecommendationItemResponse,
    RecommendationStatusResponse,
    RecommendationTaskResponse,
)
from src.services import RecommendationsQueryService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendations_query_service = RecommendationsQueryService()


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


@router.get("/actions/{lead_id}", response_model=LeadActionsResponse, status_code=status.HTTP_200_OK)
async def get_lead_actions_endpoint(
    lead_id: str = Path(..., description="Lead identifier."),
) -> LeadActionsResponse:
    actions = await recommendations_query_service.get_actions(lead_id=lead_id)
    return LeadActionsResponse(
        lead_id=actions.lead_id,
        actions=[
            RecommendationItemResponse(id=item.id, type=item.type, data=item.data) for item in actions.actions
        ],
    )


@router.get("/{lead_id}", response_model=GetRecommendationsResponse, status_code=status.HTTP_200_OK)
def get_recommendations_by_path_endpoint(
    lead_id: str = Path(..., description="Lead identifier."),
) -> GetRecommendationsResponse:
    recommendations = recommendations_query_service.get_recommendations(lead_id=lead_id)
    return GetRecommendationsResponse(
        lead_id=recommendations.lead_id,
        recommendations=[
            RecommendationItemResponse(id=item.id, type=item.type, data=item.data)
            for item in recommendations.recommendations
        ],
    )
