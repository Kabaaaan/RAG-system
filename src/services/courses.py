from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.database.models import Course
from src.database.repositories import CourseRepository
from src.database.session import session_scope
from src.rag_core import CourseIndexingStats
from src.rag_core.pipeline import RAGPipeline
from src.rag_core.schemas import CourseLike
from src.services.errors import ValidationError


@dataclass(slots=True, frozen=True)
class _IndexableCourse:
    id: int
    name: str
    description: str


def seed_courses(
    courses: Sequence[Mapping[str, str]],
    *,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> int:
    if not courses:
        raise ValidationError("No courses provided.")

    with session_scope(database_url=database_url, echo=echo_sql) as session:
        repo = CourseRepository(session)
        return repo.create_many_if_not_exists(courses)


def list_courses(*, database_url: str | None = None, echo_sql: bool = False) -> list[Course]:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        repo = CourseRepository(session)
        return repo.list()


def vectorize_courses(
    *,
    courses: Sequence[Course],
    recreate_collection: bool = False,
) -> CourseIndexingStats:
    indexable_courses = [
        _IndexableCourse(
            id=int(course.id),
            name=str(course.name),
            description=str(course.description),
        )
        for course in courses
    ]
    return asyncio.run(_index_courses(courses=indexable_courses, recreate_collection=recreate_collection))


async def _index_courses(
    *,
    courses: Sequence[CourseLike],
    recreate_collection: bool,
) -> CourseIndexingStats:
    pipeline = RAGPipeline()
    return await pipeline.index_courses(courses, recreate_collection=recreate_collection)


def list_and_vectorize_courses(
    *,
    database_url: str | None = None,
    echo_sql: bool = False,
    recreate_collection: bool = False,
) -> CourseIndexingStats:
    courses = list_courses(database_url=database_url, echo_sql=echo_sql)
    if not courses:
        return CourseIndexingStats(courses_count=0, chunks_count=0, collection_recreated=False)
    return vectorize_courses(courses=courses, recreate_collection=recreate_collection)
