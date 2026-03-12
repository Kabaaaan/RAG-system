from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.api_client.api_client import ApiClient
from src.config.settings import AppSettings


async def fetch_embedding(
    *,
    client: ApiClient,
    text: str,
    settings: AppSettings,
) -> list[float]:
    payload: dict[str, Any] = {"input": text}
    if settings.embedding_model.strip():
        payload["model"] = settings.embedding_model.strip()
    response = await client.post("", json=payload)
    response_payload = response.json()
    vector = extract_embedding(response_payload)
    if not vector:
        raise ValueError("Embedding API returned an empty vector.")
    return normalize_vector_size(vector, settings.embedding_vector_size)


def extract_embedding(payload: Any) -> list[float]:
    if isinstance(payload, Mapping):
        data = payload.get("data")
        if isinstance(data, Sequence) and data:
            first = data[0]
            if isinstance(first, Mapping):
                candidate = first.get("embedding")
                if isinstance(candidate, Sequence):
                    return [float(value) for value in candidate if isinstance(value, int | float)]
        embedding = payload.get("embedding")
        if isinstance(embedding, Sequence):
            return [float(value) for value in embedding if isinstance(value, int | float)]

    if isinstance(payload, Sequence) and not isinstance(payload, str):
        if payload and all(isinstance(item, int | float) for item in payload):
            return [float(value) for value in payload]
        token_vectors = [
            [float(value) for value in token if isinstance(value, int | float)]
            for token in payload
            if isinstance(token, Sequence) and not isinstance(token, str)
        ]
        if token_vectors:
            return mean_pool(token_vectors)

    raise ValueError("Unsupported embedding response format.")


def mean_pool(token_vectors: Sequence[Sequence[float]]) -> list[float]:
    if not token_vectors:
        return []
    vector_size = len(token_vectors[0])
    sums = [0.0] * vector_size
    for token in token_vectors:
        for index, value in enumerate(token):
            sums[index] += value
    denominator = float(len(token_vectors))
    return [value / denominator for value in sums]


def normalize_vector_size(vector: Sequence[float], vector_size: int) -> list[float]:
    if len(vector) == vector_size:
        return list(vector)
    if len(vector) > vector_size:
        return list(vector[:vector_size])
    padded = list(vector)
    padded.extend([0.0] * (vector_size - len(vector)))
    return padded
