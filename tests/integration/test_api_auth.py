from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.config.settings import get_settings


def _build_client() -> TestClient:
    return TestClient(create_app())


def test_auth_key_endpoint_returns_jwt() -> None:
    settings = get_settings()

    with _build_client() as client:
        response = client.post("/auth/key", json={"secret": settings.api_auth_secret_value})

    assert response.status_code == 200
    assert isinstance(response.json()["api-key"], str)
    assert response.json()["api-key"]


def test_protected_endpoint_requires_authentication() -> None:
    with _build_client() as client:
        response = client.get("/recommendations/status", params={"token": "token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key."
