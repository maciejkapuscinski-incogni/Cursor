"""Apify Facebook Ads Scraper client. Use when Meta Ads Library API + snapshot fetch fails (e.g. 400)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx


def validate_apify_json_data(data: Any) -> list[dict[str, Any]]:
    """
    Validate parsed JSON as Apify ad list. Raises ValueError on unexpected shape.
    Returns list of raw ad items (each a dict with adArchiveId/id).
    """
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON root must be an array of ad objects or a single ad object.")

    items: list[dict[str, Any]] = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise ValueError(f"Item at index {i} is not an object (got {type(raw).__name__}).")
        has_id = any(raw.get(k) for k in ("adArchiveId", "adArchiveID", "id"))
        if not has_id:
            raise ValueError(
                f"Item at index {i} missing ad identifier: expected one of adArchiveId, adArchiveID, id."
            )
        items.append(raw)
    return items


def load_and_validate_apify_json(path: Path) -> list[dict[str, Any]]:
    """
    Load JSON file from Apify export and validate structure.
    Raises ValueError on invalid syntax or unexpected shape.
    Returns list of raw ad items (each a dict with adArchiveId/id and snapshot).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"Cannot read file: {path}") from e
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON syntax: {e}") from e
    return validate_apify_json_data(data)


def load_and_validate_apify_from_url(url: str, timeout: float = 60.0) -> list[dict[str, Any]]:
    """
    Fetch JSON from an Apify dataset items URL and validate structure.
    Example: https://api.apify.com/v2/datasets/DATASET_ID/items?format=json&clean=true
    Raises ValueError on invalid syntax or unexpected shape.
    Returns list of raw ad items.
    """
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from URL: {e}") from e
    return validate_apify_json_data(data)



@dataclass(slots=True)
class ApifyAdsPage:
    """One page of ads from Apify (actor returns one dataset; we yield one page with all items)."""
    ads: list[dict[str, Any]]
    next_page_url: None = None
    next_cursor: None = None


