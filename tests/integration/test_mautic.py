from __future__ import annotations

import asyncio

from src.config.settings import AppSettings
from src.mauitc import MauticClient


def _load_test_config() -> tuple[AppSettings, int, str, int]:
    settings = AppSettings()
    lead_id = 293231
    email = "_00thanx@mail.ru.it"
    email_id = 29
    return settings, lead_id, email, email_id


def test_get_contact_activity_live() -> None:
    settings, lead_id, _, _ = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            response = await client.get_contact_activity(lead_id)

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        assert "events" in payload

    asyncio.run(run_test())


def test_find_contacts_by_email_live() -> None:
    settings, _, email, _ = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            response = await client.find_contacts_by_email(email)

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        assert payload

    asyncio.run(run_test())


def test_get_stages_live() -> None:
    settings, _, _, _ = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            stages = await client.get_stages()

        assert isinstance(stages, list)
        assert stages
        assert all(isinstance(stage, dict) for stage in stages)

    asyncio.run(run_test())


def test_get_contact_stage_by_id_live() -> None:
    settings, lead_id, email, _ = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            stage_by_id = await client.get_contact_stage(contact_id=lead_id)
            stage_by_email = await client.get_contact_stage(email=email)

        assert stage_by_id == stage_by_email
        assert stage_by_id is None or isinstance(stage_by_id, dict)

    asyncio.run(run_test())


def test_get_contact_stage_by_email_live() -> None:
    settings, _, email, _ = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            stage = await client.get_contact_stage(email=email)

        assert stage is None or isinstance(stage, dict)

    asyncio.run(run_test())


def test_get_emails_live() -> None:
    settings, _, _, _ = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            emails = await client.get_emails()

        assert isinstance(emails, list)
        assert emails
        assert all(isinstance(email_payload, dict) for email_payload in emails)

    asyncio.run(run_test())


def test_get_email_by_id_live() -> None:
    settings, _, _, email_id = _load_test_config()

    async def run_test() -> None:
        async with MauticClient(settings=settings) as client:
            email_payload = await client.get_emails(email_id=email_id)

        assert isinstance(email_payload, dict)
        assert str(email_payload["id"]) == str(email_id)
        assert "clean_text" in email_payload

    asyncio.run(run_test())
