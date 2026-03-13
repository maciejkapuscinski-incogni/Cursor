from datetime import UTC, datetime

from meta_ads.normalize import compute_duration_days, normalize_ad, parse_meta_datetime


def test_compute_duration_days_for_active_ad() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    now = datetime(2026, 2, 5, tzinfo=UTC)

    assert compute_duration_days(start, None, now=now) == 35.0


def test_parse_meta_datetime_accepts_date_only_values() -> None:
    parsed = parse_meta_datetime("2026-02-05")

    assert parsed == datetime(2026, 2, 5, tzinfo=UTC)


def test_normalize_ad_marks_30d_plus() -> None:
    payload = {
        "id": "123",
        "page_id": "999",
        "page_name": "Test Brand",
        "ad_creation_time": "2026-01-01T12:00:00+0000",
        "ad_delivery_start_time": "2026-01-01T12:00:00+0000",
        "ad_delivery_stop_time": "2026-02-15T12:00:00+0000",
        "ad_snapshot_url": "https://example.com/snapshot",
        "ad_creative_bodies": ["Strong hook"],
        "ad_creative_link_captions": ["caption"],
        "ad_creative_link_descriptions": ["desc"],
        "ad_creative_link_titles": ["title"],
        "languages": ["en"],
        "publisher_platforms": ["FACEBOOK"],
    }

    normalized = normalize_ad(payload, requested_media_type="VIDEO")

    assert normalized.meta_ad_id == "123"
    assert normalized.media_type_guess == "VIDEO"
    assert normalized.is_running_30d_plus is True
    assert normalized.duration_days == 45.0
