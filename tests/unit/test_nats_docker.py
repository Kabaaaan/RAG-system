from __future__ import annotations

import asyncio
import json

import pytest

from src.query_client.nats_client import RAGTasksClient


@pytest.mark.asyncio
async def test_publish_creates_message_in_stream():
    client = RAGTasksClient()
    await client.connect()

    resource_id = 123456789
    task_id = await client.publish_index(resource_id=resource_id)

    # Проверяем состояние стрима
    stream_info = await client.js.stream_info("RAG_TASKS")

    assert stream_info.state.messages >= 1, "В стриме должно быть хотя бы одно сообщение"
    assert stream_info.state.last_seq > 0

    print(f"Сообщение успешно опубликовано! task_id = {task_id}")
    print(f"   Стрим RAG_TASKS: {stream_info.state.messages} сообщений")


@pytest.mark.asyncio
async def test_publish_and_consume_message():
    client = RAGTasksClient()
    await client.connect()

    await client.js.purge_stream("RAG_TASKS")

    received = asyncio.Queue()

    async def test_handler(msg):
        """Обработчик, который будет вызван, когда сообщение придёт"""
        payload = json.loads(msg.data.decode("utf-8"))
        await received.put(payload)
        await msg.ack()

    await client.subscribe(
        subject="tasks.rag.index",
        durable="integration-test-consumer",
        handler=test_handler,
        max_ack_pending=1,
    )

    resource_id = 987654321
    task_id = await client.publish_index(resource_id=resource_id)

    payload = await asyncio.wait_for(received.get(), timeout=5.0)

    assert payload["task_id"] == task_id
    assert payload["type"] == "index"
    assert payload["payload"]["resource_id"] == resource_id
    assert payload["created_at"].endswith("Z")

    try:
        await client.js.delete_consumer("RAG_TASKS", "integration-test-consumer")
        print("   Тестовый consumer удалён")
    except Exception:
        pass

    print("Сообщение успешно прочитано consumer'ом!")
    print(f"   task_id = {task_id}, resource_id = {resource_id}")
