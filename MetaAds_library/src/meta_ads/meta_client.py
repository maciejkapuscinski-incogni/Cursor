from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

import httpx


DEFAULT_FIELDS = [
    "id",
    "ad_creation_time",
    "ad_creative_bodies",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
    "ad_creative_link_titles",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
    "ad_snapshot_url",
    "languages",
    "page_id",
    "page_name",
    "publisher_platforms",
]


@dataclass(slots=True)
class MetaAdsPage:
    ads: list[dict[str, Any]]
    next_page_url: str | None
    next_cursor: str | None


class MetaAdsClient:
    def __init__(self, access_token: str, api_version: str = "v25.0", timeout: float = 60.0) -> None:
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.timeout = timeout

    def _build_params(
        self,
        query: str | None,
        countries: Iterable[str],
        page_ids: Iterable[str] | None = None,
        media_type: str | None = None,
        active_status: str = "ALL",
        search_type: str = "KEYWORD_UNORDERED",
        publisher_platforms: Iterable[str] | None = None,
        delivery_date_min: str | None = None,
        delivery_date_max: str | None = None,
        after: str | None = None,
    ) -> dict[str, str]:
        params = {
            "access_token": self.access_token,
            "ad_reached_countries": json.dumps(list(countries)),
            "ad_type": "ALL",
            "ad_active_status": active_status,
            "fields": ",".join(DEFAULT_FIELDS),
        }
        if query:
            params["search_terms"] = query
            params["search_type"] = search_type
        if page_ids:
            params["search_page_ids"] = json.dumps(list(page_ids))
        if media_type:
            params["media_type"] = media_type
        if publisher_platforms:
            params["publisher_platforms"] = json.dumps(list(publisher_platforms))
        if delivery_date_min:
            params["ad_delivery_date_min"] = delivery_date_min
        if delivery_date_max:
            params["ad_delivery_date_max"] = delivery_date_max
        if after:
            params["after"] = after
        return params

    def fetch_page(
        self,
        query: str | None,
        countries: Iterable[str],
        page_ids: Iterable[str] | None = None,
        media_type: str | None = None,
        active_status: str = "ALL",
        search_type: str = "KEYWORD_UNORDERED",
        publisher_platforms: Iterable[str] | None = None,
        delivery_date_min: str | None = None,
        delivery_date_max: str | None = None,
        after: str | None = None,
    ) -> MetaAdsPage:
        params = self._build_params(
            query=query,
            countries=countries,
            page_ids=page_ids,
            media_type=media_type,
            active_status=active_status,
            search_type=search_type,
            publisher_platforms=publisher_platforms,
            delivery_date_min=delivery_date_min,
            delivery_date_max=delivery_date_max,
            after=after,
        )

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/ads_archive", params=params)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                error_detail = response.text
                try:
                    payload = response.json()
                    error = payload.get("error") or {}
                    if error:
                        error_detail = json.dumps(error, ensure_ascii=True)
                except ValueError:
                    pass
                raise RuntimeError(f"Meta Ads API request failed: {error_detail}") from exc
            payload = response.json()

        paging = payload.get("paging", {})
        cursors = paging.get("cursors", {})
        return MetaAdsPage(
            ads=payload.get("data", []),
            next_page_url=paging.get("next"),
            next_cursor=cursors.get("after"),
        )

    def iterate_ads(
        self,
        query: str | None,
        countries: Iterable[str],
        page_ids: Iterable[str] | None = None,
        media_type: str | None = None,
        active_status: str = "ALL",
        search_type: str = "KEYWORD_UNORDERED",
        publisher_platforms: Iterable[str] | None = None,
        delivery_date_min: str | None = None,
        delivery_date_max: str | None = None,
        limit_pages: int | None = None,
    ) -> Iterable[MetaAdsPage]:
        after: str | None = None
        pages_fetched = 0

        while True:
            page = self.fetch_page(
                query=query,
                countries=countries,
                page_ids=page_ids,
                media_type=media_type,
                active_status=active_status,
                search_type=search_type,
                publisher_platforms=publisher_platforms,
                delivery_date_min=delivery_date_min,
                delivery_date_max=delivery_date_max,
                after=after,
            )
            if not page.ads:
                break

            yield page

            pages_fetched += 1
            if limit_pages is not None and pages_fetched >= limit_pages:
                break
            if not page.next_cursor:
                break
            after = page.next_cursor
