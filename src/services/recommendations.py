from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from qdrant_client.http.models.models import FieldCondition, Filter, MatchValue

from src.api_client import ApiClient
from src.config.settings import AppSettings, get_settings
from src.database import RecommendationRepository, session_scope
from src.mauitc import MauticClient
from src.query_client import RAGTasksClient
from src.rag_core.embeddings import fetch_embedding
from src.rag_core.llm import generate_llm_response
from src.services.errors import ValidationError
from src.task_storage import RedisClient
from src.vector_db import QdrantVectorClient

GENERATE_TASK_TTL_SECONDS = 24 * 60 * 60
RECOMMENDATION_TOP_K = 5
RECOMMENDATION_SEARCH_K = 20
RESOURCE_TYPE_BY_RECOMMENDATION_TYPE = {
    "cold": "article",
    "hot": "course",
}
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


@dataclass(slots=True, frozen=True)
class RecommendationItemRecord:
    id: str
    type: str
    data: dict[str, object]


@dataclass(slots=True, frozen=True)
class LeadRecommendationsRecord:
    lead_id: str
    recommendations: list[RecommendationItemRecord]


@dataclass(slots=True, frozen=True)
class LeadActionsRecord:
    lead_id: str
    actions: list[RecommendationItemRecord]


@dataclass(slots=True, frozen=True)
class RetrievedResourceRecord:
    resource_id: int
    resource_type: str
    title: str
    url: str | None
    chunk_text: str
    score: float


@dataclass(slots=True, frozen=True)
class GeneratedRecommendationRecord:
    task_id: str
    lead_id: int
    recommendation_type: str
    prompt_text: str
    query_text: str
    retrieved_resources: list[RetrievedResourceRecord]
    recommendation_payload: dict[str, object]
    recommendation_text: str
    recommendation_id: int


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
                data={key: value for key, value in event.items() if key not in {"id", "activity_kind"} and value is not None},
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
    def _deserialize_recommendation_payload(text: str) -> dict[str, object]:
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


