from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GenerateRecommendationRequest(BaseSchema):
    lead_id: str = Field(..., description="Идентификатор пользователя")
    type: str = Field(..., description="Тип рекомендации")


class RecommendationTaskResponse(BaseSchema):
    token: str = Field(..., description="Токен рекомендации")
    status: str = Field(..., description="Статус постановки задачи в очередь")


class RecommendationStatusResponse(BaseSchema):
    status: str = Field(..., description="Текущий статус генерации рекомендации")


class RecommendationItemResponse(BaseSchema):
    id: str = Field(..., description="Идентификатор рекомендации")
    type: str = Field(..., description="Тип рекомендации")
    data: dict[str, Any] = Field(..., description="Данные рекомендации")


class GetRecommendationsResponse(BaseSchema):
    lead_id: str = Field(..., description="Идентификатор пользователя")
    recommendations: list[RecommendationItemResponse] = Field(
        default_factory=list,
        description="Список рекомендаций пользователя",
    )


class UpdateVectorDbResourceRequest(BaseSchema):
    resource_type: str = Field(..., description="Тип ресурса")
    resource_id: str | None = Field(
        default=None,
        description="ID ресурса в основной БД. Если не передан, будет создан новый ресурс этого типа.",
    )


class VectorDbOperationResponse(BaseSchema):
    operation_id: str = Field(..., description="Идентификатор операции")
    status: str = Field(..., description="Статус постановки задачи в очередь")


class OperationStatusResponse(BaseSchema):
    status: str = Field(..., description="Текущий статус операции")


class ResourceStatusResponse(BaseSchema):
    status: str = Field(..., description="Статус ресурса в векторной БД")
