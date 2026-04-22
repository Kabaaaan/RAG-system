from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

import src.api.routers.mautic as mautic_router_module
import src.api.routers.prompt as prompt_router_module
import src.api.routers.recommendations as recommendations_router_module
import src.api.routers.staging_area as staging_area_router_module
from src.api.auth import create_api_key
from src.api.main import create_app
from src.config.settings import get_settings
from src.services import (
    ImportedEmailResult,
    LeadActionsRecord,
    LeadRecommendationsRecord,
    NamedCatalogRecord,
    RecommendationItemRecord,
    StagingAreaResourceRecord,
)
from src.services.errors import AlreadyExistsError


def _build_client() -> TestClient:
    return TestClient(create_app())


def _auth_headers() -> dict[str, str]:
    settings = get_settings()
    api_key = create_api_key(secret=settings.api_auth_secret_value, settings=settings)
    return {"Authorization": f"Bearer {api_key}"}


def test_list_resource_types_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        staging_area_router_module.catalog_service,
        "list_resource_types",
        lambda: [
            NamedCatalogRecord(id=1, name="article"),
            NamedCatalogRecord(id=2, name="mautic_email"),
        ],
    )

    with _build_client() as client:
        response = client.get("/staging-area/resorces/type", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "resource_types": [
            {"id": 1, "name": "article"},
            {"id": 2, "name": "mautic_email"},
        ]
    }


def test_create_resource_type_returns_conflict(monkeypatch) -> None:
    def _raise_conflict(*, name: str) -> NamedCatalogRecord:
        raise AlreadyExistsError(f"Resource type '{name}' already exists.")

    monkeypatch.setattr(
        staging_area_router_module.catalog_service,
        "create_resource_type",
        _raise_conflict,
    )

    with _build_client() as client:
        response = client.post(
            "/staging-area/resorces/type",
            json={"name": "article"},
            headers=_auth_headers(),
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Resource type 'article' already exists."


def test_get_staging_resource_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        staging_area_router_module.staging_area_service,
        "get_resource",
        lambda *, resource_id: StagingAreaResourceRecord(
            resource_id=resource_id,
            resource_type="mautic_email",
            data={"title": "Welcome", "url": None, "text": "Hello world"},
        ),
    )

    with _build_client() as client:
        response = client.get("/staging-area/42", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "resource_id": 42,
        "resource_type": "mautic_email",
        "data": {"title": "Welcome", "url": None, "text": "Hello world"},
    }


