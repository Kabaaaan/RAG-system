import json
from typing import Any, cast

from redis import asyncio as redis

from src.config.settings import AppSettings, get_settings


class RedisClient:
    def __init__(self, *, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = redis.Redis(
            host=self._settings.redis_host,
            port=self._settings.redis_port,
            db=self._settings.redis_db,
            decode_responses=True,
        )

    async def set_record(self, key: str, payload: dict[str, Any], ttl: int) -> bool:
        result = await self._client.set(name=key, value=json.dumps(payload), ex=ttl)
        return cast(bool, result)

    async def get_record(self, key: str) -> dict[str, Any] | None:
        data = await self._client.get(key)
        if data is None:
            return None
        if not isinstance(data, str | bytes | bytearray):
            raise TypeError("Redis returned a non-JSON-compatible payload type.")
        return cast(dict[str, Any], json.loads(data))

    async def update_field(self, key: str, field: str, value: Any) -> bool:
        record = await self.get_record(key)
        if record is None:
            return False

        record[field] = value
        ttl = cast(int, await self._client.ttl(key))
        serialized_record = json.dumps(record)

        if ttl > 0:
            result = await self._client.set(name=key, value=serialized_record, ex=ttl)
            return cast(bool, result)

        result = await self._client.set(name=key, value=serialized_record)
        return cast(bool, result)

    async def get_count(self, prefix: str) -> int:
        count = 0
        cursor = 0

        pattern = f"{prefix}*"

        while True:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)
            count += len(keys)

            if cursor == 0:
                break

        return count

    async def get_active_idx_count(self) -> int:
        count = 0
        cursor = 0
        pattern = "idx:*"

        while True:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)

            if keys:
                values = await self._client.mget(keys)

                for value in values:
                    if value is None:
                        continue

                    try:
                        record = json.loads(value)
                    except json.JSONDecodeError:
                        continue

                    status = record.get("status")
                    if status in {"queued", "processing"}:
                        count += 1

            if cursor == 0:
                break

        return count

    async def list_generate_tasks(self, *, lead_id: str) -> list[dict[str, Any]]:
        normalized_lead_id = lead_id.strip()
        cursor = 0
        tasks: list[dict[str, Any]] = []
        pattern = "gen:*"

        while True:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)

            if keys:
                values = await self._client.mget(keys)
                for key, value in zip(keys, values, strict=False):
                    if value is None:
                        continue

                    try:
                        record = json.loads(value)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(record, dict):
                        continue

                    record_lead_id = str(record.get("lead_id", "")).strip()
                    if record_lead_id != normalized_lead_id:
                        continue

                    tasks.append(
                        {
                            "id": str(record.get("task_id") or key.replace("gen:", "", 1)),
                            "status": str(record.get("status") or "queued"),
                            "type": str(record.get("type") or "generate"),
                            "created_at": str(record.get("created_at") or ""),
                            "updated_at": str(record.get("updated_at") or ""),
                        }
                    )

            if cursor == 0:
                break

        tasks.sort(key=lambda item: item["created_at"], reverse=True)
        return tasks

    async def get_generate_task(self, *, task_id: str) -> dict[str, Any] | None:
        return await self.get_record(f"gen:{task_id}")

    async def aclose(self) -> None:
        await self._client.close()

    async def __aenter__(self) -> "RedisClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()
