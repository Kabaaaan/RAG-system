from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from src.api_client.api_client import ApiClient
from src.config.settings import AppSettings


async def generate_llm_response(*, settings: AppSettings, prompt: str) -> tuple[str, Any]:
    async with ApiClient.for_llm(settings=settings) as llm_client:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "stream": False,
        }
        if settings.llm_model.strip():
            payload["model"] = settings.llm_model.strip()
        response = await llm_client.post("", json=payload)
        response_payload = response.json()
    return extract_llm_text(response_payload), response_payload


def extract_llm_text(payload: Any) -> str:
    if isinstance(payload, Mapping):
        choices = payload.get("choices")
        if isinstance(choices, Sequence) and choices:
            first = choices[0]
            if isinstance(first, Mapping):
                message = first.get("message")
                if isinstance(message, Mapping):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                text = first.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
        generated_text = payload.get("generated_text")
        if isinstance(generated_text, str) and generated_text.strip():
            return generated_text.strip()

    if isinstance(payload, Sequence) and payload and not isinstance(payload, str):
        first = payload[0]
        if isinstance(first, Mapping):
            generated_text = first.get("generated_text")
            if isinstance(generated_text, str) and generated_text.strip():
                return generated_text.strip()

    compact_payload = json.dumps(payload, ensure_ascii=False)[:500]
    raise ValueError(f"Unable to extract LLM text from response: {compact_payload}")
