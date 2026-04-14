from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.database import RecommendationRepository, session_scope
from src.mauitc import MauticClient
from src.services.errors import ValidationError


@dataclass(slots=True, frozen=True)
class RecommendationItemRecord:
    id: str
    type: str
    data: dict[str, Any]


@dataclass(slots=True, frozen=True)
class LeadRecommendationsRecord:
    lead_id: str
    recommendations: list[RecommendationItemRecord]


@dataclass(slots=True, frozen=True)
class LeadActionsRecord:
    lead_id: str
    actions: list[RecommendationItemRecord]


class RecommendationsQueryService:
    def get_recommendations(self, *, lead_id: str) -> LeadRecommendationsRecord:
        normalized_lead_id = self._parse_lead_id(lead_id)
        with session_scope() as session:
            repository = RecommendationRepository(session)
            recommendations = repository.list_for_lead(lead_id=normalized_lead_id)
            items = [
                RecommendationItemRecord(
                    id=str(item.id),
                    type=item.recommendation_type.name,
                    data=self._deserialize_recommendation_payload(item.text),
                )
                for item in recommendations
            ]
            return LeadRecommendationsRecord(lead_id=str(normalized_lead_id), recommendations=items)

    async def get_actions(self, *, lead_id: str) -> LeadActionsRecord:
        normalized_lead_id = self._parse_lead_id(lead_id)
        async with MauticClient() as client:
            events = await client.get_contact_activity_events(lead_id=normalized_lead_id)

        items = [
            RecommendationItemRecord(
                id=str(index + 1 if event.get("id") is None else event["id"]),
                type=str(event.get("activity_kind", "unknown")),
                data={
                    key: value
                    for key, value in event.items()
                    if key not in {"id", "activity_kind"} and value is not None
                },
            )
            for index, event in enumerate(events)
        ]
        return LeadActionsRecord(lead_id=str(normalized_lead_id), actions=items)

    @staticmethod
    def _parse_lead_id(lead_id: str) -> int:
        normalized = lead_id.strip()
        if not normalized:
            raise ValidationError("lead_id must not be empty.")
        try:
            return int(normalized)
        except ValueError as exc:
            raise ValidationError("lead_id must be an integer-compatible value.") from exc

    @staticmethod
    def _deserialize_recommendation_payload(text: str) -> dict[str, Any]:
        stripped_text = text.strip()
        if not stripped_text:
            return {"text": ""}
        try:
            payload = json.loads(stripped_text)
        except json.JSONDecodeError:
            return {"text": text}
        if isinstance(payload, dict):
            return payload
        return {"value": payload}
