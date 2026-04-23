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
)
from src.services import CatalogService, ResourceIndexingService, StagingAreaService

router = APIRouter(prefix="/staging-area", tags=["staging-area"])
import_email_body = Body(default_factory=ImportEmailRequest)
catalog_service = CatalogService()
staging_area_service = StagingAreaService()
resource_indexing_service = ResourceIndexingService()


@router.post("/resorces/type", response_model=NamedEntityResponse, status_code=status.HTTP_201_CREATED)
def create_resource_type_endpoint(payload: NamedEntityRequest) -> NamedEntityResponse:
    created = catalog_service.create_resource_type(name=payload.name)
    return NamedEntityResponse(id=created.id, name=created.name)


@router.get("/resorces/type", response_model=ResourceTypesResponse, status_code=status.HTTP_200_OK)
def list_resource_types_endpoint() -> ResourceTypesResponse:
    resource_types = catalog_service.list_resource_types()
    return ResourceTypesResponse(
        resource_types=[NamedEntityResponse(id=item.id, name=item.name) for item in resource_types]
    )


@router.post("/recommendations/type", response_model=NamedEntityResponse, status_code=status.HTTP_201_CREATED)
def create_recommendation_type_endpoint(payload: NamedEntityRequest) -> NamedEntityResponse:
    created = catalog_service.create_recommendation_type(name=payload.name)
    return NamedEntityResponse(id=created.id, name=created.name)


@router.get("/recommendations/type", response_model=RecommendationTypesResponse, status_code=status.HTTP_200_OK)
def list_recommendation_types_endpoint() -> RecommendationTypesResponse:
    recommendation_types = catalog_service.list_recommendation_types()
    return RecommendationTypesResponse(
        recommendation_types=[NamedEntityResponse(id=item.id, name=item.name) for item in recommendation_types]
    )


@router.post(
    "",
    response_model=StagingAreaTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {"description": "Resource with identical text already exists."}},
)
async def index_staging_area_resource_endpoint(payload: StagingAreaResourceRequest) -> StagingAreaTaskResponse:
    created = staging_area_service.create_resource(
        resource_type=payload.resource_type,
        text=payload.text,
        url=payload.url,
        title=payload.title,
    )
    await resource_indexing_service.enqueue(resource_id=created.resource_id)
    return StagingAreaTaskResponse(resource_id=created.resource_id, status="queued")


@router.get("/{resource_id}", response_model=StagingAreaResourceResponse, status_code=status.HTTP_200_OK)
def get_staging_area_resource_endpoint(
    resource_id: int = Path(..., description="Resource identifier."),
) -> StagingAreaResourceResponse:
    resource = staging_area_service.get_resource(resource_id=resource_id)
    return StagingAreaResourceResponse(
        resource_id=resource.resource_id,
        resource_type=resource.resource_type,
        data=resource.data,
    )


@router.post("/email", response_model=ImportEmailResponse, status_code=status.HTTP_200_OK)
async def import_mautic_emails_endpoint(
    payload: ImportEmailRequest = import_email_body,
) -> ImportEmailResponse:
    result = await staging_area_service.import_emails(email_id=payload.id)
    return ImportEmailResponse(status=result.status, count=result.count)
