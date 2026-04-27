from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, Mock

from nats.js.api import ConsumerConfig

from src.query_client.nats_client import RAGTasksClient


def test_connect_creates_stream_once(monkeypatch) -> None:
    js = AsyncMock()
    js.stream_info.side_effect = Exception("missing stream")

    nc = Mock()
    nc.is_connected = False
    nc.connect = AsyncMock()
    nc.jetstream.return_value = js

    client = RAGTasksClient()

    def fake_nats() -> AsyncMock:
        return nc

    monkeypatch.setattr("src.query_client.nats_client.NATS", fake_nats)

    asyncio.run(client.connect())
    nc.is_connected = True
    asyncio.run(client.connect())

    nc.connect.assert_awaited_once_with(servers=["nats://localhost:4222"], allow_reconnect=True)
    js.stream_info.assert_awaited_once_with("RAG_TASKS")
    js.add_stream.assert_awaited_once()
    stream_config = js.add_stream.await_args.kwargs["config"]
    assert sorted(stream_config.subjects) == [
        "tasks.rag.generate",
        "tasks.rag.index",
        "tasks.rag.rebuild",
    ]


def test_publish_index_uses_index_subject() -> None:
    js = AsyncMock()
    client = RAGTasksClient()
    client.js = js

    task_id = asyncio.run(client.publish_index(resource_id=42))

    js.publish.assert_awaited_once()
    subject, payload_bytes = js.publish.await_args.args
    assert subject == "tasks.rag.index"
    payload = json.loads(payload_bytes.decode("utf-8"))
    assert payload["task_id"] == task_id
    assert payload["type"] == "index"
    assert payload["payload"] == {"resource_id": 42}
    assert payload["created_at"].endswith("Z")


def test_subscribe_passes_expected_arguments() -> None:
    js = AsyncMock()
    client = RAGTasksClient()
    client.js = js

    async def handler(msg) -> None:
        return None

    asyncio.run(
        client.subscribe(
            subject="tasks.rag.generate",
            durable="generate-worker",
            handler=handler,
            max_ack_pending=3,
        )
    )

    js.subscribe.assert_awaited_once_with(
        subject="tasks.rag.generate",
        durable="generate-worker",
        cb=handler,
        config=ConsumerConfig(max_ack_pending=3),
        manual_ack=True,
    )
