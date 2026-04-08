from __future__ import annotations

from fastapi import APIRouter, Body, Path, status

from src.api.schemas import (
    ImportEmailRequest,
    ImportEmailResponse,
    NamedEntityRequest,
    NamedEntityResponse,
    RecommendationTypesResponse,
    ResourceTypesResponse,
    StagingAreaResourceRequest,
    StagingAreaResourceResponse,
    StagingAreaTaskResponse,
    StatusResponse,
)

router = APIRouter(prefix="/staging-area", tags=["staging-area"])
api_staging_area_router = APIRouter(prefix="/api/staging-area", tags=["staging-area"])
import_email_body = Body(default_factory=ImportEmailRequest)


@router.get("/status", response_model=StatusResponse, status_code=status.HTTP_200_OK)
def get_staging_area_status_endpoint() -> StatusResponse:
    # Return the current staging-area status.
    pass
    return StatusResponse(status="ready")


@router.post("/resorces/type", response_model=NamedEntityResponse, status_code=status.HTTP_201_CREATED)
def create_resource_type_endpoint(payload: NamedEntityRequest) -> NamedEntityResponse:
    # Create a new resource type for staging-area ingestion.
    pass
    return NamedEntityResponse(id=1, name=payload.name)


@router.get("/resorces/type", response_model=ResourceTypesResponse, status_code=status.HTTP_200_OK)
def list_resource_types_endpoint() -> ResourceTypesResponse:
    # Return all configured resource types.
    pass
    return ResourceTypesResponse(resource_types=[])


@router.post("/recommendations/type", response_model=NamedEntityResponse, status_code=status.HTTP_201_CREATED)
def create_recommendation_type_endpoint(payload: NamedEntityRequest) -> NamedEntityResponse:
    # Create a new recommendation type.
    pass
    return NamedEntityResponse(id=1, name=payload.name)


@router.get(
    "/recommendations/type", response_model=RecommendationTypesResponse, status_code=status.HTTP_200_OK
)
def list_recommendation_types_endpoint() -> RecommendationTypesResponse:
    # Return all configured recommendation types.
    pass
    return RecommendationTypesResponse(recommendation_types=[])


@router.post("", response_model=StagingAreaTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def index_staging_area_resource_endpoint(payload: StagingAreaResourceRequest) -> StagingAreaTaskResponse:
    # Store the resource in staging-area and enqueue downstream indexing in vector DB.
    pass
    return StagingAreaTaskResponse(resource_id=payload.resource_id, status="queued")


@router.get("/{resource_id}", response_model=StagingAreaResourceResponse, status_code=status.HTTP_200_OK)
def get_staging_area_resource_endpoint(
    resource_id: str = Path(..., description="Resource identifier."),
) -> StagingAreaResourceResponse:
    # Fetch a resource from staging-area by its identifier.
    pass
    return StagingAreaResourceResponse(resource_id=resource_id, resource_type="string", data={})


@router.post("/email", response_model=ImportEmailResponse, status_code=status.HTTP_200_OK)
def import_mautic_emails_endpoint(
    payload: ImportEmailRequest = import_email_body,
) -> ImportEmailResponse:
    # Import one email by id or import all missing emails from Mautic into staging-area.
    pass
    if payload.id is not None:
        return ImportEmailResponse(status="created")
    return ImportEmailResponse(status="created", count=0)


@api_staging_area_router.post("/email", response_model=ImportEmailResponse, status_code=status.HTTP_200_OK)
def import_mautic_emails_api_endpoint(
    payload: ImportEmailRequest = import_email_body,
) -> ImportEmailResponse:
    # Keep the documented /api/staging-area/email endpoint as an alias.
    pass
    if payload.id is not None:
        return ImportEmailResponse(status="created")
    return ImportEmailResponse(status="created", count=0)
