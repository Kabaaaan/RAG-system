from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from src.config.settings import get_settings
from src.query_client.nats_client import RAGTasksClient
from src.services import RecommendationGenerationService
from src.services.errors import TaskStateNotFoundError, ValidationError
from src.utils import configure_logging, get_logger

RETRY_DELAY_SECONDS = 60
GENERATE_ACK_WAIT_SECONDS = 30 * 60
GENERATE_MAX_DELIVER = 5

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

nats_client = RAGTasksClient(settings=settings)
recommendation_generation_service = RecommendationGenerationService(settings=settings)


@dataclass(slots=True, frozen=True)
class GenerateTaskMessage:
    task_id: str
    lead_id: str
    recommendation_type: str | None


class PermanentMessageError(ValueError):
    """Raised when a NATS message is malformed and must not be retried."""


def _parse_message(raw: str) -> GenerateTaskMessage:
    cleaned = raw.strip()
    if not cleaned:
        raise PermanentMessageError("empty message")

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise PermanentMessageError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise PermanentMessageError("message root must be a JSON object")

    task_id = str(data.get("task_id") or "").strip()
    if not task_id:
        raise PermanentMessageError("missing task_id")

    task_type = str(data.get("type") or "").strip()
    if task_type != "generate":
        raise PermanentMessageError(f"unsupported task type '{task_type}'")

    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise PermanentMessageError(f"invalid payload for task '{task_id}'")

    lead_id = str(payload.get("lead_id") or "").strip()
    if not lead_id:
        raise PermanentMessageError(f"missing lead_id for task '{task_id}'")

    raw_type = payload.get("type")
    recommendation_type = str(raw_type).strip() if raw_type is not None else None
    if recommendation_type == "":
        recommendation_type = None

    return GenerateTaskMessage(
        task_id=task_id,
        lead_id=lead_id,
        recommendation_type=recommendation_type,
    )


async def _mark_failed_best_effort(task: GenerateTaskMessage, error: BaseException) -> None:
    try:
        await recommendation_generation_service.mark_failed(
            task_id=task.task_id,
            error=str(error),
            recommendation_type=task.recommendation_type,
        )
    except ValidationError:
        if task.recommendation_type is None:
            logger.exception("Could not mark generate task as failed", extra={"task_id": task.task_id})
            return
        try:
            await recommendation_generation_service.mark_failed(
                task_id=task.task_id,
                error=str(error),
                recommendation_type=None,
            )
        except TaskStateNotFoundError:
            logger.warning(
                "Could not mark generate task as failed because its Redis state is missing",
                extra={"task_id": task.task_id},
            )
        except Exception:
            logger.exception("Could not mark generate task as failed", extra={"task_id": task.task_id})
    except TaskStateNotFoundError:
        logger.warning(
            "Could not mark generate task as failed because its Redis state is missing",
            extra={"task_id": task.task_id},
        )
    except Exception:
        logger.exception("Could not mark generate task as failed", extra={"task_id": task.task_id})


async def generate_handler(msg: Any) -> None:
    raw = msg.data.decode("utf-8", errors="replace")
    task: GenerateTaskMessage | None = None

    try:
        task = _parse_message(raw)
    except PermanentMessageError as exc:
        logger.warning("Dropping malformed generate message: %s", exc)
        await msg.ack()
        return

    logger.info(
        "Received generate task",
        extra={
            "task_id": task.task_id,
            "lead_id": task.lead_id,
            "recommendation_type": task.recommendation_type,
        },
    )

    try:
        await recommendation_generation_service.mark_processing(
            task_id=task.task_id,
            recommendation_type=task.recommendation_type,
        )
    except TaskStateNotFoundError:
        logger.warning(
            "Dropping stale generate task because its Redis state is missing",
            extra={"task_id": task.task_id, "lead_id": task.lead_id},
        )
        await msg.ack()
        return
    except ValidationError as exc:
        logger.warning("Dropping invalid generate task: %s", exc, extra={"task_id": task.task_id})
        await _mark_failed_best_effort(task, exc)
        await msg.ack()
        return

    try:
        generated = await recommendation_generation_service.generate(
            task_id=task.task_id,
            lead_id=task.lead_id,
            recommendation_type=task.recommendation_type,
        )
        await recommendation_generation_service.mark_completed(
            task_id=task.task_id,
            recommendation_type=generated.recommendation_type,
            recommendation_id=generated.recommendation_id,
        )
    except TaskStateNotFoundError:
        logger.warning(
            "Generated task lost Redis state during processing; acknowledging to prevent duplicate side effects",
            extra={"task_id": task.task_id, "lead_id": task.lead_id},
        )
        await msg.ack()
        return
    except ValidationError as exc:
        logger.warning("Dropping invalid generate task: %s", exc, extra={"task_id": task.task_id})
        await _mark_failed_best_effort(task, exc)
        await msg.ack()
        return
    except Exception as exc:
        logger.exception("Generate task failed; scheduling retry", extra={"task_id": task.task_id})
        await _mark_failed_best_effort(task, exc)
        await msg.nak(delay=RETRY_DELAY_SECONDS)
        return

    await msg.ack()
    logger.info(
        "Generate task completed",
        extra={
            "task_id": task.task_id,
            "lead_id": task.lead_id,
            "recommendation_id": generated.recommendation_id,
        },
    )


async def run() -> None:
    await nats_client.connect()
    await nats_client.subscribe(
        subject="tasks.rag.generate",
        durable="generate-worker",
        handler=generate_handler,
        max_ack_pending=1,
        ack_wait=GENERATE_ACK_WAIT_SECONDS,
        max_deliver=GENERATE_MAX_DELIVER,
    )
    await asyncio.Future()
