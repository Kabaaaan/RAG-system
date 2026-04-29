from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

from src.services.errors import TaskStateNotFoundError, ValidationError
from src.workers import generate_worker


class DummyMessage:
    def __init__(self, payload: object) -> None:
        if isinstance(payload, bytes):
            self.data = payload
        elif isinstance(payload, str):
            self.data = payload.encode("utf-8")
        else:
            self.data = json.dumps(payload).encode("utf-8")
        self.ack = AsyncMock()
        self.nak = AsyncMock()


class GeneratedStub:
    recommendation_type = "hot"
    recommendation_id = 123


def test_generate_handler_acks_stale_task_without_retry(monkeypatch) -> None:
    service = AsyncMock()
    service.mark_processing.side_effect = TaskStateNotFoundError("missing")
    monkeypatch.setattr(generate_worker, "recommendation_generation_service", service)

    msg = DummyMessage(
        {
            "task_id": "task-1",
            "type": "generate",
            "payload": {"lead_id": "188736", "type": "hot"},
        }
    )

    asyncio.run(generate_worker.generate_handler(msg))

    service.mark_processing.assert_awaited_once_with(task_id="task-1", recommendation_type="hot")
    service.generate.assert_not_awaited()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


def test_generate_handler_retries_transient_generation_error(monkeypatch) -> None:
    service = AsyncMock()
    service.generate.side_effect = RuntimeError("llm timeout")
    monkeypatch.setattr(generate_worker, "recommendation_generation_service", service)

    msg = DummyMessage(
        {
            "task_id": "task-2",
            "type": "generate",
            "payload": {"lead_id": "188736", "type": "hot"},
        }
    )

    asyncio.run(generate_worker.generate_handler(msg))

    service.mark_processing.assert_awaited_once_with(task_id="task-2", recommendation_type="hot")
    service.mark_failed.assert_awaited_once()
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once_with(delay=generate_worker.RETRY_DELAY_SECONDS)


def test_generate_handler_acks_invalid_json(monkeypatch) -> None:
    service = AsyncMock()
    monkeypatch.setattr(generate_worker, "recommendation_generation_service", service)

    msg = DummyMessage("{bad json")

    asyncio.run(generate_worker.generate_handler(msg))

    service.mark_processing.assert_not_awaited()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


def test_generate_handler_acks_validation_error_after_marking_failed(monkeypatch) -> None:
    service = AsyncMock()
    service.mark_processing.side_effect = ValidationError("unknown recommendation type")
    monkeypatch.setattr(generate_worker, "recommendation_generation_service", service)

    msg = DummyMessage(
        {
            "task_id": "task-3",
            "type": "generate",
            "payload": {"lead_id": "188736", "type": "bad-type"},
        }
    )

    asyncio.run(generate_worker.generate_handler(msg))

    service.mark_processing.assert_awaited_once_with(task_id="task-3", recommendation_type="bad-type")
    service.mark_failed.assert_awaited_once()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


def test_generate_handler_retries_mark_failed_without_invalid_type(monkeypatch) -> None:
    service = AsyncMock()
    service.mark_processing.side_effect = ValidationError("unknown recommendation type")
    service.mark_failed.side_effect = [ValidationError("unknown recommendation type"), None]
    monkeypatch.setattr(generate_worker, "recommendation_generation_service", service)

    msg = DummyMessage(
        {
            "task_id": "task-5",
            "type": "generate",
            "payload": {"lead_id": "188736", "type": "bad-type"},
        }
    )

    asyncio.run(generate_worker.generate_handler(msg))

    assert service.mark_failed.await_count == 2
    assert service.mark_failed.await_args_list[0].kwargs["recommendation_type"] == "bad-type"
    assert service.mark_failed.await_args_list[1].kwargs["recommendation_type"] is None
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


def test_generate_handler_completes_valid_task(monkeypatch) -> None:
    service = AsyncMock()
    service.generate.return_value = GeneratedStub()
    monkeypatch.setattr(generate_worker, "recommendation_generation_service", service)

    msg = DummyMessage(
        {
            "task_id": "task-4",
            "type": "generate",
            "payload": {"lead_id": "188736", "type": "hot"},
        }
    )

    asyncio.run(generate_worker.generate_handler(msg))

    service.mark_processing.assert_awaited_once_with(task_id="task-4", recommendation_type="hot")
    service.generate.assert_awaited_once_with(task_id="task-4", lead_id="188736", recommendation_type="hot")
    service.mark_completed.assert_awaited_once_with(task_id="task-4", recommendation_type="hot", recommendation_id=123)
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()
