from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.database.models import Course, Recommendation, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, login: str, digital_footprints: str = "") -> User:
        user = User(login=login, digital_footprints=digital_footprints)
        self._session.add(user)
        self._session.flush()
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return cast(User | None, self._session.get(User, user_id))

    def get_by_login(self, login: str) -> User | None:
        statement: Select[tuple[User]] = select(User).where(User.login == login)
        return cast(User | None, self._session.execute(statement).scalar_one_or_none())

    def list(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        statement: Select[tuple[User]] = select(User).order_by(User.id.asc()).limit(limit).offset(offset)
        return list(self._session.scalars(statement).all())

    def update_digital_footprints(self, *, user_id: int, digital_footprints: str) -> User | None:
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.digital_footprints = digital_footprints
        self._session.flush()
        return user


class CourseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, name: str, description: str) -> Course:
        course = Course(name=name, description=description)
        self._session.add(course)
        self._session.flush()
        return course

    def get_by_id(self, course_id: int) -> Course | None:
        return cast(Course | None, self._session.get(Course, course_id))

    def get_by_name(self, name: str) -> Course | None:
        statement: Select[tuple[Course]] = select(Course).where(Course.name == name)
        return cast(Course | None, self._session.execute(statement).scalar_one_or_none())

    def list(self, *, limit: int = 100, offset: int = 0) -> list[Course]:
        statement: Select[tuple[Course]] = (
            select(Course).order_by(Course.id.asc()).limit(limit).offset(offset)
        )
        return list(self._session.scalars(statement).all())

    def create_many_if_not_exists(self, courses: Sequence[Mapping[str, str]]) -> int:
        created = 0
        for course in courses:
            name = course.get("name") or course.get("title") or ""
            description = course.get("description") or ""
            normalized_name = name.strip()
            if not normalized_name:
                continue
            if self.get_by_name(normalized_name) is not None:
                continue
            self.create(name=normalized_name, description=description.strip())
            created += 1
        return created


class RecommendationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, user_id: int, text: str) -> Recommendation:
        recommendation = Recommendation(user_id=user_id, text=text)
        self._session.add(recommendation)
        self._session.flush()
        return recommendation

    def list_for_user(self, *, user_id: int, limit: int = 100) -> list[Recommendation]:
        statement: Select[tuple[Recommendation]] = (
            select(Recommendation)
            .where(Recommendation.user_id == user_id)
            .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())
