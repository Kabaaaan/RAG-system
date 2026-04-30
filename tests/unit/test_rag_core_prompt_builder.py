"""Unit tests for pure helpers in src.rag_core.prompt_builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rag_core.prompt_builder import PROMPTS_DIR, format_available_content, render_typed_prompt
from src.rag_core.schemas import RetrievedResourceRecord

# ---------------------------------------------------------------------------
# Helper factory – avoids repeating keyword arguments in every test
# ---------------------------------------------------------------------------


def _make_resource(
    *,
    resource_id: int = 1,
    resource_type: str = "article",
    title: str = "Sample Article",
    url: str | None = "https://example.com/article",
    chunk_text: str = "A short fragment.",
    score: float = 0.875,
) -> RetrievedResourceRecord:
    return RetrievedResourceRecord(
        resource_id=resource_id,
        resource_type=resource_type,
        title=title,
        url=url,
        chunk_text=chunk_text,
        score=score,
    )


# ---------------------------------------------------------------------------
# format_available_content
# ---------------------------------------------------------------------------


def test_format_available_content_empty_list_returns_empty_string() -> None:
    assert format_available_content([]) == ""


def test_format_available_content_none_url_renders_as_na() -> None:
    resource = _make_resource(url=None)
    result = format_available_content([resource])
    assert "n/a" in result


def test_format_available_content_single_resource_contains_title_type_fragment_and_score() -> None:
    resource = _make_resource(title="My Article", resource_type="article", score=0.92345)
    result = format_available_content([resource])

    assert "My Article" in result
    assert "Type: article" in result
    assert "Fragment:" in result
    # score formatted to exactly three decimal places (0.92345 → 0.923)
    assert "Relevance: 0.923" in result


def test_format_available_content_chunk_text_longer_than_500_chars_is_truncated_with_ellipsis() -> None:
    long_text = "w" * 600
    resource = _make_resource(chunk_text=long_text)
    result = format_available_content([resource])

    # The raw 600-char string must not appear verbatim
    assert long_text not in result
    # Truncation marker must be present
    assert "..." in result


def test_format_available_content_two_resources_are_numbered_from_one() -> None:
    r1 = _make_resource(resource_id=1, title="First Resource")
    r2 = _make_resource(resource_id=2, title="Second Resource")
    result = format_available_content([r1, r2])

    assert "1. First Resource" in result
    assert "2. Second Resource" in result


# ---------------------------------------------------------------------------
# render_typed_prompt
# ---------------------------------------------------------------------------


def test_render_typed_prompt_substitutes_both_placeholders(tmp_path: Path) -> None:
    template = "Content: {available_content}\nTraces: {digital_traces}"
    (tmp_path / "cold.txt").write_text(template, encoding="utf-8")

    result = render_typed_prompt(
        recommendation_type="cold",
        available_content="article data",
        digital_traces="user footprint",
        prompts_dir=tmp_path,
    )

    assert result == "Content: article data\nTraces: user footprint"


def test_render_typed_prompt_raises_value_error_for_nonexistent_recommendation_type(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render_typed_prompt(
            recommendation_type="nonexistent_type",
            available_content="content",
            digital_traces="traces",
            prompts_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# PROMPTS_DIR constant
# ---------------------------------------------------------------------------


def test_prompts_dir_constant_points_to_existing_directory_containing_cold_txt() -> None:
    assert PROMPTS_DIR.is_dir(), f"Expected PROMPTS_DIR to be an existing directory, got: {PROMPTS_DIR}"
    assert (PROMPTS_DIR / "cold.txt").is_file(), "Expected cold.txt to exist inside PROMPTS_DIR"