def _first_media_url_from_card(card: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (url, type) for first video or image in a card. type is 'video' or 'image'."""
    for key in ("videoHdUrl", "videoSdUrl", "watermarkedVideoHdUrl", "watermarkedVideoSdUrl"):
        url = card.get(key)
        if url and isinstance(url, str) and url.strip():
            return (url.strip(), "video")
    url = card.get("originalImageUrl") or card.get("resizedImageUrl")
    if url and isinstance(url, str) and url.strip():
        return (url.strip(), "image")
    return (None, None)


def _first_media_from_snapshot(snapshot: dict[str, Any]) -> tuple[str | None, str | None]:
    """Get first video or image URL from snapshot (cards or top-level videos/images)."""
    cards = snapshot.get("cards") or []
    for card in cards:
        url, kind = _first_media_url_from_card(card)
        if url:
            return (url, kind)
    for key in ("videos", "extraVideos"):
        for v in (snapshot.get(key) or []):
            if isinstance(v, dict):
                url = v.get("videoHdUrl") or v.get("videoSdUrl")
                if url and isinstance(url, str) and url.strip():
                    return (url.strip(), "video")
            elif isinstance(v, str) and v.strip():
                return (v.strip(), "video")
    images = snapshot.get("images") or []
    for img in images:
        if isinstance(img, dict):
            url = img.get("originalImageUrl") or img.get("resizedImageUrl")
            if url and isinstance(url, str) and url.strip():
                return (url.strip(), "image")
        elif isinstance(img, str) and img.strip():
            return (img.strip(), "image")
    return (None, None)


def apify_item_to_meta_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Convert one Apify dataset item to a Meta-API-like payload for normalize_ad + pipeline."""
    ad_id = str(item.get("adArchiveId") or item.get("adArchiveID") or item.get("id") or "")
    page_id = str(item.get("pageId") or item.get("pageID") or "")
    page_name = item.get("pageName") or ""
    start_str = item.get("startDateFormatted")
    end_str = item.get("endDateFormatted")
    snapshot = item.get("snapshot") or {}
    body = snapshot.get("body") or {}
    body_text = body.get("text") if isinstance(body, dict) else str(body) if body else ""
    cards = snapshot.get("cards") or []
    titles: list[str] = []
    captions: list[str] = []
    for c in cards:
        if isinstance(c, dict):
            if c.get("title"):
                titles.append(str(c["title"]))
            if c.get("caption"):
                captions.append(str(c["caption"]))
    if not titles and body_text:
        titles = [body_text]

    resolved_url, resolved_type = _first_media_from_snapshot(snapshot)

    # Build Meta-API-shaped payload so normalize_ad and pipeline work
    payload: dict[str, Any] = {
        "id": ad_id,
        "page_id": page_id,
        "page_name": page_name,
        "ad_creation_time": None,
        "ad_delivery_start_time": start_str,
        "ad_delivery_stop_time": end_str,
        "ad_snapshot_url": f"https://www.facebook.com/ads/archive/render_ad/?id={ad_id}",
        "ad_creative_bodies": [body_text] if body_text else [],
        "ad_creative_link_captions": captions,
        "ad_creative_link_descriptions": [],
        "ad_creative_link_titles": titles,
        "languages": [],
        "publisher_platforms": [],
    }
    if resolved_url:
        payload["_resolved_media_url"] = resolved_url
        payload["_resolved_media_type"] = resolved_type or "unknown"
    return payload


class ApifyAdsClient:
    """Run Apify Facebook Ads Scraper and yield ad payloads (Meta-API shape + _resolved_media_url)."""

    def __init__(
        self,
        api_token: str,
        actor_id: str = "apify/facebook-ads-scraper",
        timeout_secs: int = 3600,
    ) -> None:
        self.api_token = api_token
        self.actor_id = actor_id
        self.timeout_secs = timeout_secs

    def run_and_fetch(
        self,
        start_urls: list[str] | None = None,
        max_ads: int | None = None,
    ) -> list[dict[str, Any]]:
        """Run the actor with the given start URLs (Ad Library or page URLs) and return Meta-shaped payloads."""
        try:
            from apify_client import ApifyClient
        except ImportError as e:
            raise ImportError(
                "Install the apify optional dependency: pip install meta-ads-library[apify]"
            ) from e

        client = ApifyClient(self.api_token)
        run_input: dict[str, Any] = {}
        if start_urls:
            run_input["startUrls"] = [{"url": u} for u in start_urls]
        if max_ads is not None:
            run_input["maxAds"] = max_ads

        run = client.actor(self.actor_id).call(run_input=run_input, timeout_secs=self.timeout_secs)
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return []

        items = list(client.dataset(dataset_id).iterate_items())
        return [apify_item_to_meta_payload(item) for item in items]

    def iterate_ads(
        self,
        start_urls: list[str] | None = None,
        max_ads: int | None = None,
    ) -> Iterable[ApifyAdsPage]:
        """Yield one page containing all ads from the actor run (for compatibility with pipeline)."""
        payloads = self.run_and_fetch(start_urls=start_urls, max_ads=max_ads)
        if payloads:
            yield ApifyAdsPage(ads=payloads)


def fetch_dataset_items_from_url(url: str, timeout: float = 60.0) -> list[dict[str, Any]]:
    """Fetch Apify dataset items JSON from a URL and return Meta-shaped payloads (with _resolved_media_url)."""
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    items = data if isinstance(data, list) else [data]
    return [apify_item_to_meta_payload(item) for item in items]


def fetch_dataset_items_from_file(path: Path) -> list[dict[str, Any]]:
    """Load Apify dataset items from a local JSON file and return Meta-shaped payloads."""
    import json
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    items = data if isinstance(data, list) else [data]
    return [apify_item_to_meta_payload(item) for item in items]
