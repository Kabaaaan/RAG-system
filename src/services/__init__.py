from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.services.catalog import CatalogService, NamedCatalogRecord
from src.services.db import init_db
from src.services.errors import ServiceError
from src.services.indexing import ResourceIndexingService
from src.services.recommendations import (
    GeneratedRecommendationRecord,
    LeadActionsRecord,
    LeadRecommendationsRecord,
    RecommendationGenerationService,
    RecommendationItemRecord,
    RecommendationsQueryService,
    RetrievedResourceRecord,
)
from src.services.staging_area import ImportedEmailResult, StagingAreaResourceRecord, StagingAreaService


@dataclass(slots=True, frozen=True)
class RecommendationRecord:
    id: int
    text: str
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RetrievedCourseRecord:
    course_id: int
    name: str
    description: str
    score: float


@dataclass(slots=True, frozen=True)
class GeneratedRecommendation:
    recommendation: RecommendationRecord
    retrieved_courses: list[RetrievedCourseRecord]
    query_text: str
    debug_file_path: Path


def _deprecated_service(name: str) -> ServiceError:
    return ServiceError(f"Service '{name}' is no longer available because User/Course-based tables were removed.")


def add_recommendation(
    *,
    login: str,
    text: str,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> RecommendationRecord:
    raise _deprecated_service("add_recommendation")


def list_recommendations(
    *,
    login: str,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> list[RecommendationRecord]:
    raise _deprecated_service("list_recommendations")


def generate_recommendation(
    *,
    login: str,
    top_k: int = 5,
    search_k: int = 20,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> GeneratedRecommendation:
    raise _deprecated_service("generate_recommendation")


__all__ = [
    "GeneratedRecommendation",
    "CatalogService",
    "GeneratedRecommendationRecord",
    "ImportedEmailResult",
    "LeadActionsRecord",
    "LeadRecommendationsRecord",
    "NamedCatalogRecord",
    "ResourceIndexingService",
    "RecommendationGenerationService",
    "RecommendationRecord",
    "RecommendationItemRecord",
    "RecommendationsQueryService",
    "RetrievedResourceRecord",
    "RetrievedCourseRecord",
    "StagingAreaResourceRecord",
    "StagingAreaService",
    "add_recommendation",
    "generate_recommendation",
    "init_db",
    "list_recommendations",
]