def test_index_staging_resource_endpoint(monkeypatch) -> None:
    def _fake_create_resource(
        *,
        resource_type: str,
        text: str,
        url: str | None = None,
        title: str | None = None,
    ) -> StagingAreaResourceRecord:
        assert resource_type == "article"
        assert text == "Body text"
        assert url == "https://example.com/post"
        assert title == "Post title"
        return StagingAreaResourceRecord(
            resource_id=73,
            resource_type=resource_type,
            data={"title": title, "url": url, "text": text},
        )

    monkeypatch.setattr(
        staging_area_router_module.staging_area_service,
        "create_resource",
        _fake_create_resource,
    )

    with _build_client() as client:
        response = client.post(
            "/staging-area",
            json={
                "resource_type": "article",
                "text": "Body text",
                "url": "https://example.com/post",
                "title": "Post title",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 202
    assert response.json() == {"resource_id": 73, "status": "queued"}


def test_index_staging_resource_endpoint_returns_conflict_for_duplicate(monkeypatch) -> None:
    def _raise_duplicate(
        *,
        resource_type: str,
        text: str,
        url: str | None = None,
        title: str | None = None,
    ) -> StagingAreaResourceRecord:
        assert resource_type == "article"
        assert text == "Body text"
        assert url == "https://example.com/post"
        assert title == "Post title"
        raise AlreadyExistsError("Resource with identical text already exists.")

    monkeypatch.setattr(
        staging_area_router_module.staging_area_service,
        "create_resource",
        _raise_duplicate,
    )

    with _build_client() as client:
        response = client.post(
            "/staging-area",
            json={
                "resource_type": "article",
                "text": "Body text",
                "url": "https://example.com/post",
                "title": "Post title",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Resource with identical text already exists."}


def test_import_mautic_email_alias_endpoint(monkeypatch) -> None:
    async def _fake_import(*, email_id: int | None = None) -> ImportedEmailResult:
        assert email_id == 15
        return ImportedEmailResult(status="created")

    monkeypatch.setattr(
        staging_area_router_module.staging_area_service,
        "import_emails",
        _fake_import,
    )

    with _build_client() as client:
        response = client.post(
            "/staging-area/email",
            json={"id": 15},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json() == {"status": "created", "count": None}


def test_get_recommendations_by_path_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        recommendations_router_module.recommendations_query_service,
        "get_recommendations",
        lambda *, lead_id: LeadRecommendationsRecord(
            lead_id=lead_id,
            recommendations=[
                RecommendationItemRecord(
                    id="101",
                    type="awareness",
                    data={"text": "Read article"},
                )
            ],
        ),
    )

    with _build_client() as client:
        response = client.get("/recommendations/77", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "lead_id": "77",
        "recommendations": [
            {
                "id": "101",
                "type": "awareness",
                "data": {"text": "Read article"},
            }
        ],
    }


def test_get_lead_actions_endpoint(monkeypatch) -> None:
    async def _fake_get_actions(*, lead_id: str) -> LeadActionsRecord:
        assert lead_id == "77"
        return LeadActionsRecord(
            lead_id=lead_id,
            actions=[
                RecommendationItemRecord(
                    id="evt-1",
                    type="email_opened",
                    data={"summary": "Email opened: Welcome"},
                )
            ],
        )

    monkeypatch.setattr(
        recommendations_router_module.recommendations_query_service,
        "get_actions",
        _fake_get_actions,
    )

    with _build_client() as client:
        response = client.get("/recommendations/actions/77", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "lead_id": "77",
        "actions": [
            {
                "id": "evt-1",
                "type": "email_opened",
                "data": {"summary": "Email opened: Welcome"},
            }
        ],
    }


def test_get_prompt_endpoint(monkeypatch) -> None:
    with TemporaryDirectory() as tmp_dir:
        prompt_dir = Path(tmp_dir)
        (prompt_dir / "warm.txt").write_text("Warm prompt text", encoding="utf-8")
        monkeypatch.setattr(prompt_router_module, "PROMPTS_DIR", prompt_dir)

        with _build_client() as client:
            response = client.get(
                "/prompt",
                params={"lead_type": "warm"},
                headers=_auth_headers(),
            )

    assert response.status_code == 200
    assert response.json() == {"lead_type": "warm", "prompt": "Warm prompt text"}


def test_update_prompt_endpoint(monkeypatch) -> None:
    with TemporaryDirectory() as tmp_dir:
        prompt_dir = Path(tmp_dir)
        target_file = prompt_dir / "hot.txt"
        target_file.write_text("Old prompt", encoding="utf-8")
        monkeypatch.setattr(prompt_router_module, "PROMPTS_DIR", prompt_dir)

        with _build_client() as client:
            response = client.put(
                "/prompt",
                json={"lead_type": "hot", "prompt": "Updated prompt"},
                headers=_auth_headers(),
            )

        stored_prompt = target_file.read_text(encoding="utf-8")

    assert response.status_code == 200
    assert response.json() == {"lead_type": "hot", "prompt": "Updated prompt"}
    assert stored_prompt == "Updated prompt"


def test_create_mautic_contact_field_endpoint(monkeypatch) -> None:
    class _FakeResponse:
        def json(self) -> dict[str, object]:
            return {
                "field": {
                    "id": 13,
                    "label": "Lead Score",
                    "alias": "lead_score",
                    "type": "text",
                    "object": "lead",
                }
            }

    class _FakeMauticClient:
        async def __aenter__(self) -> _FakeMauticClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def create_contact_field(self, *, json=None, data=None, headers=None, timeout=None):
            assert json == {
                "label": "Lead Score",
                "alias": "lead_score",
                "type": "text",
                "object": "lead",
            }
            return _FakeResponse()

    monkeypatch.setattr(mautic_router_module, "MauticClient", _FakeMauticClient)

    with _build_client() as client:
        response = client.post(
            "/mautic/field",
            json={"name": "Lead Score"},
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 13,
        "name": "Lead Score",
        "alias": "lead_score",
        "type": "text",
        "object": "lead",
    }


def test_update_mautic_contact_field_endpoint(monkeypatch) -> None:
    class _FakeMauticClient:
        async def __aenter__(self) -> _FakeMauticClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def update_contact(self, contact_id, *, json=None, data=None, headers=None, timeout=None):
            assert contact_id == "293231"
            assert json == {"lead_score": "42"}
            return None

    monkeypatch.setattr(mautic_router_module, "MauticClient", _FakeMauticClient)

    with _build_client() as client:
        response = client.patch(
            "/mautic/field",
            json={"lead_id": "293231", "field": "lead_score", "value": "42"},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json() == {
        "lead_id": "293231",
        "field": "lead_score",
        "value": "42",
        "status": "updated",
    }
