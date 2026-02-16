from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click


def _load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise click.ClickException(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in {path}: {exc}") from exc


def load_courses(path: Path) -> list[dict[str, Any]]:
    payload = _load_json_file(path)
    if isinstance(payload, list):
        return [course for course in payload if isinstance(course, dict)]
    if isinstance(payload, dict):
        courses = payload.get("courses")
        if isinstance(courses, list):
            return [course for course in courses if isinstance(course, dict)]
    raise click.ClickException("Courses JSON must be a list or an object with a 'courses' list.")


def load_users(path: Path) -> list[dict[str, Any]]:
    payload = _load_json_file(path)
    if not isinstance(payload, list):
        raise click.ClickException("Users JSON must be a list.")
    return [item for item in payload if isinstance(item, dict)]
