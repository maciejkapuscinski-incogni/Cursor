from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol


class AdLike(Protocol):
    meta_ad_id: str
    page_id: str | None
    ad_creation_time: datetime | None
    ad_creative_bodies: list[str]
    ad_creative_link_titles: list[str]
    ad_creative_link_descriptions: list[str]
    duration_days: float | None


def normalize_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value).strip().lower()
    return re.sub(r"[^\w\s]", "", collapsed)


def compute_creative_fingerprint(ad: AdLike) -> str:
    chunks = [
        normalize_text(" ".join(ad.ad_creative_bodies)),
        normalize_text(" ".join(ad.ad_creative_link_titles)),
        normalize_text(" ".join(ad.ad_creative_link_descriptions)),
        normalize_text(ad.page_id or ""),
    ]
    payload = "|".join(chunks)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def choose_canonical_ad(ads: Iterable[AdLike]) -> AdLike:
    candidates = list(ads)
    if not candidates:
        raise ValueError("At least one ad is required to select a canonical record.")
    return sorted(
        candidates,
        key=lambda ad: (
            -(ad.duration_days or 0),
            ad.ad_creation_time or datetime.min,
            ad.meta_ad_id,
        ),
    )[0]


@dataclass(slots=True)
class DedupeCluster:
    fingerprint: str
    canonical_meta_ad_id: str
    ad_ids: list[str]


def cluster_ads(ads: Iterable[AdLike]) -> list[DedupeCluster]:
    groups: dict[str, list[AdLike]] = defaultdict(list)
    for ad in ads:
        fingerprint = compute_creative_fingerprint(ad)
        groups[fingerprint].append(ad)

    clusters: list[DedupeCluster] = []
    for fingerprint, items in groups.items():
        canonical = choose_canonical_ad(items)
        clusters.append(
            DedupeCluster(
                fingerprint=fingerprint,
                canonical_meta_ad_id=canonical.meta_ad_id,
                ad_ids=[item.meta_ad_id for item in items],
            )
        )
    return clusters
