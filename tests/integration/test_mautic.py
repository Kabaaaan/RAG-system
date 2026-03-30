from __future__ import annotations

import asyncio

from src.config.settings import AppSettings
from src.mauitc import MauticClient


def _load_test_config() -> tuple[AppSettings, int, str]:
    settings = AppSettings()
    lead_id = 293231
    email = "_00thanx@mail.ru.it"
    return settings, lead_id, email


def test_get_contact_activity_live() -> None:
    settings, lead_id, _ = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            response = await client.get_contact_activity(lead_id)

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        assert "events" in payload

    asyncio.run(run_test())


def test_find_contacts_by_email_live() -> None:
    settings, _, email = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            response = await client.find_contacts_by_email(email)

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        assert payload

    asyncio.run(run_test())
