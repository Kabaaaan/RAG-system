from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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
    resource_types: list[NamedEntityResponse] = Field(default_factory=list, description="Available resource types.")


class RecommendationTypesResponse(BaseSchema):
    recommendation_types: list[NamedEntityResponse] = Field(
        default_factory=list,
        description="Available recommendation types.",
    )


class StagingAreaResourceRequest(BaseSchema):
    resource_type: str = Field(..., description="Resource type.")
    text: str = Field(..., description="Resource text content.")
    url: str | None = Field(default=None, description="Optional resource URL.")
    title: str | None = Field(default=None, description="Optional resource title.")


class StagingAreaTaskResponse(BaseSchema):
    resource_id: int = Field(..., description="Resource identifier.")
    status: str = Field(..., description="Task status.")


class StagingAreaResourceResponse(BaseSchema):
    resource_id: int = Field(..., description="Resource identifier.")
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


class LeadActionsResponse(BaseSchema):
    lead_id: str = Field(..., description="Lead identifier.")
    actions: list[RecommendationItemResponse] = Field(
        default_factory=list,
        description="Normalized user actions from Mautic.",
    )


class RecommendationTaskItemResponse(BaseSchema):
    id: str = Field(..., description="Task identifier.")
    status: str = Field(..., description="Task status.")
    type: str = Field(..., description="Task type.")
    created_at: str = Field(..., description="Task creation timestamp.")
    updated_at: str = Field(..., description="Task last update timestamp.")


class LeadRecommendationTasksResponse(BaseSchema):
    lead_id: str = Field(..., description="Lead identifier.")
    tasks: list[RecommendationTaskItemResponse] = Field(
        default_factory=list,
        description="Recommendation-generation tasks stored in Redis.",
    )


LeadType = Literal["cold", "warm", "hot", "after_sale"]


class PromptResponse(BaseSchema):
    lead_type: LeadType = Field(..., description="Recommendation type / funnel stage.")
    prompt: str = Field(..., description="Prompt text.")


class UpdatePromptRequest(BaseSchema):
    lead_type: LeadType = Field(..., description="Recommendation type / funnel stage.")
    prompt: str = Field(..., description="Updated prompt text.")


class CreateMauticFieldRequest(BaseSchema):
    name: str = Field(..., description="Human-readable contact field name.")


class MauticFieldResponse(BaseSchema):
    id: int | None = Field(default=None, description="Mautic field identifier when returned by Mautic.")
    name: str = Field(..., description="Human-readable field name.")
    alias: str = Field(..., description="Mautic field alias.")
    type: str = Field(..., description="Mautic field type.")
    object: str = Field(..., description="Mautic object type.")


class UpdateMauticFieldRequest(BaseSchema):
    lead_id: str = Field(..., description="Lead identifier in Mautic.")
    field: str = Field(..., description="Contact field alias.")
    value: Any = Field(..., description="New field value.")


class UpdateMauticFieldResponse(BaseSchema):
    lead_id: str = Field(..., description="Lead identifier in Mautic.")
    field: str = Field(..., description="Updated contact field alias.")
    value: Any = Field(..., description="Updated field value.")
    status: str = Field(..., description="Update operation status.")
