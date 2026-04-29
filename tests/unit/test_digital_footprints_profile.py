from __future__ import annotations

from src.preprocessing.digital_footprints import build_digital_footprint_profile_text


def test_profile_builder_supports_actions_payload_and_url_topics() -> None:
    payload = {
        "lead_id": "188736",
        "actions": [
            {
                "id": "384894",
                "type": "page_hit",
                "data": {
                    "timestamp": "2026-03-23T10:23:27+03:00",
                    "title": "https://moi-universitet.ru/besplatnye-kursy-povysheniya-kvalifikacii-dlya-pedagogov",
                    "importance": 4,
                    "summary": "Page hit",
                },
            },
            {
                "id": "segment_membership872318",
                "type": "segment_membership_change",
                "data": {
                    "title": "Contact added to segment, \u041f\u0435\u0434\u0430\u0433\u043e\u0433\u0438 \u042e\u041b",
                    "importance": 3,
                    "entities": {
                        "segment": {
                            "name": "\u041f\u0435\u0434\u0430\u0433\u043e\u0433\u0438 \u042e\u041b",
                        }
                    },
                    "summary": "Segment membership change: \u041f\u0435\u0434\u0430\u0433\u043e\u0433\u0438 \u042e\u041b",
                },
            },
        ],
    }

    profile = build_digital_footprint_profile_text(payload)

    assert "Lead ID: 188736" in profile
    assert "\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0435 \u043a\u0443\u0440\u0441\u044b" in profile
    assert "\u043f\u043e\u0432\u044b\u0448\u0435\u043d\u0438\u044f \u043a\u0432\u0430\u043b\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u0438" in profile
    assert "\u041f\u0435\u0434\u0430\u0433\u043e\u0433\u0438 \u042e\u041b" in profile


def test_profile_builder_cleans_segment_codes_and_keeps_subjects() -> None:
    profile = build_digital_footprint_profile_text(
        [
            {
                "activity_kind": "segment_membership_change",
                "title": (
                    "Contact added to segment, "
                    "931 \u0414\u043e\u0448\u043a\u043e\u043b\u044c\u043d\u043e\u0435 "
                    "\u043e\u0431\u0440\u0430\u0437\u043e\u0432\u0430\u043d\u0438\u0435"
                ),
                "importance": 3,
                "entities": {
                    "segment": {
                        "name": (
                            "931 \u0414\u043e\u0448\u043a\u043e\u043b\u044c\u043d\u043e\u0435 "
                            "\u043e\u0431\u0440\u0430\u0437\u043e\u0432\u0430\u043d\u0438\u0435"
                        ),
                    }
                },
            },
            {
                "activity_kind": "segment_membership_change",
                "title": "Contact added to segment, 914 \u041e\u0411\u0416",
                "importance": 3,
                "entities": {"segment": {"name": "914 \u041e\u0411\u0416"}},
            },
        ]
    )

    assert "931 \u0414\u043e\u0448\u043a\u043e\u043b\u044c\u043d\u043e\u0435" not in profile
    assert "\u0414\u043e\u0448\u043a\u043e\u043b\u044c\u043d\u043e\u0435 \u043e\u0431\u0440\u0430\u0437\u043e\u0432\u0430\u043d\u0438\u0435" in profile
    assert "\u041e\u0411\u0416" in profile


def test_profile_builder_ignores_file_asset_urls_as_topics() -> None:
    profile = build_digital_footprint_profile_text(
        [
            {
                "activity_kind": "page_hit",
                "title": "http://www.moi-universitet.ru/resources/5055-original.gif",
                "importance": 4,
                "summary": "Page hit",
            }
        ]
    )

    assert "5055-original" not in profile
