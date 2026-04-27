import json
from uuid import uuid4

import pytest

from src.task_storage import RedisClient


@pytest.mark.asyncio
async def test_set_and_get_record():
    client = RedisClient()
    key = f"test:redis:record:{uuid4().hex}"
    payload = {"name": "test_item", "value": 42, "active": True}
    ttl = 60

    success = await client.set_record(key, payload, ttl)
    assert success is True

    retrieved = await client.get_record(key)
    assert retrieved == payload

    print(f"set_record + get_record работает! key={key}")

    await client._client.delete(key)
    await client.aclose()


@pytest.mark.asyncio
async def test_update_field_preserves_ttl():
    client = RedisClient()
    key = f"test:redis:update_ttl:{uuid4().hex}"
    payload = {"name": "original", "count": 1}
    ttl = 30

    await client.set_record(key, payload, ttl)

    success = await client.update_field(key, "count", 999)
    assert success is True

    updated = await client.get_record(key)
    assert updated["count"] == 999

    remaining_ttl = await client._client.ttl(key)
    assert remaining_ttl > 0, "TTL должен быть сохранён после update_field"

    print(f"update_field с TTL работает! remaining_ttl ≈ {remaining_ttl}s")

    await client._client.delete(key)
    await client.aclose()


@pytest.mark.asyncio
async def test_update_field_no_ttl_and_non_existing():
    client = RedisClient()
    key = f"test:redis:no_ttl:{uuid4().hex}"

    # Создаём ключ БЕЗ срока жизни (чтобы проверить else-ветку)
    await client._client.set(key, json.dumps({"name": "no_ttl_original"}))

    success = await client.update_field(key, "count", 5)
    assert success is True

    updated = await client.get_record(key)
    assert updated["count"] == 5

    ttl = await client._client.ttl(key)
    assert ttl == -1, "У ключа не должно быть TTL после обновления"

    # Проверка несуществующего ключа
    non_key = f"test:redis:nonexist:{uuid4().hex}"
    success_non = await client.update_field(non_key, "field", "value")
    assert success_non is False

    retrieved_non = await client.get_record(non_key)
    assert retrieved_non is None

    print("update_field без TTL и на несуществующем ключе работает корректно")

    await client._client.delete(key)
    await client.aclose()
