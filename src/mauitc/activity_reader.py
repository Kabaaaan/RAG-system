from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import parse_qs, urlparse


class MauticActivityReader:
    _TYPE_KEYS = ("eventType", "type", "event")
    _TIMESTAMP_KEYS = ("timestamp", "dateAdded", "date_added", "createdAt", "created_at")
    _TITLE_KEYS = ("eventLabel", "label", "title")
    _DESCRIPTION_KEYS = ("description", "details", "note")
    _ID_KEYS = ("id", "eventId", "event_id")
    _CONTACT_ID_KEYS = ("leadId", "lead_id", "contactId", "contact_id")
    _CONTEXT_KEYS: dict[str, tuple[str, ...]] = {
        "email": ("id", "name", "subject"),
        "page": ("id", "title", "url"),
        "form": ("id", "name"),
        "asset": ("id", "title", "name"),
    }

    _CLASSIFICATION_RULES: dict[str, dict[str, Any]] = {
        "email_opened": {"importance": 5, "parse": True},
        "form_submitted": {"importance": 5, "parse": True},
        "page_hit": {"importance": 4, "parse": True},
        "do_not_contact": {"importance": 4, "parse": False},
        "utm_recorded": {"importance": 3, "parse": False},
        "segment_membership_change": {"importance": 3, "parse": True},
        "accessed_from_ip": {"importance": 3, "parse": False},
        "email_sent": {"importance": 2, "parse": False},
        "contact_lifecycle": {"importance": 2, "parse": False},
        "contact_profile_update": {"importance": 1, "parse": False},
        "unknown": {"importance": 1, "parse": False},
    }

    @staticmethod
    def _as_clean_text(value: Any) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, Mapping):
            for key in ("label", "name", "title", "subject", "url", "type"):
                nested = value.get(key)
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()
            return None
        if value is None:
            return None
        if isinstance(value, list):
            return None
        return str(value)

    @classmethod
    def _first_present(cls, data: Mapping[str, Any], keys: Iterable[str]) -> str | None:
        for key in keys:
            value = cls._as_clean_text(data.get(key))
            if value:
                return value
        return None

    @staticmethod
    def _collect_events(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        events = payload.get("events")
        raw_events: Iterable[Any]
        if isinstance(events, Mapping):
            raw_events = events.values()
        elif isinstance(events, list):
            raw_events = events
        else:
            return []
        return [event for event in raw_events if isinstance(event, Mapping)]

    @classmethod
    def _extract_context(cls, event: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        context: dict[str, dict[str, Any]] = {}
        for section_name, allowed_keys in cls._CONTEXT_KEYS.items():
            section = event.get(section_name)
            if not isinstance(section, Mapping):
                continue
            filtered_section = {
                key: value
                for key, value in section.items()
                if key in allowed_keys and value is not None and not isinstance(value, dict | list)
            }
            if filtered_section:
                context[section_name] = filtered_section
        return context

    @classmethod
    def _search_blob(cls, event: Mapping[str, Any]) -> str:
        candidate_keys = (
            *cls._TYPE_KEYS,
            *cls._TITLE_KEYS,
            *cls._DESCRIPTION_KEYS,
            "actionName",
            "eventName",
            "name",
            "message",
        )
        parts: list[str] = []
        for key in candidate_keys:
            value = cls._as_clean_text(event.get(key))
            if value:
                parts.append(value.lower())
        return " | ".join(parts)

    @classmethod
    def _extract_segment_name(cls, event: Mapping[str, Any]) -> str | None:
        segment = event.get("segment")
        if isinstance(segment, Mapping):
            segment_name = cls._as_clean_text(segment.get("name"))
            if segment_name:
                return segment_name
        segment_name = cls._first_present(event, ("segmentName", "segment_name"))
        if segment_name:
            return segment_name

        title = cls._as_clean_text(event.get("title")) or cls._as_clean_text(event.get("eventLabel"))
        if not title:
            return None
        marker = "segment,"
        lowered = title.lower()
        if marker not in lowered:
            return None
        _, _, tail = title.partition(",")
        candidate = tail.strip()
        return candidate or None

    @classmethod
    def _resolve_activity_kind(cls, event: Mapping[str, Any]) -> str:
        blob = cls._search_blob(event)

        if "do not contact" in blob or "suppression" in blob or "unsubscribe" in blob:
            return "do_not_contact"
        if "utm" in blob:
            return "utm_recorded"
        if "form submitted" in blob or "form submit" in blob or "form.submitted" in blob:
            return "form_submitted"
        if (
            "email read" in blob
            or "email opened" in blob
            or "email open" in blob
            or "email.read" in blob
            or "email.open" in blob
        ):
            return "email_opened"
        if "email sent" in blob:
            return "email_sent"
        if "page hit" in blob or "page.hit" in blob or "visited page" in blob or "pageview" in blob:
            return "page_hit"
        if "segment membership change" in blob or "added to segment" in blob or "segment" in blob:
            return "segment_membership_change"
        if "accessed from ip" in blob or "ip" in blob:
            return "accessed_from_ip"
        if (
            "contact identified" in blob
            or "identified by source" in blob
            or "contact created" in blob
            or "imported" in blob
        ):
            return "contact_lifecycle"
        if "updated from csv" in blob or "housekeeping" in blob or "name changed" in blob:
            return "contact_profile_update"
        return "unknown"

    @classmethod
    def _extract_utm_from_url(cls, url: str | None) -> dict[str, str]:
        if not url:
            return {}
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        utm: dict[str, str] = {}
        for key in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"):
            values = query.get(key)
            if values and values[0]:
                utm[key] = values[0]
        return utm

    @classmethod
    def _extract_entities(cls, event: Mapping[str, Any], kind: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        context = cls._extract_context(event)
        raw_description = event.get("description")
        raw_details = raw_description if isinstance(raw_description, Mapping) else {}

        if kind == "email_opened":
            if "email" in context:
                entities["email"] = context["email"]
            stat = raw_details.get("stat")
            if isinstance(stat, Mapping):
                email_meta: dict[str, Any] = {}
                for key in ("email_id", "subject", "email_name", "list_name", "dateSent", "dateRead"):
                    value = stat.get(key)
                    if value is not None and not isinstance(value, dict | list):
                        email_meta[key] = value
                if email_meta:
                    entities["email_meta"] = email_meta

        if kind == "form_submitted":
            if "form" in context:
                entities["form"] = context["form"]

        if kind == "page_hit":
            if "page" in context:
                entities["page"] = context["page"]
                page_url = context["page"].get("url")
                if isinstance(page_url, str):
                    utm = cls._extract_utm_from_url(page_url)
                    if utm:
                        entities["utm"] = utm

        if kind == "segment_membership_change":
            segment_name = cls._extract_segment_name(event)
            if segment_name:
                entities["segment"] = {"name": segment_name}

        return entities

    @staticmethod
    def _build_summary(activity_kind: str, entities: Mapping[str, Any]) -> str:
        if activity_kind == "email_opened":
            email_meta = entities.get("email_meta")
            if isinstance(email_meta, Mapping):
                subject = email_meta.get("subject")
                if isinstance(subject, str) and subject.strip():
                    return f"Email opened: {subject.strip()}"
            return "Email opened"
        if activity_kind == "form_submitted":
            form = entities.get("form")
            if isinstance(form, Mapping):
                name = form.get("name")
                if isinstance(name, str) and name.strip():
                    return f"Form submitted: {name.strip()}"
            return "Form submitted"
        if activity_kind == "page_hit":
            page = entities.get("page")
            if isinstance(page, Mapping):
                title = page.get("title")
                url = page.get("url")
                if isinstance(title, str) and title.strip():
                    return f"Page hit: {title.strip()}"
                if isinstance(url, str) and url.strip():
                    return f"Page hit: {url.strip()}"
            return "Page hit"
        if activity_kind == "segment_membership_change":
            segment = entities.get("segment")
            if isinstance(segment, Mapping):
                name = segment.get("name")
                if isinstance(name, str) and name.strip():
                    return f"Segment membership change: {name.strip()}"
            return "Segment membership change"
        return activity_kind

    @classmethod
    def normalize_event(cls, event: Mapping[str, Any], *, keep_raw: bool = False) -> dict[str, Any]:
        kind = cls._resolve_activity_kind(event)
        rule = cls._CLASSIFICATION_RULES[kind]
        should_parse = bool(rule["parse"])

        normalized: dict[str, Any] = {
            "id": cls._first_present(event, cls._ID_KEYS),
            "raw_type": cls._first_present(event, cls._TYPE_KEYS),
            "activity_kind": kind,
            "timestamp": cls._first_present(event, cls._TIMESTAMP_KEYS),
            "title": cls._first_present(event, cls._TITLE_KEYS),
            "description": cls._first_present(event, cls._DESCRIPTION_KEYS),
            "contact_id": cls._first_present(event, cls._CONTACT_ID_KEYS),
            "importance": rule["importance"],
            "should_parse": should_parse,
        }

        entities = cls._extract_entities(event, kind)
        if entities:
            normalized["entities"] = entities
        normalized["summary"] = cls._build_summary(kind, entities)

        if keep_raw:
            normalized["raw"] = dict(event)
        return normalized

    @staticmethod
    def _normalize_types(types: Iterable[str] | None) -> set[str] | None:
        if types is None:
            return None
        normalized_types = {
            event_type.strip().lower() for event_type in types if event_type and event_type.strip()
        }
        return normalized_types or None

    @classmethod
    def read_events(
        cls,
        payload: Mapping[str, Any],
        *,
        include_types: Iterable[str] | None = None,
        exclude_types: Iterable[str] | None = None,
        parse_only: bool = True,
        keep_raw: bool = False,
    ) -> list[dict[str, Any]]:
        include = cls._normalize_types(include_types)
        exclude = cls._normalize_types(exclude_types)
        result: list[dict[str, Any]] = []

        for event in cls._collect_events(payload):
            normalized_event = cls.normalize_event(event, keep_raw=keep_raw)
            activity_kind = cls._as_clean_text(normalized_event.get("activity_kind")) or ""
            raw_type = cls._as_clean_text(normalized_event.get("raw_type")) or ""
            normalized_keys = {activity_kind.lower(), raw_type.lower()}

            if include is not None and normalized_keys.isdisjoint(include):
                continue
            if exclude is not None and not normalized_keys.isdisjoint(exclude):
                continue
            if parse_only and not bool(normalized_event.get("should_parse")):
                continue

            result.append(normalized_event)

        return result
