from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from qdrant_client.http.models.models import FieldCondition, Filter, MatchValue

from src.api_client.api_client import ApiClient
from src.config.settings import AppSettings, get_settings
from src.preprocessing import create_embedding_question_input
from src.rag_core.embeddings import fetch_embedding
from src.rag_core.schemas import RetrievedCourse, RetrievedResourceRecord
from src.utils import get_logger
from src.vector_db import QdrantVectorClient

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Resource-type routing for typed recommendations
# ---------------------------------------------------------------------------

#: Maps a recommendation type name to the Qdrant ``resource_type`` payload
#: value that should be used when filtering search results.  Types that are
#: absent from this mapping are retrieved without a resource-type filter
#: (all indexed content is considered).
RESOURCE_TYPE_BY_RECOMMENDATION_TYPE: dict[str, str] = {
    "cold": "article",
    "hot": "course",
}


def resource_type_for_recommendation(recommendation_type: str) -> str | None:
    """Return the Qdrant resource_type filter value for a recommendation type.

    Returns ``None`` when the recommendation type has no specific resource
    restriction (e.g. "warm", "after_sale").
    """
    return RESOURCE_TYPE_BY_RECOMMENDATION_TYPE.get(recommendation_type)


def build_resource_type_filter(resource_type: str | None) -> Filter | None:
    """Build a Qdrant :class:`Filter` that restricts results to a resource type.

    Returns ``None`` if *resource_type* is ``None`` (no filtering).
    """
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


async def retrieve_resources(
    *,
    query_text: str,
    settings: AppSettings,
    resource_type_filter: str | None = None,
    top_k: int = 5,
    search_k: int = 20,
) -> list[RetrievedResourceRecord]:
    """Retrieve the most relevant resources from the vector DB for *query_text*.

    This is the core RAG retrieval step for the typed-recommendation pipeline.
    The function embeds *query_text*, searches Qdrant with an optional
    resource-type filter, deduplicates by resource ID (keeping the highest
    scored chunk per resource), and returns the top *top_k* results.

    Args:
        query_text: Raw digital-footprint profile text.  A ``"query: "``
            prefix is added internally before embedding.
        settings: Application settings (used to reach the embedding API and
            Qdrant).
        resource_type_filter: Optional Qdrant ``resource_type`` payload value
            to restrict results (e.g. ``"article"``, ``"course"``).
        top_k: Maximum number of deduplicated resources to return.
        search_k: Number of candidate points to fetch from Qdrant before
            deduplication.

    Returns:
        Resources sorted by semantic relevance score, descending.

    Raises:
        ValueError: If no resources are found.
    """
    async with ApiClient.for_embeddings(settings=settings) as embedding_client:
        query_vector = await fetch_embedding(
            client=embedding_client,
            text=f"query: {query_text}",
            settings=settings,
        )

    query_filter = build_resource_type_filter(resource_type_filter)
    async with await QdrantVectorClient.connect(settings=settings) as qdrant_client:
        if query_filter is None:
            scored_points = await qdrant_client.search(query_vector=query_vector, k=search_k)
        else:
            scored_points = await qdrant_client.search_with_filter(
                query_vector=query_vector,
                query_filter=query_filter,
                k=search_k,
            )

    resources: dict[int, RetrievedResourceRecord] = {}
    for point in scored_points:
        payload = point.payload if isinstance(point.payload, dict) else {}
        raw_resource_id = payload.get("resource_id")
        if not isinstance(raw_resource_id, int):
            continue

        title = str(payload.get("title") or "").strip() or f"Resource #{raw_resource_id}"
        res_type = str(payload.get("resource_type") or "").strip()
        url = str(payload.get("url") or "").strip() or None
        chunk_text = str(payload.get("chunk_text") or "").strip()
        score = float(point.score or 0.0)

        existing = resources.get(raw_resource_id)
        if existing is None or score > existing.score:
            resources[raw_resource_id] = RetrievedResourceRecord(
                resource_id=raw_resource_id,
                resource_type=res_type,
                title=title,
                url=url,
                chunk_text=chunk_text,
                score=score,
            )

    retrieved = sorted(resources.values(), key=lambda item: item.score, reverse=True)[:top_k]
    if not retrieved:
        raise ValueError("No similar resources were found in Qdrant for the provided digital footprint.")
    logger.info(
        "Retrieved resources from vector DB",
        extra={"search_k": search_k, "top_k": top_k, "result_count": len(retrieved)},
    )
    return retrieved


# ---------------------------------------------------------------------------
# Course retrieval (generic RAGPipeline)
# ---------------------------------------------------------------------------


async def retrieve_courses_for_footprints(
    *,
    digital_footprints: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str,
    settings: AppSettings,
    top_k: int = 5,
    search_k: int = 20,
) -> tuple[list[RetrievedCourse], str]:
    query_text = create_embedding_question_input(digital_footprints)
    async with ApiClient.for_embeddings(settings=settings) as embedding_client:
        query_vector = await fetch_embedding(
            client=embedding_client,
            text=query_text,
            settings=settings,
        )

    async with await QdrantVectorClient.connect(settings=settings) as qdrant_client:
        scored_points = await qdrant_client.search(query_vector=query_vector, k=search_k)

    by_course_id: dict[int, RetrievedCourse] = {}
    for point in scored_points:
        payload = point.payload if isinstance(point.payload, Mapping) else {}
        raw_course_id = payload.get("course_id")
        if not isinstance(raw_course_id, int):
            continue

        name = str(payload.get("course_name") or "").strip()
        description = str(payload.get("course_description") or "").strip()
        score = float(point.score or 0.0)
        existing = by_course_id.get(raw_course_id)
        if existing is None or score > existing.score:
            by_course_id[raw_course_id] = RetrievedCourse(
                course_id=raw_course_id,
                name=name,
                description=description,
                score=score,
            )

    courses = sorted(by_course_id.values(), key=lambda item: item.score, reverse=True)[:top_k]
    logger.info(
        "Retrieved similar courses",
        extra={"search_k": search_k, "top_k": top_k, "result_count": len(courses)},
    )
    return courses, query_text


async def retrieve_similar_courses(
    digital_footprints: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str,
    *,
    settings: AppSettings | None = None,
    top_k: int = 5,
    search_k: int = 20,
) -> tuple[list[RetrievedCourse], str]:
    resolved_settings = settings or get_settings()
    return await retrieve_courses_for_footprints(
        digital_footprints=digital_footprints,
        settings=resolved_settings,
        top_k=top_k,
        search_k=search_k,
    )
