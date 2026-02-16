from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

Event = Mapping[str, Any]
DigitalFootprints = Mapping[str, Any] | Sequence[Event] | str | None


def create_embedding_passage_input(title: str, description: str) -> str:
    text = f"""
    Название: {title}
    Описание:
    {description}
    """
    return "passage: " + text


def create_embedding_question_input(digital_footprints: DigitalFootprints) -> str:
    events: Sequence[Event] | None = None
    if isinstance(digital_footprints, Mapping):
        raw_events = digital_footprints.get("events")
        if isinstance(raw_events, Sequence):
            events = raw_events
    elif isinstance(digital_footprints, Sequence) and not isinstance(digital_footprints, str):
        events = digital_footprints

    if not events:
        text = f"{digital_footprints}".strip()
        return "query: " + text

    views: list[str] = []
    favorites: list[str] = []
    searches: list[str] = []
    articles: list[str] = []
    other: list[str] = []

    for event in events:
        if not isinstance(event, Mapping):
            continue
        event_type = str(event.get("event_type") or "").strip()
        entity_type = str(event.get("entity_type") or "").strip()
        entity_name = str(event.get("entity_name") or "").strip()
        duration = event.get("duration_seconds")

        if not entity_name:
            continue

        duration_info = ""
        if isinstance(duration, int | float) and duration > 0:
            duration_info = f" ({int(duration)} sec)"

        if event_type == "view":
            label = f"View {entity_type}" if entity_type else "View"
            views.append(f'{label} "{entity_name}"{duration_info}')
        elif event_type == "favorite":
            label = f"Favorite {entity_type}" if entity_type else "Favorite"
            favorites.append(f'{label} "{entity_name}"')
        elif event_type == "search":
            searches.append(f"Search: {entity_name}")
        elif event_type == "article_read":
            articles.append(f'Article: "{entity_name}"{duration_info}')
        else:
            label = event_type or "event"
            prefix = f"{label} {entity_type}".strip()
            other.append(f'{prefix} "{entity_name}"{duration_info}')

    parts: list[str] = []
    if views:
        parts.append("Просмотры: " + "; ".join(views))
    if favorites:
        parts.append("Избранное: " + "; ".join(favorites))
    if searches:
        parts.append("Поиск: " + "; ".join(searches))
    if articles:
        parts.append("Статьи: " + "; ".join(articles))
    if other:
        parts.append("Другое: " + "; ".join(other))

    summary = " | ".join(parts).strip()
    return "query: " + summary
