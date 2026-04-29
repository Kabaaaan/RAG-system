from __future__ import annotations

from pathlib import Path

import pytest

from src.preprocessing.embeddings import create_embedding_passage_input, create_embedding_question_input
from src.rag_core.prompt_builder import format_courses_context, render_prompt
from src.rag_core.schemas import RetrievedCourse


def test_create_embedding_passage_input_contains_russian_labels() -> None:
    result = create_embedding_passage_input("Python", "Базовый курс")
    assert "Название: Python" in result
    assert "Описание:" in result


def test_create_embedding_question_input_builds_summary() -> None:
    result = create_embedding_question_input(
        {
            "events": [
                {
                    "event_type": "view",
                    "entity_type": "course",
                    "entity_name": "Python basics",
                    "duration_seconds": 35,
                },
                {"event_type": "search", "entity_name": "data analysis"},
                {"event_type": "favorite", "entity_name": "SQL"},
            ]
        }
    )
    assert result.startswith("query: ")
    assert "Цифровой профиль пользователя" in result
    assert "Python basics" in result
    assert "data analysis" in result
    assert "SQL" in result


def test_format_courses_context_empty() -> None:
    assert format_courses_context([]) == "Похожие курсы не найдены."


def test_render_prompt_requires_placeholders(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("no placeholders", encoding="utf-8")
    with pytest.raises(ValueError):
        render_prompt(prompt_path=path, courses_context="ctx", user_query="query")


def test_format_courses_context_contains_score() -> None:
    courses = [
        RetrievedCourse(course_id=1, name="SQL", description="desc", score=0.81234),
    ]
    rendered = format_courses_context(courses)
    assert "1. SQL" in rendered
    assert "Семантическая релевантность: 0.812" in rendered
