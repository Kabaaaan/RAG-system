from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthComponentResponse(BaseSchema):
    status: str = Field(..., description="Component health status.")
    latency_ms: int | None = Field(default=None, description="Component latency in milliseconds.")
    queue_depth: int | None = Field(default=None, description="Queue depth when applicable.")


class SystemHealthResponse(BaseSchema):
    status: str = Field(..., description="Overall system health status.")
    timestamp: datetime = Field(..., description="Response timestamp.")
    components: dict[str, HealthComponentResponse] = Field(..., description="Per-component health details.")
    uptime_seconds: int = Field(..., description="Application uptime in seconds.")


class AuthKeyRequest(BaseSchema):
    secret: str = Field(..., description="Shared secret used to request an API key.")


class AuthKeyResponse(BaseSchema):
    api_key: str = Field(..., serialization_alias="api-key", description="Issued JWT API key.")


class StatusResponse(BaseSchema):
    status: str = Field(..., description="Operation status.")


class NamedEntityRequest(BaseSchema):
    name: str = Field(..., description="Entity name.")


class NamedEntityResponse(BaseSchema):
    id: int = Field(..., description="Entity identifier.")
    name: str = Field(..., description="Entity name.")


class ResourceTypesResponse(BaseSchema):
    resource_types: list[NamedEntityResponse] = Field(
        default_factory=list, description="Available resource types."
    )


class RecommendationTypesResponse(BaseSchema):
    recommendation_types: list[NamedEntityResponse] = Field(
        default_factory=list,
        description="Available recommendation types.",
    )


class StagingAreaResourceRequest(BaseSchema):
    resource_id: str = Field(..., description="External resource identifier.")
    resource_type: str = Field(..., description="Resource type.")
    data: dict[str, Any] = Field(default_factory=dict, description="Serialized resource payload.")


class StagingAreaTaskResponse(BaseSchema):
    resource_id: str = Field(..., description="Resource identifier.")
    status: str = Field(..., description="Task status.")


class StagingAreaResourceResponse(BaseSchema):
    resource_id: str = Field(..., description="Resource identifier.")
    resource_type: str = Field(..., description="Resource type.")
    data: dict[str, Any] = Field(default_factory=dict, description="Stored resource payload.")


class ImportEmailRequest(BaseSchema):
    id: int | None = Field(default=None, description="Mautic email identifier.")


class ImportEmailResponse(BaseSchema):
    status: str = Field(..., description="Import result status.")
    count: int | None = Field(default=None, description="Number of imported emails for bulk operations.")


class VectorDbOperationResponse(BaseSchema):
    operation_id: str = Field(..., description="Queued operation identifier.")
    status: str = Field(..., description="Task status.")


class ResourceStatusResponse(BaseSchema):
    status: str = Field(..., description="Resource status in the vector database.")


class GenerateRecommendationRequest(BaseSchema):
    lead_id: str = Field(..., description="Lead identifier.")
    type: str | None = Field(default=None, description="Recommendation type.")


class RecommendationTaskResponse(BaseSchema):
    token: str = Field(..., description="Recommendation task token.")
    status: str = Field(..., description="Task status.")


class RecommendationStatusResponse(BaseSchema):
    status: str = Field(..., description="Current recommendation generation status.")


class RecommendationItemResponse(BaseSchema):
    id: str = Field(..., description="Recommendation identifier.")
    type: str = Field(..., description="Recommendation type.")
    data: dict[str, Any] = Field(default_factory=dict, description="Recommendation payload.")


class GetRecommendationsResponse(BaseSchema):
    lead_id: str = Field(..., description="Lead identifier.")
    recommendations: list[RecommendationItemResponse] = Field(
        default_factory=list,
        description="Stored recommendations for the lead.",
    )
