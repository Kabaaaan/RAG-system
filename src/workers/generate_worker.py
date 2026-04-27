from __future__ import annotations

import asyncio
import json

from src.query_client.nats_client import RAGTasksClient
from src.services import RecommendationGenerationService

nats_client = RAGTasksClient()
recommendation_generation_service = RecommendationGenerationService()


async def generate_handler(msg):
    task_id = "unknown"
    recommendation_type: str | None = None

    try:
        data = json.loads(msg.data.decode("utf-8"))
        task_id = data["task_id"]
        task_type = str(data.get("type") or "")
        payload = data["payload"]

        print(f"[GenerateWorker] Received task {task_id} (type={task_type})")

        if task_type != "generate":
            await msg.ack()
            print(f"[GenerateWorker] Skipped unsupported task {task_id} (type={task_type})")
            return

        lead_id = str(payload["lead_id"])
        raw_type = payload.get("type")
        if raw_type is not None:
            recommendation_type = str(raw_type)

        await recommendation_generation_service.mark_processing(
            task_id=task_id,
            recommendation_type=recommendation_type,
        )
        generated = await recommendation_generation_service.generate(
            task_id=task_id,
            lead_id=lead_id,
            recommendation_type=recommendation_type,
        )
        await recommendation_generation_service.mark_completed(
            task_id=task_id,
            recommendation_type=generated.recommendation_type,
            recommendation_id=generated.recommendation_id,
        )

        await msg.ack()
        print(f"[GenerateWorker] Task {task_id} completed")

    except Exception as exc:
        if task_id != "unknown":
            try:
                await recommendation_generation_service.mark_failed(
                    task_id=task_id,
                    error=str(exc),
                    recommendation_type=recommendation_type,
                )
            except Exception as mark_exc:
                print(f"[GenerateWorker] Failed to mark task {task_id} as failed: {mark_exc}")
        print(f"[GenerateWorker] Error: {exc}")
        await msg.nak()


async def run():
    await nats_client.connect()
    await nats_client.subscribe(
        subject="tasks.rag.generate",
        durable="generate-worker",
        handler=generate_handler,
        max_ack_pending=1,
    )
    await asyncio.Future()
