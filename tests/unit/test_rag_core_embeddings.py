"""Unit tests for pure helpers in src.rag_core.embeddings."""

from __future__ import annotations

import pytest

from src.rag_core.embeddings import extract_embedding, mean_pool, normalize_vector_size

# ---------------------------------------------------------------------------
# extract_embedding – format dispatch
# ---------------------------------------------------------------------------


def test_extract_embedding_supports_openai_format() -> None:
    payload = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
    result = extract_embedding(payload)
    assert result == pytest.approx([0.1, 0.2, 0.3])


def test_extract_embedding_supports_ollama_format() -> None:
    payload = {"embedding": [0.1, 0.2, 0.3]}
    result = extract_embedding(payload)
    assert result == pytest.approx([0.1, 0.2, 0.3])


def test_extract_embedding_supports_embeddings_key_format() -> None:
    payload = {"embeddings": [[0.1, 0.2, 0.3]]}
    result = extract_embedding(payload)
    assert result == pytest.approx([0.1, 0.2, 0.3])


def test_extract_embedding_supports_direct_float_list() -> None:
    result = extract_embedding([0.1, 0.2, 0.3])
    assert result == pytest.approx([0.1, 0.2, 0.3])


def test_extract_embedding_raises_on_unsupported_format() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        extract_embedding({"foo": "bar"})


# ---------------------------------------------------------------------------
# mean_pool
# ---------------------------------------------------------------------------


def test_mean_pool_averages_two_vectors_element_wise() -> None:
    vectors = [[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]]
    result = mean_pool(vectors)
    assert result == pytest.approx([2.0, 3.0, 4.0])


def test_mean_pool_returns_empty_list_for_empty_input() -> None:
    assert mean_pool([]) == []


# ---------------------------------------------------------------------------
# normalize_vector_size
# ---------------------------------------------------------------------------


def test_normalize_vector_size_pads_shorter_vector_with_zeros() -> None:
    result = normalize_vector_size([0.1, 0.2], vector_size=5)
    assert result == pytest.approx([0.1, 0.2, 0.0, 0.0, 0.0])
    assert len(result) == 5


def test_normalize_vector_size_truncates_longer_vector() -> None:
    result = normalize_vector_size([0.1, 0.2, 0.3, 0.4, 0.5], vector_size=3)
    assert result == pytest.approx([0.1, 0.2, 0.3])
    assert len(result) == 3


def test_normalize_vector_size_returns_copy_for_exact_size_without_mutating_original() -> None:
    original = [0.1, 0.2, 0.3]
    result = normalize_vector_size(original, vector_size=3)
    assert result == pytest.approx(original)
    # Must be a fresh list, not the same object
    assert result is not original
    # Mutating the result must not affect the original
    result[0] = 999.0
    assert original[0] == pytest.approx(0.1)
