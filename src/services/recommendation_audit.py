from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.utils import get_logger

logger = get_logger(__name__)


class RecommendationAuditLog:
    def __init__(
        self,
        *,
        task_id: str,
        lead_id: int,
        recommendation_type: str | None,
        base_dir: str,
        task_created_at: str | None = None,
    ) -> None:
        self._started_monotonic = time.perf_counter()
        self._task_created_at = task_created_at
        self._payload: dict[str, Any] = {
            "task_id": task_id,
            "lead_id": str(lead_id),
            "recommendation_type": recommendation_type,
            "task_created_at": task_created_at,
            "trace_started_at": self._timestamp(),
            "steps": [],
        }

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safe_task_id = self._safe_part(task_id)
        safe_lead_id = self._safe_part(str(lead_id))
        self.path = Path(base_dir) / f"{timestamp}_{safe_lead_id}_{safe_task_id}.json"

    def step(self, name: str, **data: Any) -> None:
        entry = {
            "name": name,
            "at": self._timestamp(),
            "elapsed_seconds": round(time.perf_counter() - self._started_monotonic, 3),
            "data": data,
        }
        duration_from_api = self._seconds_since_task_created()
        if duration_from_api is not None:
            entry["duration_from_api_request_seconds"] = duration_from_api
        self._payload["steps"].append(entry)
        self._write()

    def finish(self, *, status: str, **data: Any) -> None:
        task_to_finish_seconds = self._seconds_since_task_created()
        self._payload["finished_at"] = self._timestamp()
        self._payload["status"] = status
        self._payload["duration_seconds"] = round(time.perf_counter() - self._started_monotonic, 3)
        if task_to_finish_seconds is not None:
            self._payload["duration_from_api_request_seconds"] = task_to_finish_seconds
        if data:
            self._payload["result"] = data
        self._write()

    def _seconds_since_task_created(self) -> float | None:
        if not self._task_created_at:
            return None
        try:
            created_at = datetime.fromisoformat(self._task_created_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        return round((datetime.now(UTC) - created_at).total_seconds(), 3)

    def _write(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Could not write recommendation audit log", extra={"path": str(self.path)})

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _safe_part(value: str) -> str:
        safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
        return safe[:80] or "unknown"
