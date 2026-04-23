from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from src.config.settings import AppSettings, get_settings
from src.query_client import RAGTasksClient
from src.task_storage import RedisClient

INDEX_TASK_TTL_SECONDS = 24 * 60 * 60


class ResourceIndexingService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()

    async def enqueue(self, *, resource_id: int) -> str:
        task_id = str(uuid.uuid4())
        record = self._build_record(task_id=task_id, resource_id=resource_id, status="queued")

        async with RedisClient(settings=self._settings) as redis_client:
            await redis_client.set_record(
                self._build_key(resource_id),
                record,
                ttl=INDEX_TASK_TTL_SECONDS,
            )

        nats_client = RAGTasksClient(settings=self._settings)
        try:
            await nats_client.connect()
            await nats_client.publish_index(resource_id=resource_id, task_id=task_id)
        except Exception as exc:
            await self.mark_failed(resource_id=resource_id, error=str(exc))
            raise
        finally:
            await nats_client.close()

        return task_id

    async def get_status(self, *, resource_id: int) -> dict[str, Any] | None:
        async with RedisClient(settings=self._settings) as redis_client:
            return await redis_client.get_record(self._build_key(resource_id))

    async def mark_processing(self, *, resource_id: int) -> None:
        await self._update_record(
            resource_id=resource_id,
            status="processing",
            error=None,
        )

    async def mark_completed(self, *, resource_id: int) -> None:
        await self._update_record(
            resource_id=resource_id,
            status="completed",
            error=None,
        )

    async def mark_failed(self, *, resource_id: int, error: str | None = None) -> None:
        await self._update_record(
            resource_id=resource_id,
            status="failed",
            error=error,
        )

    @staticmethod
    def _build_key(resource_id: int) -> str:
        return f"idx:{resource_id}"

    def _build_record(self, *, task_id: str, resource_id: int, status: str) -> dict[str, Any]:
        timestamp = self._timestamp()
        return {
            "task_id": task_id,
            "resource_id": resource_id,
            "type": "index",
            "status": status,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    async def _update_record(
        self,
        *,
        resource_id: int,
        status: str,
        error: str | None,
    ) -> None:
        async with RedisClient(settings=self._settings) as redis_client:
            key = self._build_key(resource_id)
            record = await redis_client.get_record(key)
            if record is None:
                record = self._build_record(task_id=str(uuid.uuid4()), resource_id=resource_id, status=status)
                if error is not None:
                    record["error"] = error
                await redis_client.set_record(key, record, ttl=INDEX_TASK_TTL_SECONDS)
                return

            record["status"] = status
            record["updated_at"] = self._timestamp()
            if error is None:
                record.pop("error", None)
            else:
                record["error"] = error

            await redis_client.set_record(key, record, ttl=INDEX_TASK_TTL_SECONDS)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")
