from src.mauitc.activity_reader import MauticActivityReader


def test_read_events_filters_and_normalizes() -> None:
    payload = {
        "events": [
            {
                "id": 11,
                "eventType": "page.hit",
                "timestamp": "2026-04-14T09:00:00+00:00",
                "eventLabel": "Visited pricing",
                "leadId": 101,
                "page": {
                    "id": 7,
                    "title": "Pricing",
                    "url": "https://example.com/pricing",
                    "extra": "ignore",
                },
            },
            {
                "id": 12,
                "eventType": "email.sent",
                "timestamp": "2026-04-14T09:01:00+00:00",
            },
        ]
    }

    events = MauticActivityReader.read_events(payload, include_types={"page_hit"})

    assert len(events) == 1
    assert events[0]["activity_kind"] == "page_hit"
    assert events[0]["contact_id"] == "101"
    assert events[0]["should_parse"] is True
    assert events[0]["entities"]["page"] == {
        "id": 7,
        "title": "Pricing",
        "url": "https://example.com/pricing",
    }


def test_read_events_handles_mapping_payload() -> None:
    payload = {
        "events": {
            "20": {
                "event_id": "20",
                "type": "form.submitted",
                "dateAdded": "2026-04-14T10:00:00+00:00",
                "form": {"id": 4, "name": "Lead form"},
            }
        }
    }

    events = MauticActivityReader.read_events(payload)

    assert len(events) == 1
    assert events[0]["id"] == "20"
    assert events[0]["activity_kind"] == "form_submitted"
    assert events[0]["entities"]["form"] == {"id": 4, "name": "Lead form"}
