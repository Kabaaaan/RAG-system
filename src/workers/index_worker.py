import asyncio
import json
import uuid

from src.api_client import ApiClient
from src.config.settings import get_settings
from src.preprocessing import create_embedding_passage_input, split_text
from src.query_client.nats_client import RAGTasksClient
from src.rag_core.embeddings import fetch_embedding
from src.services import ResourceIndexingService, StagingAreaService
from src.vector_db import PointData, QdrantVectorClient

nats_client = RAGTasksClient()
staging_area_service = StagingAreaService()
resource_indexing_service = ResourceIndexingService()
settings = get_settings()


async def index_handler(msg):
    task_id = "unknown"
    resource_id: int | None = None

    try:
        data = json.loads(msg.data.decode("utf-8"))
        task_id = data["task_id"]
        task_type = str(data.get("type") or "")
        payload = data["payload"]

        print(f"[IndexWorker] Received task {task_id} (type={task_type})")

        if task_type != "index":
            await msg.ack()
            print(f"[IndexWorker] Skipped unsupported task {task_id} (type={task_type})")
            return

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

        await resource_indexing_service.mark_completed(resource_id=resource_id)
        await msg.ack()
        print(f"[IndexWorker] Task {task_id} completed")

    except Exception as e:
        if resource_id is not None:
            await resource_indexing_service.mark_failed(resource_id=resource_id, error=str(e))
        print(f"[IndexWorker] Error: {e}")
        await msg.nak()


async def run():
    await nats_client.connect()
    await nats_client.subscribe(subject="tasks.rag.index", durable="index-worker", handler=index_handler, max_ack_pending=1)
    await asyncio.Future()
