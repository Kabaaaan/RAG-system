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

    async def aclose(self) -> None:
        await self._client.close()

    async def __aenter__(self) -> "RedisClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()
