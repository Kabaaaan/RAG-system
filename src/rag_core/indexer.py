from __future__ import annotations

from collections.abc import Sequence

from src.api_client.api_client import ApiClient
from src.config.settings import AppSettings
from src.preprocessing import create_embedding_passage_input, split_text
from src.rag_core.embeddings import fetch_embedding
from src.rag_core.schemas import CourseIndexingStats, CourseLike
from src.utils import get_logger
from src.vector_db import PointData, QdrantVectorClient

logger = get_logger(__name__)


async def index_courses_in_vector_db(
    *,
    courses: Sequence[CourseLike],
    settings: AppSettings,
    recreate_collection: bool = False,
) -> CourseIndexingStats:
    if not courses:
        return CourseIndexingStats(courses_count=0, chunks_count=0, collection_recreated=False)
    logger.info("Indexing courses in vector DB", extra={"courses_count": len(courses)})

    points: list[PointData] = []
    async with ApiClient.for_embeddings(settings=settings) as embedding_client:
        for course in courses:
            chunks = split_text(course.description.strip()) if course.description.strip() else []
            if not chunks:
                chunks = [course.name.strip()]

            for chunk_index, chunk in enumerate(chunks):
                embedding_input = create_embedding_passage_input(course.name, chunk)
                vector = await fetch_embedding(
                    client=embedding_client,
                    text=embedding_input,
                    settings=settings,
                )
                payload = {
                    "resource_id": course.id,
                    "resource_type": "course",
                    "title": course.name,
                    "url": None,
                    "course_id": course.id,
                    "course_name": course.name,
                    "course_description": course.description,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk,
                }
                point_id = course.id * 10_000 + chunk_index
                points.append(PointData(point_id=point_id, vector=vector, payload=payload))

    if not points:
        return CourseIndexingStats(courses_count=len(courses), chunks_count=0, collection_recreated=False)

    async with await QdrantVectorClient.connect(settings=settings) as qdrant_client:
        collection_recreated = await qdrant_client.create_collection(
            vector_size=settings.embedding_vector_size,
            recreate_if_exists=recreate_collection,
        )
        await qdrant_client.add_points(points)

    return CourseIndexingStats(
        courses_count=len(courses),
        chunks_count=len(points),
        collection_recreated=collection_recreated,
    )
