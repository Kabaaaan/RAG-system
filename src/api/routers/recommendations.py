from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, status

from src.api.schemas import (
    GenerateRecommendationRequest,
    GetRecommendationsResponse,
    LeadActionsResponse,
    LeadRecommendationTasksResponse,
    RecommendationItemResponse,
    RecommendationStatusResponse,
    RecommendationTaskItemResponse,
    RecommendationTaskResponse,
)
from src.services import RecommendationGenerationService, RecommendationsQueryService
from src.services.errors import ValidationError
from src.task_storage import RedisClient

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendations_query_service = RecommendationsQueryService()
recommendation_generation_service = RecommendationGenerationService()


@router.post("/generate", response_model=RecommendationTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_recommendation_endpoint(payload: GenerateRecommendationRequest) -> RecommendationTaskResponse:
    try:
        task_id = await recommendation_generation_service.enqueue(
            lead_id=payload.lead_id,
            recommendation_type=payload.type,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to enqueue recommendation generation task.",
        ) from exc

    return RecommendationTaskResponse(token=task_id, status="queued")


async def _build_recommendation_status_response(token: str) -> RecommendationStatusResponse:
    resolved_token = token.strip()
    if not resolved_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recommendation task token is required.",
        )

    try:
        record = await recommendation_generation_service.get_status(task_id=resolved_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve recommendation task status from Redis.",
        ) from exc

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation task '{resolved_token}' was not found.",
        )

    return RecommendationStatusResponse(status=str(record.get("status") or "queued"))


@router.get("/status/{token}", response_model=RecommendationStatusResponse, status_code=status.HTTP_200_OK)
async def get_recommendation_status_by_path_endpoint(
    token: str = Path(..., description="Recommendation task token."),
) -> RecommendationStatusResponse:
    return await _build_recommendation_status_response(token)


@router.get("/status", response_model=RecommendationStatusResponse, status_code=status.HTTP_200_OK)
async def get_recommendation_status_endpoint(
    token: str = Query(..., description="Recommendation task token."),
) -> RecommendationStatusResponse:
    return await _build_recommendation_status_response(token)


@router.get("/actions/{lead_id}", response_model=LeadActionsResponse, status_code=status.HTTP_200_OK)
async def get_lead_actions_endpoint(
    lead_id: str = Path(..., description="Lead identifier."),
) -> LeadActionsResponse:
    actions = await recommendations_query_service.get_actions(lead_id=lead_id)
    return LeadActionsResponse(
        lead_id=actions.lead_id,
        actions=[RecommendationItemResponse(id=item.id, type=item.type, data=item.data) for item in actions.actions],
    )


@router.get("/tasks/{lead_id}", response_model=LeadRecommendationTasksResponse, status_code=status.HTTP_200_OK)
async def get_recommendation_tasks_endpoint(
    lead_id: str = Path(..., description="Lead identifier."),
) -> LeadRecommendationTasksResponse:
    try:
        async with RedisClient() as redis_client:
            tasks = await redis_client.list_generate_tasks(lead_id=lead_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve recommendation tasks from Redis.",
        ) from exc

    return LeadRecommendationTasksResponse(
        lead_id=lead_id,
        tasks=[
            RecommendationTaskItemResponse(
                id=task["id"],
                status=task["status"],
                type=task["type"],
                created_at=task["created_at"],
                updated_at=task["updated_at"],
            )
            for task in tasks
        ],
    )


@router.get("/{lead_id}", response_model=GetRecommendationsResponse, status_code=status.HTTP_200_OK)
def get_recommendations_by_path_endpoint(
    lead_id: str = Path(..., description="Lead identifier."),
) -> GetRecommendationsResponse:
    recommendations = recommendations_query_service.get_recommendations(lead_id=lead_id)
    return GetRecommendationsResponse(
        lead_id=recommendations.lead_id,
        recommendations=[RecommendationItemResponse(id=item.id, type=item.type, data=item.data) for item in recommendations.recommendations],
    )
