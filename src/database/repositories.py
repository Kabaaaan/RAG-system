from __future__ import annotations

from typing import cast

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.database.models import RAGResource, Recommendation, RecommendationType, ResourceType


class ResourceTypeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_name(self, *, name: str) -> ResourceType | None:
        statement: Select[tuple[ResourceType]] = select(ResourceType).where(ResourceType.name == name)
        resource_type = self._session.scalar(statement)
        return cast(ResourceType | None, resource_type)

    def create(self, *, name: str) -> ResourceType:
        resource_type = ResourceType(name=name)
        self._session.add(resource_type)
        self._session.flush()
        return resource_type

    def get_or_create(self, *, name: str) -> ResourceType:
        existing = self.get_by_name(name=name)
        if existing is not None:
            return existing
        return self.create(name=name)

    def get_all(self) -> list[ResourceType]:
        statement: Select[tuple[ResourceType]] = select(ResourceType)
        result = self._session.scalars(statement).all()
        return list(result)


class ResourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._resource_types = ResourceTypeRepository(session)

    def add(
        self,
        *,
        text: str,
        resource_type_id: int | None = None,
        resource_type_name: str | None = None,
        title: str | None = None,
        url: str | None = None,
    ) -> RAGResource:
        resolved_type_id = self._resolve_resource_type_id(
            resource_type_id=resource_type_id,
            resource_type_name=resource_type_name,
        )
        resource = RAGResource(
            url=url,
            type_id=resolved_type_id,
            title=title,
            text=text,
        )
        self._session.add(resource)
        self._session.flush()
        return resource

    def list(self, *, limit: int = 100) -> list[RAGResource]:
        statement: Select[tuple[RAGResource]] = (
            select(RAGResource).order_by(RAGResource.created_at.desc(), RAGResource.id.desc()).limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def _resolve_resource_type_id(
        self,
        *,
        resource_type_id: int | None,
        resource_type_name: str | None,
    ) -> int:
        if resource_type_id is not None and resource_type_name is not None:
            raise ValueError("Pass either resource_type_id or resource_type_name, not both.")
        if resource_type_id is not None:
            return resource_type_id
        if resource_type_name is None:
            raise ValueError("resource_type_id or resource_type_name is required.")
        resource_type = self._resource_types.get_or_create(name=resource_type_name)
        return cast(int, resource_type.id)


class RecommendationTypeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_name(self, *, name: str) -> RecommendationType | None:
        statement: Select[tuple[RecommendationType]] = select(RecommendationType).where(
            RecommendationType.name == name
        )
        recommendation_type = self._session.scalar(statement)
        return cast(RecommendationType | None, recommendation_type)

    def create(self, *, name: str) -> RecommendationType:
        recommendation_type = RecommendationType(name=name)
        self._session.add(recommendation_type)
        self._session.flush()
        return recommendation_type

    def get_or_create(self, *, name: str) -> RecommendationType:
        existing = self.get_by_name(name=name)
        if existing is not None:
            return existing
        return self.create(name=name)

    def get_all(self) -> list[RecommendationType]:
        statement: Select[tuple[RecommendationType]] = select(RecommendationType)
        result = self._session.scalars(statement).all()
        return list(result)


class RecommendationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._recommendation_types = RecommendationTypeRepository(session)

    def create(
        self,
        *,
        lead_id: int,
        text: str,
        recommendation_type_id: int | None = None,
        recommendation_type_name: str | None = None,
    ) -> Recommendation:
        resolved_type_id = self._resolve_recommendation_type_id(
            recommendation_type_id=recommendation_type_id,
            recommendation_type_name=recommendation_type_name,
        )
        recommendation = Recommendation(
            lead_id=lead_id,
            type_id=resolved_type_id,
            text=text,
        )
        self._session.add(recommendation)
        self._session.flush()
        return recommendation

    def list_for_lead(self, *, lead_id: int, limit: int = 100) -> list[Recommendation]:
        statement: Select[tuple[Recommendation]] = (
            select(Recommendation)
            .where(Recommendation.lead_id == lead_id)
            .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def _resolve_recommendation_type_id(
        self,
        *,
        recommendation_type_id: int | None,
        recommendation_type_name: str | None,
    ) -> int:
        if recommendation_type_id is not None and recommendation_type_name is not None:
            raise ValueError("Pass either recommendation_type_id or recommendation_type_name, not both.")
        if recommendation_type_id is not None:
            return recommendation_type_id
        if recommendation_type_name is None:
            raise ValueError("recommendation_type_id or recommendation_type_name is required.")
        recommendation_type = self._recommendation_types.get_or_create(name=recommendation_type_name)
        return cast(int, recommendation_type.id)
