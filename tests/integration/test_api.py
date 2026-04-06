from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import create_app


def _build_client() -> TestClient:
    return TestClient(create_app())


def test_healthcheck() -> None:
    with _build_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
