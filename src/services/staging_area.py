from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.database import ResourceRepository, ResourceTypeRepository, session_scope
from src.mauitc import MauticClient
from src.services.errors import NotFoundError, ValidationError


@dataclass(slots=True, frozen=True)
class StagingAreaResourceRecord:
    resource_id: int
    resource_type: str
    data: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ImportedEmailResult:
    status: str
    count: int | None = None


class StagingAreaService:
    def create_resource(
        self,
        *,
        resource_type: str,
        text: str,
        url: str | None = None,
        title: str | None = None,
    ) -> StagingAreaResourceRecord:
        normalized_type = resource_type.strip()
        if not normalized_type:
            raise ValidationError("resource_type must not be empty.")
        normalized_text = text.strip()
        if not normalized_text:
            raise ValidationError("text must not be empty.")
        normalized_title = title.strip() if isinstance(title, str) and title.strip() else None
        normalized_url = url.strip() if isinstance(url, str) and url.strip() else None

        with session_scope() as session:
            resource_types = ResourceTypeRepository(session)
            resource_type_record = resource_types.get_by_name(name=normalized_type)
            if resource_type_record is None:
                raise ValidationError(
                    f"Unknown resource type '{normalized_type}'. Seed static reference data first."
                )

            resources = ResourceRepository(session)
            created = resources.add(
                resource_type_id=resource_type_record.id,
                title=normalized_title,
                url=normalized_url,
                text=normalized_text,
            )
            return self._to_resource_record(created)

    def get_resource(self, *, resource_id: int) -> StagingAreaResourceRecord:
        with session_scope() as session:
            resources = ResourceRepository(session)
            resource = resources.get_by_id(resource_id=resource_id)
            if resource is None:
                raise NotFoundError(f"Resource '{resource_id}' was not found.")
            return self._to_resource_record(resource)

    async def import_emails(self, *, email_id: int | None = None) -> ImportedEmailResult:
        async with MauticClient() as client:
            if email_id is not None:
                email_payload = await client.get_emails(email_id=email_id)
                if not isinstance(email_payload, dict):
                    return ImportedEmailResult(status="not_found")

                created = self._store_mautic_email(email_payload)
                return ImportedEmailResult(status="created" if created else "already_exists")

            emails_payload = await client.get_emails()
            if not isinstance(emails_payload, list):
                return ImportedEmailResult(status="created", count=0)

            created_count = 0
            for email_payload in emails_payload:
                if self._store_mautic_email(email_payload):
                    created_count += 1
            return ImportedEmailResult(status="created", count=created_count)

    @staticmethod
    def _extract_optional_string(data: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    return normalized
        return None

    @classmethod
    def _extract_resource_text(cls, data: dict[str, Any]) -> str:
        for key in ("text", "clean_text", "content", "body", "description"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise ValidationError(
            "Resource payload must contain one of: text, clean_text, content, body, description."
        )

    def _store_mautic_email(self, email_payload: dict[str, Any]) -> bool:
        email_identifier = str(email_payload.get("id", "")).strip()
        if not email_identifier:
            raise ValidationError("Mautic email payload does not contain an id.")

        with session_scope() as session:
            resource_types = ResourceTypeRepository(session)
            email_resource_type = resource_types.get_by_name(name="mautic_email")
            if email_resource_type is None:
                raise ValidationError(
                    "Resource type 'mautic_email' is missing. Run the reference-data SQL seed first."
                )

            resources = ResourceRepository(session)
            title = self._extract_optional_string(email_payload, "subject", "name", "title")
            resources.add(
                resource_type_id=email_resource_type.id,
                title=title,
                text=self._extract_resource_text(email_payload),
            )
            return True

    @staticmethod
    def _to_resource_record(resource: Any) -> StagingAreaResourceRecord:
        resource_type = getattr(resource, "resource_type", None)
        resource_type_name = getattr(resource_type, "name", None)
        return StagingAreaResourceRecord(
            resource_id=resource.id,
            resource_type=resource_type_name or "",
            data={
                "title": resource.title,
                "url": resource.url,
                "text": resource.text,
            },
        )