class RecommendationGenerationService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()

    async def enqueue(self, *, lead_id: str, recommendation_type: str | None = None) -> str:
        normalized_lead_id = self._parse_lead_id(lead_id)
        normalized_type = self._normalize_recommendation_type(recommendation_type, allow_empty=True)
        task_id = str(uuid4())
        record = self._build_record(
            task_id=task_id,
            lead_id=normalized_lead_id,
            recommendation_type=normalized_type,
            status="queued",
        )

        async with RedisClient(settings=self._settings) as redis_client:
            await redis_client.set_record(self._build_key(task_id), record, ttl=GENERATE_TASK_TTL_SECONDS)

        nats_client = RAGTasksClient(settings=self._settings)
        try:
            await nats_client.connect()
            await nats_client.publish_generate(
                lead_id=str(normalized_lead_id),
                rec_type=normalized_type,
                task_id=task_id,
            )
        except Exception as exc:
            await self.mark_failed(task_id=task_id, error=str(exc), recommendation_type=normalized_type)
            raise
        finally:
            await nats_client.close()

        return task_id

    async def get_status(self, *, task_id: str) -> dict[str, object] | None:
        async with RedisClient(settings=self._settings) as redis_client:
            return await redis_client.get_generate_task(task_id=task_id)

    async def mark_processing(self, *, task_id: str, recommendation_type: str | None = None) -> None:
        await self._update_record(
            task_id=task_id,
            status="processing",
            error=None,
            recommendation_type=self._normalize_recommendation_type(recommendation_type, allow_empty=True),
        )

    async def mark_completed(
        self,
        *,
        task_id: str,
        recommendation_type: str | None = None,
        recommendation_id: int | None = None,
    ) -> None:
        extras: dict[str, object] = {}
        if recommendation_id is not None:
            extras["recommendation_id"] = recommendation_id
        await self._update_record(
            task_id=task_id,
            status="completed",
            error=None,
            recommendation_type=self._normalize_recommendation_type(recommendation_type, allow_empty=True),
            extras=extras,
        )

    async def mark_failed(
        self,
        *,
        task_id: str,
        error: str | None = None,
        recommendation_type: str | None = None,
    ) -> None:
        await self._update_record(
            task_id=task_id,
            status="failed",
            error=error,
            recommendation_type=self._normalize_recommendation_type(recommendation_type, allow_empty=True),
        )

    async def generate(
        self,
        *,
        task_id: str,
        lead_id: str,
        recommendation_type: str | None = None,
    ) -> GeneratedRecommendationRecord:
        normalized_lead_id = self._parse_lead_id(lead_id)

        async with MauticClient(settings=self._settings) as mautic_client:
            resolved_type = self._normalize_recommendation_type(recommendation_type, allow_empty=True)
            if resolved_type is None:
                resolved_type = await self._resolve_recommendation_type(mautic_client, lead_id=normalized_lead_id)

            digital_footprints = await mautic_client.get_digital_footprint(normalized_lead_id)
            query_text = self._format_digital_footprints(digital_footprints)
            retrieved_resources = await self._retrieve_resources(
                query_text=query_text,
                recommendation_type=resolved_type,
            )
            prompt_text = self._render_prompt(
                recommendation_type=resolved_type,
                available_content=self._format_available_content(retrieved_resources),
                digital_traces=query_text,
            )
            raw_llm_text, _ = await generate_llm_response(settings=self._settings, prompt=prompt_text)
            recommendation_payload = self._parse_recommendation_payload(raw_llm_text)
            stored_payload = {
                **recommendation_payload,
                "_system": {
                    "task_id": task_id,
                    "lead_id": str(normalized_lead_id),
                    "type": resolved_type,
                },
            }

            recommendation_text = str(recommendation_payload.get("recommendation") or raw_llm_text).strip()
            if not recommendation_text:
                raise ValueError("Generated recommendation does not contain a user-facing message.")

            existing_recommendation_id = self._find_existing_recommendation_id(
                lead_id=normalized_lead_id,
                task_id=task_id,
            )
            if existing_recommendation_id is not None:
                return GeneratedRecommendationRecord(
                    task_id=task_id,
                    lead_id=normalized_lead_id,
                    recommendation_type=resolved_type,
                    prompt_text=prompt_text,
                    query_text=query_text,
                    retrieved_resources=retrieved_resources,
                    recommendation_payload=stored_payload,
                    recommendation_text=recommendation_text,
                    recommendation_id=existing_recommendation_id,
                )

            await mautic_client.save_recommendation(
                normalized_lead_id,
                recommendation_text,
                field_alias=self._settings.mautic_recommendation_field_alias,
            )

        serialized_payload = json.dumps(stored_payload, ensure_ascii=False)
        with session_scope() as session:
            repository = RecommendationRepository(session)
            created = repository.create(
                lead_id=normalized_lead_id,
                text=serialized_payload,
                recommendation_type_name=resolved_type,
            )
            recommendation_id = int(created.id)

        return GeneratedRecommendationRecord(
            task_id=task_id,
            lead_id=normalized_lead_id,
            recommendation_type=resolved_type,
            prompt_text=prompt_text,
            query_text=query_text,
            retrieved_resources=retrieved_resources,
            recommendation_payload=stored_payload,
            recommendation_text=recommendation_text,
            recommendation_id=recommendation_id,
        )

    async def _retrieve_resources(self, *, query_text: str, recommendation_type: str) -> list[RetrievedResourceRecord]:
        async with ApiClient.for_embeddings(settings=self._settings) as embedding_client:
            query_vector = await fetch_embedding(
                client=embedding_client,
                text=f"query: {query_text}",
                settings=self._settings,
            )

        resource_type = self._resource_type_for_recommendation(recommendation_type)
        query_filter = self._build_resource_type_filter(resource_type)
        async with await QdrantVectorClient.connect(settings=self._settings) as qdrant_client:
            if query_filter is None:
                scored_points = await qdrant_client.search(query_vector=query_vector, k=RECOMMENDATION_SEARCH_K)
            else:
                scored_points = await qdrant_client.search_with_filter(
                    query_vector=query_vector,
                    query_filter=query_filter,
                    k=RECOMMENDATION_SEARCH_K,
                )

        resources: dict[int, RetrievedResourceRecord] = {}
        for point in scored_points:
            payload = point.payload if isinstance(point.payload, dict) else {}
            raw_resource_id = payload.get("resource_id")
            if not isinstance(raw_resource_id, int):
                continue

            title = str(payload.get("title") or "").strip() or f"Resource #{raw_resource_id}"
            resource_type = str(payload.get("resource_type") or "").strip()
            url = str(payload.get("url") or "").strip() or None
            chunk_text = str(payload.get("chunk_text") or "").strip()
            score = float(point.score or 0.0)

            existing = resources.get(raw_resource_id)
            if existing is None or score > existing.score:
                resources[raw_resource_id] = RetrievedResourceRecord(
                    resource_id=raw_resource_id,
                    resource_type=resource_type,
                    title=title,
                    url=url,
                    chunk_text=chunk_text,
                    score=score,
                )

        retrieved_resources = sorted(resources.values(), key=lambda item: item.score, reverse=True)[:RECOMMENDATION_TOP_K]
        if not retrieved_resources:
            raise ValueError("No similar resources were found in Qdrant for the provided digital footprint.")
        return retrieved_resources

    @staticmethod
    def _resource_type_for_recommendation(recommendation_type: str) -> str | None:
        return RESOURCE_TYPE_BY_RECOMMENDATION_TYPE.get(recommendation_type)

    @staticmethod
    def _build_resource_type_filter(resource_type: str | None) -> Filter | None:
        if resource_type is None:
            return None
        return Filter(
            must=[
                FieldCondition(
                    key="resource_type",
                    match=MatchValue(value=resource_type),
                )
            ]
        )

    async def _resolve_recommendation_type(self, mautic_client: MauticClient, *, lead_id: int) -> str:
        stage = await mautic_client.get_contact_stage(contact_id=lead_id)
        if not stage:
            raise ValueError(f"Unable to determine Mautic stage for lead '{lead_id}'.")

        candidates = [
            str(stage.get("alias") or "").strip().lower(),
            str(stage.get("name") or "").strip().lower(),
            str(stage.get("description") or "").strip().lower(),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            if "after_sale" in candidate or "post_sale" in candidate or "postsale" in candidate:
                return "after_sale"
            if "after" in candidate and "sale" in candidate:
                return "after_sale"
            if "\u043f\u043e\u0441\u043b\u0435\u043f\u0440\u043e\u0434" in candidate or "\u043f\u043e\u0441\u0442\u043f\u0440\u043e\u0434" in candidate:
                return "after_sale"
            if "cold" in candidate or "\u0445\u043e\u043b\u043e\u0434" in candidate:
                return "cold"
            if "warm" in candidate or "\u0442\u0435\u043f\u043b" in candidate:
                return "warm"
            if "hot" in candidate or "\u0433\u043e\u0440\u044f\u0447" in candidate:
                return "hot"

        raise ValueError(f"Unsupported Mautic stage for lead '{lead_id}': {stage!r}")

    def _render_prompt(self, *, recommendation_type: str, available_content: str, digital_traces: str) -> str:
        prompt_path = PROMPTS_DIR / f"{recommendation_type}.txt"
        if not prompt_path.exists():
            raise ValueError(f"Prompt file for recommendation type '{recommendation_type}' was not found.")
        template = prompt_path.read_text(encoding="utf-8")
        return template.format(available_content=available_content, digital_traces=digital_traces)

    @staticmethod
    def _format_digital_footprints(events: list[dict[str, object]]) -> str:
        if not events:
            return "No user activity was found in Mautic."

        lines: list[str] = []
        for index, event in enumerate(events[:25], start=1):
            summary = str(event.get("summary") or event.get("title") or event.get("activity_kind") or "").strip()
            timestamp = str(event.get("timestamp") or "").strip()
            description = str(event.get("description") or "").strip()
            entities = event.get("entities")

            parts: list[str] = []
            if summary:
                parts.append(summary)
            if description and description.lower() not in summary.lower():
                parts.append(description)
            if isinstance(entities, dict) and entities:
                parts.append(json.dumps(entities, ensure_ascii=False))
            if timestamp:
                parts.append(f"timestamp={timestamp}")

            line = " | ".join(part for part in parts if part)
            if line:
                lines.append(f"{index}. {line}")

        return "\n".join(lines) if lines else "No user activity was found in Mautic."

    @staticmethod
    def _format_available_content(resources: list[RetrievedResourceRecord]) -> str:
        lines: list[str] = []
        for index, resource in enumerate(resources, start=1):
            fragment = resource.chunk_text.replace("\n", " ").strip()
            if len(fragment) > 500:
                fragment = fragment[:497] + "..."
            lines.append(
                "\n".join(
                    [
                        f"{index}. {resource.title}",
                        f"Type: {resource.resource_type or 'unknown'}",
                        f"URL: {resource.url or 'n/a'}",
                        f"Fragment: {fragment or 'n/a'}",
                        f"Relevance: {resource.score:.3f}",
                    ]
                )
            )
        return "\n\n".join(lines)

    @staticmethod
    def _parse_recommendation_payload(raw_text: str) -> dict[str, object]:
        stripped = raw_text.strip()
        if not stripped:
            raise ValueError("LLM returned an empty recommendation payload.")

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("LLM did not return valid JSON.") from None
            payload = json.loads(stripped[start : end + 1])

        if not isinstance(payload, dict):
            raise ValueError("Recommendation payload must be a JSON object.")
        return payload

    def _find_existing_recommendation_id(self, *, lead_id: int, task_id: str) -> int | None:
        with session_scope() as session:
            repository = RecommendationRepository(session)
            for item in repository.list_for_lead(lead_id=lead_id, limit=100):
                try:
                    payload = json.loads(item.text)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                system_payload = payload.get("_system")
                if not isinstance(system_payload, dict):
                    continue
                if str(system_payload.get("task_id") or "").strip() == task_id:
                    return int(item.id)
        return None

    @staticmethod
    def _normalize_recommendation_type(value: str | None, *, allow_empty: bool) -> str | None:
        if value is None:
            return None if allow_empty else ""
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            return None if allow_empty else ""
        if not (PROMPTS_DIR / f"{normalized}.txt").exists():
            raise ValidationError(f"Unknown recommendation type '{value}'.")
        return normalized

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
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _build_key(task_id: str) -> str:
        return f"gen:{task_id}"

    def _build_record(
        self,
        *,
        task_id: str,
        lead_id: int,
        recommendation_type: str | None,
        status: str,
    ) -> dict[str, object]:
        timestamp = self._timestamp()
        record: dict[str, object] = {
            "task_id": task_id,
            "lead_id": str(lead_id),
            "status": status,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        if recommendation_type:
            record["type"] = recommendation_type
        return record

    async def _update_record(
        self,
        *,
        task_id: str,
        status: str,
        error: str | None,
        recommendation_type: str | None,
        extras: dict[str, object] | None = None,
    ) -> None:
        async with RedisClient(settings=self._settings) as redis_client:
            key = self._build_key(task_id)
            record = await redis_client.get_record(key)
            if record is None:
                raise ValueError(f"Recommendation task '{task_id}' was not found in Redis.")

            record["status"] = status
            record["updated_at"] = self._timestamp()
            if recommendation_type:
                record["type"] = recommendation_type
            if error is None:
                record.pop("error", None)
            else:
                record["error"] = error
            if extras:
                record.update(extras)

            await redis_client.set_record(key, record, ttl=GENERATE_TASK_TTL_SECONDS)
