from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

RawFootprints = Mapping[str, Any] | Sequence[Mapping[str, Any]] | str | None

_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")
_SEGMENT_CODE_RE = re.compile(r"^\s*\d+\s+")
_FILE_EXTENSION_RE = re.compile(r"\.(gif|png|jpe?g|webp|svg|css|js|ico|woff2?|ttf|map)$", re.IGNORECASE)

_SLUG_TOKEN_TRANSLATIONS = {
    "akcii": "акции",
    "aktsii": "акции",
    "besplatnye": "бесплатные",
    "besplatnyj": "бесплатный",
    "besplatnyi": "бесплатный",
    "cherchenie": "черчение",
    "dlya": "для",
    "fgos": "ФГОС",
    "izo": "ИЗО",
    "kvalifikacii": "квалификации",
    "kurs": "курс",
    "kursy": "курсы",
    "mhk": "МХК",
    "obrazovanie": "образование",
    "obuchenie": "обучение",
    "obzh": "ОБЖ",
    "pedagog": "педагог",
    "pedagogi": "педагоги",
    "pedagogov": "педагогов",
    "povysheniya": "повышения",
    "skidki": "скидки",
    "shkola": "школа",
}

_LOW_VALUE_SEGMENT_MARKERS = (
    "почта в ",
    "mail.ru",
    "прочитавшие",
)


@dataclass(slots=True, frozen=True)
class FootprintEvent:
    kind: str
    timestamp: str
    title: str
    description: str
    summary: str
    importance: int
    entities: Mapping[str, Any]


def build_digital_footprint_profile_text(digital_footprints: RawFootprints, *, max_events: int = 25) -> str:
    """Convert Mautic/API footprints into a compact semantic profile for embedding."""

    if isinstance(digital_footprints, str):
        return _normalize_space(digital_footprints) or "No user activity was found in Mautic."

    lead_id = _extract_lead_id(digital_footprints)
    events = _extract_events(digital_footprints)
    if not events:
        return "No user activity was found in Mautic."

    limited_events = events[:max_events]
    topics = _score_topics(limited_events)
    segments = _collect_segments(limited_events)
    page_topics = _collect_page_topics(limited_events)
    email_titles = _collect_email_titles(limited_events)

    lines: list[str] = ["Цифровой профиль пользователя для поиска релевантного образовательного контента."]
    if lead_id:
        lines.append(f"Lead ID: {lead_id}.")

    if topics:
        lines.append("Ключевые интересы: " + "; ".join(topic for topic, _ in topics[:8]) + ".")
    if segments:
        lines.append("Сегменты и устойчивые признаки: " + "; ".join(segments[:8]) + ".")
    if page_topics:
        lines.append("Интерес по посещенным страницам: " + "; ".join(page_topics[:6]) + ".")
    if email_titles:
        lines.append(f"Email-вовлеченность: открыто писем {len(email_titles)}; темы/выпуски: " + "; ".join(email_titles[:5]) + ".")

    lines.append("Значимые действия:")
    for index, event in enumerate(limited_events, start=1):
        event_line = _format_event_line(index, event)
        if event_line:
            lines.append(event_line)

    return "\n".join(lines)


def _extract_lead_id(digital_footprints: RawFootprints) -> str:
    if not isinstance(digital_footprints, Mapping):
        return ""
    lead_id = digital_footprints.get("lead_id")
    return _normalize_space(str(lead_id)) if lead_id is not None else ""


def _extract_events(digital_footprints: RawFootprints) -> list[FootprintEvent]:
    raw_events: Sequence[Any] | None = None
    if isinstance(digital_footprints, Mapping):
        for key in ("actions", "events"):
            candidate = digital_footprints.get(key)
            if isinstance(candidate, Sequence) and not isinstance(candidate, str):
                raw_events = candidate
                break
    elif isinstance(digital_footprints, Sequence):
        raw_events = digital_footprints

    if raw_events is None:
        return []

    events: list[FootprintEvent] = []
    for raw_event in raw_events:
        if not isinstance(raw_event, Mapping):
            continue
        event = _normalize_event(raw_event)
        if event is not None:
            events.append(event)
    return events


def _normalize_event(raw_event: Mapping[str, Any]) -> FootprintEvent | None:
    data = raw_event.get("data")
    event_data = data if isinstance(data, Mapping) else raw_event
    kind = _first_text(raw_event, "type", "activity_kind", "event_type") or _first_text(event_data, "activity_kind", "raw_type")
    title = _first_text(event_data, "title", "entity_name") or _first_text(raw_event, "title", "entity_name")
    summary = _first_text(event_data, "summary") or _first_text(raw_event, "summary")
    description = _first_text(event_data, "description") or _first_text(raw_event, "description")
    timestamp = _first_text(event_data, "timestamp") or _first_text(raw_event, "timestamp")
    raw_importance = event_data.get("importance", raw_event.get("importance", 1))

    try:
        importance = int(raw_importance)
    except (TypeError, ValueError):
        importance = 1

    entities = event_data.get("entities")
    normalized_entities = entities if isinstance(entities, Mapping) else {}
    if not any((kind, title, summary, description, normalized_entities)):
        return None

    return FootprintEvent(
        kind=_normalize_space(kind),
        timestamp=_normalize_space(timestamp),
        title=_normalize_space(title),
        description=_normalize_space(description),
        summary=_normalize_space(summary),
        importance=importance,
        entities=normalized_entities,
    )


