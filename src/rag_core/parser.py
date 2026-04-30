"""Utilities for parsing structured payloads from raw LLM text responses."""

from __future__ import annotations

import json


def parse_recommendation_payload(raw_text: str) -> dict[str, object]:
    """Extract a JSON recommendation payload from raw LLM output.

    The LLM is expected to return a JSON object.  If the response contains
    surrounding prose, the function attempts to locate the first ``{…}``
    block and parse only that.

    Args:
        raw_text: Raw string returned by the LLM.

    Returns:
        Parsed recommendation payload as a dictionary.

    Raises:
        ValueError: If the text is empty, contains no valid JSON object, or
                    the parsed value is not a dictionary.
    """
    stripped = raw_text.strip()
    if not stripped:
        raise ValueError("LLM returned an empty recommendation payload.")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM did not return valid JSON.") from None
        payload = json.loads(stripped[start : end + 1])

    if not isinstance(payload, dict):
        raise ValueError("Recommendation payload must be a JSON object.")
    return payload
