from dataclasses import dataclass
from datetime import UTC, datetime

from meta_ads.dedupe import choose_canonical_ad, cluster_ads, compute_creative_fingerprint


@dataclass
class FakeAd:
    meta_ad_id: str
    page_id: str | None
    ad_creation_time: datetime | None
    ad_creative_bodies: list[str]
    ad_creative_link_titles: list[str]
    ad_creative_link_descriptions: list[str]
    duration_days: float | None


def test_same_creative_text_builds_same_fingerprint() -> None:
    ad_a = FakeAd(
        meta_ad_id="a",
        page_id="1",
        ad_creation_time=datetime(2026, 1, 1, tzinfo=UTC),
        ad_creative_bodies=["Buy now!!!"],
        ad_creative_link_titles=["New drop"],
        ad_creative_link_descriptions=["Limited offer"],
        duration_days=35,
    )
    ad_b = FakeAd(
        meta_ad_id="b",
        page_id="1",
        ad_creation_time=datetime(2026, 1, 2, tzinfo=UTC),
        ad_creative_bodies=[" buy now "],
        ad_creative_link_titles=["new drop"],
        ad_creative_link_descriptions=["limited offer"],
        duration_days=31,
    )

    assert compute_creative_fingerprint(ad_a) == compute_creative_fingerprint(ad_b)


def test_longest_running_ad_becomes_canonical() -> None:
    ads = [
        FakeAd("a", "1", datetime(2026, 1, 1, tzinfo=UTC), ["Body"], ["Title"], ["Desc"], 31),
        FakeAd("b", "1", datetime(2026, 1, 3, tzinfo=UTC), ["Body"], ["Title"], ["Desc"], 44),
    ]

    canonical = choose_canonical_ad(ads)
    clusters = cluster_ads(ads)

    assert canonical.meta_ad_id == "b"
    assert clusters[0].canonical_meta_ad_id == "b"
    assert set(clusters[0].ad_ids) == {"a", "b"}
