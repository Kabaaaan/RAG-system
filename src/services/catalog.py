from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from src.database import RecommendationTypeRepository, ResourceTypeRepository, session_scope
from src.services.errors import AlreadyExistsError, ValidationError


@dataclass(slots=True, frozen=True)
class NamedCatalogRecord:
    id: int
    name: str


class CatalogService:
    def list_resource_types(self) -> list[NamedCatalogRecord]:
        with session_scope() as session:
            repository = ResourceTypeRepository(session)
            return [NamedCatalogRecord(id=item.id, name=item.name) for item in repository.get_all()]

    def create_resource_type(self, *, name: str) -> NamedCatalogRecord:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("Resource type name must not be empty.")
        with session_scope() as session:
            repository = ResourceTypeRepository(session)
            existing = repository.get_by_name(name=normalized_name)
            if existing is not None:
                raise AlreadyExistsError(f"Resource type '{normalized_name}' already exists.")
            try:
                created = repository.create(name=normalized_name)
            except IntegrityError as exc:
                raise AlreadyExistsError(f"Resource type '{normalized_name}' already exists.") from exc
            return NamedCatalogRecord(id=created.id, name=created.name)

    def list_recommendation_types(self) -> list[NamedCatalogRecord]:
        with session_scope() as session:
            repository = RecommendationTypeRepository(session)
            return [NamedCatalogRecord(id=item.id, name=item.name) for item in repository.get_all()]

    def create_recommendation_type(self, *, name: str) -> NamedCatalogRecord:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("Recommendation type name must not be empty.")
        with session_scope() as session:
            repository = RecommendationTypeRepository(session)
            existing = repository.get_by_name(name=normalized_name)
            if existing is not None:
                raise AlreadyExistsError(f"Recommendation type '{normalized_name}' already exists.")
            try:
                created = repository.create(name=normalized_name)
            except IntegrityError as exc:
                raise AlreadyExistsError(f"Recommendation type '{normalized_name}' already exists.") from exc
            return NamedCatalogRecord(id=created.id, name=created.name)
