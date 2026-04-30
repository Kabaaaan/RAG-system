"""Unit tests for the pure helper functions in src.rag_core.retriever."""

from __future__ import annotations

from typing import cast

from qdrant_client.http.models.models import FieldCondition, MatchValue

from src.rag_core.retriever import build_resource_type_filter, resource_type_for_recommendation

# ---------------------------------------------------------------------------
# resource_type_for_recommendation – mapping look-ups
# ---------------------------------------------------------------------------


def test_resource_type_for_recommendation_cold_returns_article() -> None:
    assert resource_type_for_recommendation("cold") == "article"


def test_resource_type_for_recommendation_hot_returns_course() -> None:
    assert resource_type_for_recommendation("hot") == "course"


def test_resource_type_for_recommendation_warm_returns_none() -> None:
    assert resource_type_for_recommendation("warm") is None


def test_resource_type_for_recommendation_after_sale_returns_none() -> None:
    assert resource_type_for_recommendation("after_sale") is None


def test_resource_type_for_recommendation_completely_unknown_key_returns_none() -> None:
    assert resource_type_for_recommendation("unknown_xyz") is None


# ---------------------------------------------------------------------------
# build_resource_type_filter – Filter construction
# ---------------------------------------------------------------------------


def test_build_resource_type_filter_article_returns_non_null_filter_with_one_condition() -> None:
    result = build_resource_type_filter("article")

    assert result is not None
    assert result.must is not None

    # Qdrant types Filter.must as a complex union; cast to list for assertion.
    conditions = cast(list[FieldCondition], result.must)
    assert len(conditions) == 1

    condition = conditions[0]
    assert isinstance(condition, FieldCondition)
    assert condition.key == "resource_type"
    assert isinstance(condition.match, MatchValue)
    assert condition.match.value == "article"


def test_build_resource_type_filter_course_returns_filter_matching_course_value() -> None:
    result = build_resource_type_filter("course")

    assert result is not None
    assert result.must is not None

    conditions = cast(list[FieldCondition], result.must)
    assert len(conditions) == 1

    condition = conditions[0]
    assert isinstance(condition, FieldCondition)
    assert condition.key == "resource_type"
    assert isinstance(condition.match, MatchValue)
    assert condition.match.value == "course"


def test_build_resource_type_filter_none_resource_type_returns_none() -> None:
    assert build_resource_type_filter(None) is None
