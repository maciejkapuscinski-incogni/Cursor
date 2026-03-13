from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def parse_meta_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    # Date-only, Meta API with %z, or ISO 8601 with Z / .000Z (Apify, JavaScript)
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            parsed = datetime.strptime(value.strip(), fmt)
            if fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
                return parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            continue
    raise ValueError(f"Unsupported Meta datetime format: {value}")


def listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def guess_media_type(payload: dict[str, Any], requested_media_type: str | None = None) -> str:
    if requested_media_type:
        return requested_media_type.upper()
    snapshot_url = str(payload.get("ad_snapshot_url") or "").lower()
    if ".mp4" in snapshot_url or "video" in snapshot_url:
        return "VIDEO"
    if any(payload.get(key) for key in ("ad_creative_link_titles", "ad_creative_link_descriptions")):
        return "IMAGE"
    return "UNKNOWN"


def compute_duration_days(
    start: datetime | None,
    stop: datetime | None,
    now: datetime | None = None,
) -> float | None:
    if start is None:
        return None
    effective_now = now or datetime.now(UTC)
    effective_end = stop or effective_now
    if effective_end < start:
        return 0.0
    return round((effective_end - start).total_seconds() / 86400, 2)


@dataclass(slots=True)
class NormalizedAd:
    meta_ad_id: str
    page_id: str | None
    page_name: str | None
    ad_creation_time: datetime | None
    ad_delivery_start_time: datetime | None
    ad_delivery_stop_time: datetime | None
    ad_snapshot_url: str | None
    ad_creative_bodies: list[str]
    ad_creative_link_captions: list[str]
    ad_creative_link_descriptions: list[str]
    ad_creative_link_titles: list[str]
    languages: list[str]
    publisher_platforms: list[str]
    media_type_guess: str
    duration_days: float | None
    is_running_30d_plus: bool
    # When using Apify (or another source that provides media URL directly)
    pre_resolved_media_url: str | None = None
    pre_resolved_media_type: str | None = None  # "video" | "image"


def normalize_ad(payload: dict[str, Any], requested_media_type: str | None = None) -> NormalizedAd:
    start_time = parse_meta_datetime(payload.get("ad_delivery_start_time"))
    stop_time = parse_meta_datetime(payload.get("ad_delivery_stop_time"))
    duration_days = compute_duration_days(start_time, stop_time)

    return NormalizedAd(
        meta_ad_id=str(payload["id"]),
        page_id=str(payload["page_id"]) if payload.get("page_id") else None,
        page_name=payload.get("page_name"),
        ad_creation_time=parse_meta_datetime(payload.get("ad_creation_time")),
        ad_delivery_start_time=start_time,
        ad_delivery_stop_time=stop_time,
        ad_snapshot_url=payload.get("ad_snapshot_url"),
        ad_creative_bodies=listify(payload.get("ad_creative_bodies")),
        ad_creative_link_captions=listify(payload.get("ad_creative_link_captions")),
        ad_creative_link_descriptions=listify(payload.get("ad_creative_link_descriptions")),
        ad_creative_link_titles=listify(payload.get("ad_creative_link_titles")),
        languages=listify(payload.get("languages")),
        publisher_platforms=listify(payload.get("publisher_platforms")),
        media_type_guess=guess_media_type(payload, requested_media_type=requested_media_type),
        duration_days=duration_days,
        is_running_30d_plus=bool(duration_days is not None and duration_days >= 30),
        pre_resolved_media_url=str(payload.get("_resolved_media_url")) if payload.get("_resolved_media_url") else None,
        pre_resolved_media_type=str(payload.get("_resolved_media_type")) if payload.get("_resolved_media_type") else None,
    )
