"""Unit tests for src.rag_core.parser.parse_recommendation_payload."""

from __future__ import annotations

import pytest

from src.rag_core.parser import parse_recommendation_payload

# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_parse_recommendation_payload_returns_clean_json_dict() -> None:
    raw = '{"course_id": 42, "score": 0.95}'
    result = parse_recommendation_payload(raw)
    assert result == {"course_id": 42, "score": 0.95}


def test_parse_recommendation_payload_extracts_json_surrounded_by_prose() -> None:
    raw = 'Here is the recommendation:\n{"course_id": 7, "reason": "good match"}\nEnd of response.'
    result = parse_recommendation_payload(raw)
    assert result == {"course_id": 7, "reason": "good match"}


def test_parse_recommendation_payload_preserves_nested_dict() -> None:
    raw = '{"top": {"inner_key": "inner_value", "score": 0.5}, "flag": true}'
    result = parse_recommendation_payload(raw)
    assert result == {"top": {"inner_key": "inner_value", "score": 0.5}, "flag": True}


def test_parse_recommendation_payload_strips_surrounding_whitespace() -> None:
    raw = '   \n  {"id": 1}  \n  '
    result = parse_recommendation_payload(raw)
    assert result == {"id": 1}


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


def test_parse_recommendation_payload_raises_on_empty_string() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_recommendation_payload("")


def test_parse_recommendation_payload_raises_on_whitespace_only() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_recommendation_payload("   \t\n  ")


def test_parse_recommendation_payload_raises_when_json_is_a_list_not_dict() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_recommendation_payload("[1, 2, 3]")


def test_parse_recommendation_payload_raises_on_malformed_text_without_braces() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        parse_recommendation_payload("This is just plain text with no braces at all.")
