from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.services import AlreadyExistsError, NotFoundError


def _build_client() -> TestClient:
    return TestClient(create_app())


def test_healthcheck() -> None:
    with _build_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_user_returns_201(monkeypatch) -> None:
    call_args: dict[str, object] = {}

    def fake_create_user(*, login: str, digital_footprints: str, database_url: str | None, echo_sql: bool):
        call_args.update(
            {
                "login": login,
                "digital_footprints": digital_footprints,
                "database_url": database_url,
                "echo_sql": echo_sql,
            }
        )
        return SimpleNamespace(id=7, login=login, updated_at=datetime(2026, 2, 16, tzinfo=UTC))

    monkeypatch.setattr("src.api.routers.users.create_user", fake_create_user)

    with _build_client() as client:
        response = client.post(
            "/users",
            params={"database_url": "sqlite:///tmp.db", "echo_sql": "true"},
            json={"login": "roman", "digital_footprints": '{"events":[]}'},
        )

    assert response.status_code == 201
    assert response.json()["id"] == 7
    assert call_args == {
        "login": "roman",
        "digital_footprints": '{"events":[]}',
        "database_url": "sqlite:///tmp.db",
        "echo_sql": True,
    }


def test_create_user_conflict_returns_409(monkeypatch) -> None:
    def fake_create_user(**_: object):
        raise AlreadyExistsError("User with login 'roman' already exists.")

    monkeypatch.setattr("src.api.routers.users.create_user", fake_create_user)

    with _build_client() as client:
        response = client.post("/users", json={"login": "roman", "digital_footprints": ""})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_init_db_endpoint_runs_services_in_order(monkeypatch) -> None:
    call_order: list[str] = []

    def fake_init_db(*, database_url: str | None, echo_sql: bool, drop_existing: bool) -> None:
        assert database_url is None
        assert echo_sql is False
        assert drop_existing is True
        call_order.append("init_db")

    def fake_load_courses(path: Path):
        assert path.as_posix().endswith("data/courses.json")
        call_order.append("load_courses")
        return [{"name": "Python", "description": "Basics"}]

    def fake_seed_courses(courses, *, database_url: str | None, echo_sql: bool) -> int:
        assert courses == [{"name": "Python", "description": "Basics"}]
        call_order.append("seed_courses")
        return 1

    def fake_list_and_vectorize_courses(
        *, database_url: str | None, echo_sql: bool, recreate_collection: bool
    ):
        assert recreate_collection is True
        call_order.append("list_and_vectorize_courses")
        return SimpleNamespace(courses_count=1, chunks_count=2, collection_recreated=True)

    monkeypatch.setattr("src.api.routers.db.init_db", fake_init_db)
    monkeypatch.setattr("src.api.routers.db.load_courses", fake_load_courses)
    monkeypatch.setattr("src.api.routers.db.seed_courses", fake_seed_courses)
    monkeypatch.setattr(
        "src.api.routers.db.list_and_vectorize_courses",
        fake_list_and_vectorize_courses,
    )

    with _build_client() as client:
        response = client.post("/db/init", json={"drop_existing": True})

    assert response.status_code == 200
    assert response.json() == {
        "courses_seeded": 1,
        "courses_count": 1,
        "chunks_count": 2,
        "collection_recreated": True,
    }
    assert call_order == ["init_db", "load_courses", "seed_courses", "list_and_vectorize_courses"]


def test_generate_recommendation_response(monkeypatch) -> None:
    def fake_generate_recommendation(
        *, login: str, top_k: int, search_k: int, database_url: str | None, echo_sql: bool
    ):
        assert login == "alex_dev"
        assert top_k == 3
        assert search_k == 10
        assert database_url is None
        assert echo_sql is False
        return SimpleNamespace(
            recommendation=SimpleNamespace(
                id=11,
                text="Start with Python fundamentals",
                created_at=datetime(2026, 2, 16, tzinfo=UTC),
            ),
            debug_file_path=Path("data/recs/debug.json"),
            query_text="query text",
            retrieved_courses=[
                SimpleNamespace(
                    course_id=1,
                    name="Python fundamentals",
                    description="intro",
                    score=0.98,
                )
            ],
        )

    monkeypatch.setattr(
        "src.api.routers.recommendations.generate_recommendation", fake_generate_recommendation
    )

    with _build_client() as client:
        response = client.post(
            "/recommendations/generate",
            json={"login": "alex_dev", "top_k": 3, "search_k": 10},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["recommendation"]["id"] == 11
    assert Path(payload["debug_file_path"]).as_posix() == "data/recs/debug.json"
    assert payload["retrieved_courses"][0]["course_id"] == 1


def test_list_recommendations_not_found_returns_404(monkeypatch) -> None:
    def fake_list_recommendations(*, login: str, database_url: str | None, echo_sql: bool):
        raise NotFoundError(f"User with login '{login}' not found.")

    monkeypatch.setattr("src.api.routers.recommendations.list_recommendations", fake_list_recommendations)

    with _build_client() as client:
        response = client.get("/recommendations/missing_user")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
