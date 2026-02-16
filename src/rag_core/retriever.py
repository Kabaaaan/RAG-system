from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.api_client.api_client import ApiClient
from src.config.settings import AppSettings, get_settings
from src.preprocessing import create_embedding_question_input
from src.rag_core.embeddings import fetch_embedding
from src.rag_core.schemas import RetrievedCourse
from src.utils import get_logger
from src.vector_db import QdrantVectorClient

logger = get_logger(__name__)


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
