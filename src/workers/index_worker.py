from __future__ import annotations

import asyncio
import contextlib
import json
import uuid

from src.api_client import ApiClient
from src.config.settings import get_settings
from src.preprocessing import create_embedding_passage_input, split_text
from src.query_client.nats_client import RAGTasksClient
from src.rag_core.embeddings import fetch_embedding
from src.services import ResourceIndexingService, StagingAreaService
from src.utils import configure_logging, get_logger
from src.vector_db import PointData, QdrantVectorClient

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

# How long the NATS server waits for an ack before redelivering.
# Must be greater than the worst-case time for a full indexing run
# (text splitting + embedding API + Qdrant upsert).
INDEX_ACK_WAIT_SECONDS = 30 * 60  # 30 minutes

# Maximum number of redelivery attempts before the message is abandoned.
INDEX_MAX_DELIVER = 5

# Interval at which we notify NATS that we are still processing.
# Must be well below INDEX_ACK_WAIT_SECONDS to prevent spurious redelivery.
INDEX_HEARTBEAT_INTERVAL_SECONDS = 5 * 60  # 5 minutes

RETRY_DELAY_SECONDS = 60

# ------------------------------------------------------------------
# Module-level singletons
# ------------------------------------------------------------------

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

nats_client = RAGTasksClient()
staging_area_service = StagingAreaService()
resource_indexing_service = ResourceIndexingService()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


async def _send_in_progress_heartbeat(msg, interval: float) -> None:
    """Periodically send an in-progress signal to reset the ack_wait timer."""
    while True:
        await asyncio.sleep(interval)
        try:
            await msg.in_progress()
        except Exception:
            logger.debug("Failed to send in_progress heartbeat; stopping heartbeat loop")
            return


# ------------------------------------------------------------------
# Message handler
# ------------------------------------------------------------------


async def index_handler(msg) -> None:
    task_id = "unknown"
    resource_id: int | None = None

    try:
        data = json.loads(msg.data.decode("utf-8"))
        task_id = str(data.get("task_id") or "").strip()
        task_type = str(data.get("type") or "").strip()
        payload = data.get("payload")

        logger.info(
            "Received index task",
            extra={"task_id": task_id, "task_type": task_type},
        )

        if task_type != "index":
            await msg.ack()
            logger.info(
                "Skipped unsupported task type",
                extra={"task_id": task_id, "task_type": task_type},
            )
            return

        if not isinstance(payload, dict):
            raise ValueError(f"Invalid payload for task '{task_id}': expected dict, got {type(payload).__name__}")

        resource_id = int(payload["resource_id"])
        await resource_indexing_service.mark_processing(resource_id=resource_id)

        resource = staging_area_service.get_resource(resource_id=resource_id)
        resource_text = str(resource.data.get("text") or "").strip()
        if not resource_text:
            raise ValueError(f"Resource '{resource_id}' does not contain text for indexing.")

        chunks = split_text(resource_text)
        if not chunks:
            chunks = [resource_text]

        title = str(resource.data.get("title") or "").strip() or f"{resource.resource_type} #{resource.resource_id}"
        points: list[PointData] = []

        heartbeat_task = asyncio.create_task(_send_in_progress_heartbeat(msg, INDEX_HEARTBEAT_INTERVAL_SECONDS))
        try:
            async with ApiClient.for_embeddings(settings=settings) as embedding_client:
                for chunk_index, chunk in enumerate(chunks):
                    vector = await fetch_embedding(
                        client=embedding_client,
                        text=create_embedding_passage_input(title, chunk),
                        settings=settings,
                    )
                    points.append(
                        PointData(
                            point_id=str(uuid.uuid4()),
                            vector=vector,
                            payload={
                                "resource_id": resource.resource_id,
                                "resource_type": resource.resource_type,
                                "title": resource.data.get("title"),
                                "url": resource.data.get("url"),
                                "chunk_index": chunk_index,
                                "chunk_text": chunk,
                            },
                        )
                    )

            async with await QdrantVectorClient.connect(settings=settings) as qdrant_client:
                await qdrant_client.create_collection(vector_size=settings.embedding_vector_size)
                await qdrant_client.add_points(points)

        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        await resource_indexing_service.mark_completed(resource_id=resource_id)
        await msg.ack()
        logger.info(
            "Index task completed",
            extra={"task_id": task_id, "resource_id": resource_id, "chunks": len(chunks)},
        )

    except Exception:
        logger.exception("Index task failed", extra={"task_id": task_id, "resource_id": resource_id})
        if resource_id is not None:
            await resource_indexing_service.mark_failed(
                resource_id=resource_id,
                error=f"Unhandled exception in index_handler (task_id={task_id})",
            )
        await msg.nak(delay=RETRY_DELAY_SECONDS)


# ------------------------------------------------------------------
# Worker entry point
# ------------------------------------------------------------------


async def run() -> None:
    await nats_client.connect()
    await nats_client.subscribe(
        subject="tasks.rag.index",
        durable="index-worker",
        handler=index_handler,
        max_ack_pending=1,
        ack_wait=INDEX_ACK_WAIT_SECONDS,
        max_deliver=INDEX_MAX_DELIVER,
    )
    await asyncio.Future()
