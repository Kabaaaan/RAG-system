import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, RetentionPolicy, StreamConfig

from src.config.settings import AppSettings, get_settings

logger = logging.getLogger(__name__)


class RAGTasksClient:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self.servers = [f"nats://{self._settings.nats_host}:{self._settings.nats_port}"]
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

    async def _reset_consumer_on_startup(self, durable: str) -> None:
        """Delete the durable consumer (if it exists) so it is recreated with
        the correct configuration on the next subscribe() call.

        Root cause this addresses: a consumer created in a previous run may have
        stale settings (e.g. default ack_wait of 30 s instead of the intended
        30 min, or unlimited max_deliver).  NATS does not automatically apply the
        ConsumerConfig passed to js.subscribe() when the consumer already exists —
        it simply binds to the existing one.  Deleting it here forces recreation
        with the correct parameters.

        With WorkQueue retention, any unacked messages are returned to the stream
        and redelivered to the new consumer, so no messages are lost.
        """
        if self.js is None:
            return
        try:
            await self.js.delete_consumer(self.stream_name, durable)
            logger.info(
                "Stale NATS consumer '%s' deleted; it will be recreated with correct ack_wait / max_deliver settings on subscribe.",
                durable,
            )
        except Exception:
            # Consumer does not exist yet, or a transient network error — both are fine.
            pass

    async def close(self) -> None:
        if self.nc:
            await self.nc.close()

    async def publish_task(
        self,
        task_type: str,
        payload: dict[str, Any],
        *,
        task_id: str | None = None,
    ) -> str:
        if self.js is None:
            await self.connect()
        if self.js is None:
            raise RuntimeError("JetStream context is not initialized")

        resolved_task_id = task_id or str(uuid.uuid4())
        subject = f"tasks.rag.{task_type}"
        message = {
            "task_id": resolved_task_id,
            "type": task_type,
            "payload": payload,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        await self.js.publish(subject, json.dumps(message).encode("utf-8"))
        return resolved_task_id

    async def publish_generate(self, lead_id: str, rec_type: str | None = None, *, task_id: str | None = None) -> str:
        payload: dict[str, Any] = {"lead_id": lead_id}
        if rec_type is not None and rec_type.strip():
            payload["type"] = rec_type.strip()
        return await self.publish_task("generate", payload, task_id=task_id)

    async def publish_index(self, resource_id: int, *, task_id: str | None = None) -> str:
        return await self.publish_task("index", {"resource_id": resource_id}, task_id=task_id)

    async def publish_rebuild(self, *, task_id: str | None = None) -> str:
        return await self.publish_task("rebuild", {}, task_id=task_id)

    async def subscribe(
        self,
        subject: str,
        durable: str,
        handler: Callable[[Msg], Awaitable[None]],
        max_ack_pending: int = 1,
        ack_wait: float | None = None,
        max_deliver: int | None = None,
        backoff: list[float] | None = None,
    ) -> None:
        if self.js is None:
            await self.connect()
        if self.js is None:
            raise RuntimeError("JetStream context is not initialized")

        # Ensure the consumer is created fresh with the correct config.
        # (A consumer that survived from a previous run keeps its original
        # settings; deleting it here forces recreation with our parameters.)
        await self._reset_consumer_on_startup(durable)

        await self.js.subscribe(
            subject=subject,
            durable=durable,
            cb=handler,
            config=ConsumerConfig(
                max_ack_pending=max_ack_pending,
                ack_wait=ack_wait,
                max_deliver=max_deliver,
                backoff=backoff,
            ),
            manual_ack=True,
        )


nats_client = RAGTasksClient()
