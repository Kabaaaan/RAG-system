from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.database.models import Course
from src.database.repositories import CourseRepository
from src.database.session import session_scope
from src.services.errors import ValidationError


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
