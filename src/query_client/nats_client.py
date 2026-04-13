import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, RetentionPolicy, StreamConfig

from src.config.settings import AppSettings, get_settings


class RAGTasksClient:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self.servers = f"nats://{self._settings.nats_host}:{self._settings.nats_port}"
        self.nc: NATS | None = None
        self.js: JetStreamContext | None = None
        self.stream_name = self._settings.nats_stream_name

    async def connect(self) -> None:
        if self.nc and self.nc.is_connected:
            return

        self.nc = NATS()
        await self.nc.connect(servers=self.servers, allow_reconnect=True)
        self.js = self.nc.jetstream()
        await self._ensure_stream()

    async def _ensure_stream(self) -> None:
        if self.js is None:
            raise RuntimeError("JetStream context is not initialized")

        try:
            await self.js.stream_info(self.stream_name)
        except Exception:
            await self.js.add_stream(
                config=StreamConfig(
                    name=self.stream_name,
                    subjects=[
                        "tasks.rag.generate",
                        "tasks.rag.index",
                        "tasks.rag.rebuild",
                    ],
                    retention=RetentionPolicy.WORK_QUEUE,
                    max_age=0,
                    max_msgs=-1,
                    max_bytes=-1,
                )
            )

    async def close(self) -> None:
        if self.nc:
            await self.nc.close()

    async def publish_task(self, task_type: str, payload: dict[str, Any]) -> str:
        if self.js is None:
            await self.connect()
        if self.js is None:
            raise RuntimeError("JetStream context is not initialized")

        task_id = str(uuid.uuid4())
        subject = f"tasks.rag.{task_type}"
        message = {
            "task_id": task_id,
            "type": task_type,
            "payload": payload,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        await self.js.publish(subject, json.dumps(message).encode("utf-8"))
        return task_id

    async def publish_generate(self, lead_id: str, rec_type: str) -> str:
        return await self.publish_task("generate", {"lead_id": lead_id, "type": rec_type})

    async def publish_index(self, resource_id: int) -> str:
        return await self.publish_task("index", {"resource_id": resource_id})

    async def publish_rebuild(self) -> str:
        return await self.publish_task("rebuild", {})

    async def subscribe(
        self,
        subject: str,
        durable: str,
        handler: Callable[[Msg], Awaitable[None]],
        max_ack_pending: int = 1,
    ) -> None:
        if self.js is None:
            await self.connect()
        if self.js is None:
            raise RuntimeError("JetStream context is not initialized")

        await self.js.subscribe(
            subject=subject,
            durable=durable,
            cb=handler,
            config=ConsumerConfig(max_ack_pending=max_ack_pending),
            manual_ack=True,
        )


nats_client = RAGTasksClient()
