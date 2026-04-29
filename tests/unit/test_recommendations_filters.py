from __future__ import annotations

from qdrant_client.http.models.models import FieldCondition, MatchValue

from src.services.recommendations import RecommendationGenerationService


def test_resource_type_for_cold_recommendations_is_article() -> None:
    assert RecommendationGenerationService._resource_type_for_recommendation("cold") == "article"


def test_resource_type_for_hot_recommendations_is_course() -> None:
    assert RecommendationGenerationService._resource_type_for_recommendation("hot") == "course"


def test_resource_type_for_other_recommendations_is_unrestricted() -> None:
    assert RecommendationGenerationService._resource_type_for_recommendation("warm") is None
    assert RecommendationGenerationService._resource_type_for_recommendation("after_sale") is None


def test_build_resource_type_filter_matches_qdrant_payload_field() -> None:
    query_filter = RecommendationGenerationService._build_resource_type_filter("article")

    assert query_filter is not None
    assert len(query_filter.must or []) == 1
    condition = query_filter.must[0]
    assert isinstance(condition, FieldCondition)
    assert condition.key == "resource_type"
    assert isinstance(condition.match, MatchValue)
    assert condition.match.value == "article"


def test_build_resource_type_filter_returns_none_without_resource_type() -> None:
    assert RecommendationGenerationService._build_resource_type_filter(None) is None
