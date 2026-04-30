"""Unit tests for pure utility helpers in RecommendationGenerationService and RecommendationsQueryService.

Covered helpers:
- RecommendationGenerationService._normalize_recommendation_type
- RecommendationGenerationService._parse_lead_id
- RecommendationsQueryService._deserialize_recommendation_payload
- RecommendationGenerationService._build_mautic_recommendation_candidates
"""

from __future__ import annotations

import pytest

from src.config.settings import AppSettings
from src.services.errors import ValidationError
from src.services.recommendations import RecommendationGenerationService, RecommendationsQueryService

# ---------------------------------------------------------------------------
# Shared AppSettings instance used for tests that require a service instance.
# External URLs are dummies — no real network calls are made in these tests.
# ---------------------------------------------------------------------------

_SETTINGS_500 = AppSettings(
    LLM_API_URL="http://llm.test",
    EMBEDDING_MODEL_API_URL="http://embedding.test",
    MAUTIC_RECOMMENDATION_MAX_LENGTH=500,
)


# ===========================================================================
# RecommendationGenerationService._normalize_recommendation_type
# ===========================================================================


def test_normalize_recommendation_type_known_lowercase_type_returned_unchanged() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type("cold", allow_empty=False)

    assert result == "cold"


def test_normalize_recommendation_type_uppercase_input_is_lowercased() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type("HOT", allow_empty=False)

    assert result == "hot"


def test_normalize_recommendation_type_hyphens_are_converted_to_underscores() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type("after-sale", allow_empty=False)

    assert result == "after_sale"


def test_normalize_recommendation_type_surrounding_whitespace_is_stripped() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type("  warm  ", allow_empty=False)

    assert result == "warm"


def test_normalize_recommendation_type_none_with_allow_empty_true_returns_none() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type(None, allow_empty=True)

    assert result is None


def test_normalize_recommendation_type_none_with_allow_empty_false_returns_empty_string() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type(None, allow_empty=False)

    assert result == ""


def test_normalize_recommendation_type_empty_string_with_allow_empty_true_returns_none() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type("", allow_empty=True)

    assert result is None


def test_normalize_recommendation_type_empty_string_with_allow_empty_false_returns_empty_string() -> None:
    result = RecommendationGenerationService._normalize_recommendation_type("", allow_empty=False)

    assert result == ""


def test_normalize_recommendation_type_unknown_type_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="Unknown recommendation type"):
        RecommendationGenerationService._normalize_recommendation_type("nonexistent_type_xyz", allow_empty=False)


# ===========================================================================
# RecommendationGenerationService._parse_lead_id
# ===========================================================================


def test_parse_lead_id_integer_string_returns_int() -> None:
    result = RecommendationGenerationService._parse_lead_id("12345")

    assert result == 12345
    assert isinstance(result, int)


def test_parse_lead_id_strips_surrounding_whitespace_before_conversion() -> None:
    result = RecommendationGenerationService._parse_lead_id("  188736  ")

    assert result == 188736


def test_parse_lead_id_zero_string_returns_zero() -> None:
    result = RecommendationGenerationService._parse_lead_id("0")

    assert result == 0


def test_parse_lead_id_empty_string_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        RecommendationGenerationService._parse_lead_id("")


def test_parse_lead_id_whitespace_only_string_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        RecommendationGenerationService._parse_lead_id("   ")


def test_parse_lead_id_alphabetic_string_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="integer-compatible"):
        RecommendationGenerationService._parse_lead_id("abc")


def test_parse_lead_id_float_string_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="integer-compatible"):
        RecommendationGenerationService._parse_lead_id("12.5")


# ===========================================================================
# RecommendationsQueryService._deserialize_recommendation_payload
# ===========================================================================


def test_deserialize_recommendation_payload_valid_json_dict_is_returned_as_is() -> None:
    text = '{"key": "value", "score": 0.9}'

    result = RecommendationsQueryService._deserialize_recommendation_payload(text)

    assert result == {"key": "value", "score": 0.9}


def test_deserialize_recommendation_payload_preserves_nested_dict_structure() -> None:
    text = '{"outer": {"inner_key": 42, "flag": true}, "list": [1, 2, 3]}'

    result = RecommendationsQueryService._deserialize_recommendation_payload(text)

    assert result == {"outer": {"inner_key": 42, "flag": True}, "list": [1, 2, 3]}


def test_deserialize_recommendation_payload_json_list_is_wrapped_under_value_key() -> None:
    text = "[1, 2]"

    result = RecommendationsQueryService._deserialize_recommendation_payload(text)

    assert result == {"value": [1, 2]}


def test_deserialize_recommendation_payload_json_number_is_wrapped_under_value_key() -> None:
    text = "42"

    result = RecommendationsQueryService._deserialize_recommendation_payload(text)

    assert result == {"value": 42}


def test_deserialize_recommendation_payload_empty_string_returns_text_key_with_empty_value() -> None:
    result = RecommendationsQueryService._deserialize_recommendation_payload("")

    assert result == {"text": ""}


def test_deserialize_recommendation_payload_whitespace_only_returns_text_key_with_empty_value() -> None:
    result = RecommendationsQueryService._deserialize_recommendation_payload("   ")

    assert result == {"text": ""}


def test_deserialize_recommendation_payload_invalid_json_returns_text_key_with_original_string() -> None:
    raw = "just plain text, not JSON!"

    result = RecommendationsQueryService._deserialize_recommendation_payload(raw)

    assert result == {"text": raw}
