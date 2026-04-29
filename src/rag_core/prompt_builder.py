from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from src.rag_core.schemas import RetrievedCourse


def render_prompt(*, prompt_path: Path, courses_context: str, user_query: str) -> str:
    template = prompt_path.read_text(encoding="utf-8")
    if "{courses_context}" not in template or "{user_query}" not in template:
        raise ValueError("Prompt template must contain '{courses_context}' and '{user_query}' placeholders.")
    return template.format(courses_context=courses_context, user_query=user_query)


def format_courses_context(courses: Sequence[RetrievedCourse]) -> str:
    if not courses:
        return "Похожие курсы не найдены."

    lines: list[str] = []
    for index, course in enumerate(courses, start=1):
        short_description = course.description.strip().replace("\n", " ")
        if len(short_description) > 300:
            short_description = short_description[:297] + "..."
        lines.append(f"{index}. {course.name}\nОписание: {short_description}\nСемантическая релевантность: {course.score:.3f}")
    return "\n\n".join(lines)
