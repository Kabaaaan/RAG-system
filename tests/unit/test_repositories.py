from __future__ import annotations

import json
from pathlib import Path

import click
import pytest

from src.cli.loaders import load_courses, load_users


def test_load_courses_accepts_list_payload(tmp_path: Path) -> None:
    path = tmp_path / "courses.json"
    path.write_text(json.dumps([{"name": "A", "description": "B"}]), encoding="utf-8")
    result = load_courses(path)
    assert result == [{"name": "A", "description": "B"}]


def test_load_courses_accepts_wrapped_payload(tmp_path: Path) -> None:
    path = tmp_path / "courses.json"
    path.write_text(json.dumps({"courses": [{"name": "A"}]}), encoding="utf-8")
    result = load_courses(path)
    assert result == [{"name": "A"}]


def test_load_users_requires_list(tmp_path: Path) -> None:
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"users": []}), encoding="utf-8")
    with pytest.raises(click.ClickException):
        load_users(path)
