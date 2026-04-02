from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.db import init_db
from src.services.errors import (
    AlreadyExistsError,
    NotFoundError,
    ServiceError,
    ValidationError,
)


@dataclass(slots=True, frozen=True)
class SeedUsersStats:
    created: int
    updated: int
    skipped: int


@dataclass(slots=True, frozen=True)
class VectorizationStats:
    courses_count: int
    chunks_count: int
    collection_recreated: bool


@dataclass(slots=True, frozen=True)
class UserRecord:
    id: int
    login: str
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class CourseRecord:
    id: int
    name: str
    description: str


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
    return ServiceError(
        f"Service '{name}' is no longer available because User/Course-based tables were removed."
    )


def create_user(
    *, login: str, digital_footprints: str = "", database_url: str | None = None, echo_sql: bool = False
) -> UserRecord:
    raise _deprecated_service("create_user")


def list_users(*, database_url: str | None = None, echo_sql: bool = False) -> list[UserRecord]:
    raise _deprecated_service("list_users")


def seed_users(
    users: list[dict[str, Any]],
    *,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> SeedUsersStats:
    raise _deprecated_service("seed_users")


def seed_courses(
    courses: list[dict[str, str]],
    *,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> int:
    raise _deprecated_service("seed_courses")


def list_courses(*, database_url: str | None = None, echo_sql: bool = False) -> list[CourseRecord]:
    raise _deprecated_service("list_courses")


def list_and_vectorize_courses(
    *,
    database_url: str | None = None,
    echo_sql: bool = False,
    recreate_collection: bool = False,
) -> VectorizationStats:
    raise _deprecated_service("list_and_vectorize_courses")


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
    "AlreadyExistsError",
    "CourseRecord",
    "GeneratedRecommendation",
    "NotFoundError",
    "RecommendationRecord",
    "RetrievedCourseRecord",
    "SeedUsersStats",
    "ServiceError",
    "UserRecord",
    "ValidationError",
    "VectorizationStats",
    "add_recommendation",
    "create_user",
    "generate_recommendation",
    "init_db",
    "list_and_vectorize_courses",
    "list_courses",
    "list_recommendations",
    "list_users",
    "seed_courses",
    "seed_users",
]
