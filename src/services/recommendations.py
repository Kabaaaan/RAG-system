from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.database.models import Recommendation
from src.database.repositories import RecommendationRepository, UserRepository
from src.database.session import session_scope
from src.rag_core import RAGPipeline, RetrievedCourse
from src.services.errors import NotFoundError
from src.utils import get_logger

logger = get_logger(__name__)


@dataclass(slots=True, frozen=True)
class GeneratedRecommendation:
    recommendation: Recommendation
    retrieved_courses: list[RetrievedCourse]
    query_text: str
    debug_file_path: Path


def add_recommendation(
    *,
    login: str,
    text: str,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> Recommendation:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        user_repo = UserRepository(session)
        user = user_repo.get_by_login(login)
        if user is None:
            raise NotFoundError(f"User with login '{login}' not found.")
        rec_repo = RecommendationRepository(session)
        return rec_repo.create(user_id=user.id, text=_fit_recommendation_text(text))


def list_recommendations(
    *, login: str, database_url: str | None = None, echo_sql: bool = False
) -> list[Recommendation]:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        user_repo = UserRepository(session)
        user = user_repo.get_by_login(login)
        if user is None:
            raise NotFoundError(f"User with login '{login}' not found.")
        rec_repo = RecommendationRepository(session)
        return rec_repo.list_for_user(user_id=user.id)


def generate_recommendation(
    *,
    login: str,
    top_k: int = 5,
    search_k: int = 20,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> GeneratedRecommendation:
    logger.info(
        "Generating recommendation",
        extra={"login": login, "top_k": top_k, "search_k": search_k},
    )
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        user_repo = UserRepository(session)
        user = user_repo.get_by_login(login)
        if user is None:
            raise NotFoundError(f"User with login '{login}' not found.")

        digital_footprints = _parse_digital_footprints(user.digital_footprints)
        pipeline = RAGPipeline()
        pipeline_result = asyncio.run(
            pipeline.generate_recommendation(
                digital_footprints=digital_footprints,
                top_k=top_k,
                search_k=search_k,
            )
        )

        rec_repo = RecommendationRepository(session)
        recommendation = rec_repo.create(
            user_id=user.id,
            text=_fit_recommendation_text(pipeline_result.recommendation_text),
        )

    debug_file_path = _write_recommendation_debug_file(
        login=login,
        query_text=pipeline_result.query_text,
        prompt_text=pipeline_result.prompt_text,
        llm_response=pipeline_result.llm_response,
        recommendation_text=pipeline_result.recommendation_text,
        retrieved_courses=pipeline_result.retrieved_courses,
    )

    logger.info(
        "Recommendation generated",
        extra={
            "login": login,
            "recommendation_id": recommendation.id,
            "retrieved_courses": len(pipeline_result.retrieved_courses),
            "debug_file_path": str(debug_file_path),
        },
    )

    return GeneratedRecommendation(
        recommendation=recommendation,
        retrieved_courses=pipeline_result.retrieved_courses,
        query_text=pipeline_result.query_text,
        debug_file_path=debug_file_path,
    )


def _parse_digital_footprints(
    raw_value: str,
) -> Mapping[str, Any] | Sequence[Mapping[str, Any]] | str:
    stripped = raw_value.strip()
    if not stripped:
        return ""
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped

    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, Sequence) and not isinstance(payload, str):
        normalized_events: list[Mapping[str, Any]] = []
        for item in payload:
            if isinstance(item, Mapping):
                normalized_events.append(item)
        return normalized_events
    return stripped


def _fit_recommendation_text(text: str, *, max_length: int = 300) -> str:
    normalized = text.strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _write_recommendation_debug_file(
    *,
    login: str,
    query_text: str,
    prompt_text: str,
    llm_response: Any,
    recommendation_text: str,
    retrieved_courses: Sequence[RetrievedCourse],
) -> Path:
    base_dir = Path("data/recs")
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_login = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in login)
    file_path = base_dir / f"{timestamp}_{safe_login}.json"

    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "login": login,
        "query": query_text,
        "vector_search_results": [
            {
                "course_id": course.course_id,
                "name": course.name,
                "description": course.description,
                "score": course.score,
            }
            for course in retrieved_courses
        ],
        "llm_prompt": prompt_text,
        "llm_response_raw": llm_response,
        "llm_response_text": recommendation_text,
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path
