"""Unit tests for the pure helper extract_llm_text in src.rag_core.llm."""

from __future__ import annotations

import pytest

from src.rag_core.llm import extract_llm_text

# ---------------------------------------------------------------------------
# OpenAI-compatible formats
# ---------------------------------------------------------------------------


def test_extract_llm_text_openai_chat_completion_message_content() -> None:
    payload = {"choices": [{"message": {"content": "Hello"}}]}
    assert extract_llm_text(payload) == "Hello"


def test_extract_llm_text_openai_completion_text_field() -> None:
    payload = {"choices": [{"text": "Hello"}]}
    assert extract_llm_text(payload) == "Hello"


# ---------------------------------------------------------------------------
# Ollama format
# ---------------------------------------------------------------------------


def test_extract_llm_text_ollama_response_strips_surrounding_whitespace() -> None:
    payload = {"response": "  Hello world  "}
    assert extract_llm_text(payload) == "Hello world"


# ---------------------------------------------------------------------------
# HuggingFace formats
# ---------------------------------------------------------------------------


def test_extract_llm_text_huggingface_top_level_generated_text() -> None:
    payload = {"generated_text": "result"}
    assert extract_llm_text(payload) == "result"


def test_extract_llm_text_huggingface_list_of_dicts_generated_text() -> None:
    payload = [{"generated_text": "result"}]
    assert extract_llm_text(payload) == "result"


# ---------------------------------------------------------------------------
# Unsupported / error paths
# ---------------------------------------------------------------------------


def test_extract_llm_text_raises_value_error_for_empty_dict() -> None:
    with pytest.raises(ValueError):
        extract_llm_text({})


def test_extract_llm_text_raises_value_error_for_integer_payload() -> None:
    with pytest.raises(ValueError):
        extract_llm_text(42)


# ---------------------------------------------------------------------------
# Whitespace stripping
# ---------------------------------------------------------------------------


def test_extract_llm_text_strips_whitespace_from_openai_message_content() -> None:
    payload = {"choices": [{"message": {"content": "   trimmed   "}}]}
    assert extract_llm_text(payload) == "trimmed"