def _first_text(data: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _score_topics(events: Sequence[FootprintEvent]) -> list[tuple[str, float]]:
    scores: Counter[str] = Counter()
    for event in events:
        weight = max(event.importance, 1)
        for topic in _event_topics(event):
            scores[topic] += weight
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def _event_topics(event: FootprintEvent) -> list[str]:
    topics: list[str] = []
    topics.extend(_extract_segments(event))
    topics.extend(_extract_page_topics(event))
    topics.extend(_extract_url_topics(event.title))
    topics.extend(_extract_url_topics(event.summary))
    return _dedupe_preserve_order(_clean_topic(topic) for topic in topics if topic)


def _collect_segments(events: Sequence[FootprintEvent]) -> list[str]:
    result: list[str] = []
    for event in events:
        result.extend(_extract_segments(event))
    return _dedupe_preserve_order(_clean_topic(item) for item in result if item and not _is_low_value_segment(item))


def _collect_page_topics(events: Sequence[FootprintEvent]) -> list[str]:
    result: list[str] = []
    for event in events:
        if event.kind != "page_hit":
            continue
        result.extend(_extract_page_topics(event))
        result.extend(_extract_url_topics(event.title))
    return _dedupe_preserve_order(_clean_topic(item) for item in result if item)


def _collect_email_titles(events: Sequence[FootprintEvent]) -> list[str]:
    titles: list[str] = []
    for event in events:
        if event.kind != "email_opened":
            continue
        title = event.title or event.summary
        if title and title.lower() not in {"read", "email opened"}:
            titles.append(title)
    return _dedupe_preserve_order(titles)


def _extract_segments(event: FootprintEvent) -> list[str]:
    segment = event.entities.get("segment")
    if isinstance(segment, Mapping):
        name = segment.get("name")
        if isinstance(name, str) and name.strip():
            return [name.strip()]

    title = event.title or event.summary
    marker = "segment,"
    if marker in title.lower():
        return [title.split(",", 1)[1].strip()]
    return []


def _extract_page_topics(event: FootprintEvent) -> list[str]:
    page = event.entities.get("page")
    result: list[str] = []
    if isinstance(page, Mapping):
        for key in ("title", "url"):
            value = page.get(key)
            if isinstance(value, str) and value.strip():
                if key == "url":
                    result.extend(_extract_url_topics(value))
                else:
                    result.append(value.strip())
    return result


def _extract_url_topics(text: str) -> list[str]:
    topics: list[str] = []
    for match in _URL_RE.finditer(text):
        topic = _topic_from_url(match.group(0))
        if topic:
            topics.append(topic)
    if text.startswith(("http://", "https://")):
        topic = _topic_from_url(text)
        if topic:
            topics.append(topic)
    return _dedupe_preserve_order(topics)


def _topic_from_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = unquote(parsed.path or "")
    if not path or _FILE_EXTENSION_RE.search(path):
        return ""

    parts = [part for part in path.split("/") if part]
    if not parts:
        return ""
    slug = parts[-1]
    slug = re.sub(r"\.[a-z0-9]{2,5}$", "", slug, flags=re.IGNORECASE)
    slug = slug.replace("_", "-")
    tokens = [token for token in slug.split("-") if token and not token.isdigit()]
    if not tokens:
        return ""

    translated = [_SLUG_TOKEN_TRANSLATIONS.get(token.lower(), token) for token in tokens]
    return _normalize_space(" ".join(translated))


def _format_event_line(index: int, event: FootprintEvent) -> str:
    label = _event_label(event.kind)
    details = _event_details(event)
    if not details:
        return ""

    parts = [f"{index}. {label}: {details}"]
    if event.timestamp:
        parts.append(f"дата={event.timestamp}")
    parts.append(f"важность={event.importance}")
    return " | ".join(parts) + "."


def _event_details(event: FootprintEvent) -> str:
    if event.kind in {"view", "favorite", "search", "article_read"}:
        return event.title or event.summary or event.description
    if event.kind == "segment_membership_change":
        segments = _extract_segments(event)
        return _clean_topic(segments[0]) if segments else event.summary or event.title
    if event.kind == "page_hit":
        page_topics = _extract_page_topics(event) or _extract_url_topics(event.title)
        if page_topics:
            return "; ".join(_clean_topic(topic) for topic in page_topics if topic)
        if event.title.startswith(("http://", "https://")) and _FILE_EXTENSION_RE.search(urlparse(event.title).path):
            return ""
        return event.title or event.summary
    if event.kind == "email_opened":
        return event.title or event.summary or "открытие письма"
    return event.summary or event.title or event.description


def _event_label(kind: str) -> str:
    labels = {
        "email_opened": "открытие письма",
        "form_submitted": "отправка формы",
        "page_hit": "посещение страницы",
        "segment_membership_change": "сегмент",
    }
    return labels.get(kind, kind or "действие")


def _clean_topic(topic: str) -> str:
    cleaned = _SEGMENT_CODE_RE.sub("", topic)
    cleaned = cleaned.replace("Contact added to segment,", "")
    cleaned = cleaned.strip(" .;:-")
    return _normalize_space(cleaned)


def _is_low_value_segment(segment: str) -> bool:
    lowered = segment.lower()
    return any(marker in lowered for marker in _LOW_VALUE_SEGMENT_MARKERS)


def _dedupe_preserve_order(values: Sequence[str] | Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _normalize_space(str(value))
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _normalize_space(value: str | None) -> str:
    if not value:
        return ""
    return _SPACE_RE.sub(" ", value).strip()
