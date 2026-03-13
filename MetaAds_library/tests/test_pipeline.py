from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from meta_ads.assemblyai_client import TranscriptResult
from meta_ads.media import MediaFetchResult, ResolvedSnapshotMedia
from meta_ads.models import Base, VideoTranscript
from meta_ads.normalize import NormalizedAd
from meta_ads.pipeline import AdsPipeline


class FakeMediaProcessor:
    def __init__(self, result: MediaFetchResult, resolved_url: str = "https://cdn.example.com/creative.mp4") -> None:
        self.result = result
        self.resolved_url = resolved_url

    def resolve_snapshot_media(
        self,
        snapshot_url: str,
        meta_ad_id: str | None = None,
        debug_snapshot_path: Path | None = None,
    ) -> ResolvedSnapshotMedia:
        return ResolvedSnapshotMedia(
            resolved_url=self.resolved_url,
            asset_type="video" if (self.result.asset_type == "video") else "image",
            extracted_url=self.resolved_url,
        )

    def download_media_from_url(
        self,
        meta_ad_id: str,
        media_url: str,
        source_snapshot_url: str,
        extracted_url: str | None = None,
    ) -> MediaFetchResult:
        return self.result

    def fetch_media(self, meta_ad_id: str, snapshot_url: str) -> MediaFetchResult:
        return self.result


def build_normalized_ad() -> NormalizedAd:
    return NormalizedAd(
        meta_ad_id="123",
        page_id="999",
        page_name="Test Brand",
        ad_creation_time=datetime(2026, 1, 1, tzinfo=UTC),
        ad_delivery_start_time=datetime(2026, 1, 1, tzinfo=UTC),
        ad_delivery_stop_time=None,
        ad_snapshot_url="https://example.com/snapshot",
        ad_creative_bodies=["Strong hook"],
        ad_creative_link_captions=["caption"],
        ad_creative_link_descriptions=["desc"],
        ad_creative_link_titles=["title"],
        languages=["en"],
        publisher_platforms=["FACEBOOK"],
        media_type_guess="VIDEO",
        duration_days=35.0,
        is_running_30d_plus=True,
    )


def test_ingest_media_and_transcript_records_skipped_when_no_assemblyai() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    media_result = MediaFetchResult(
        status="downloaded",
        source_url="https://example.com/snapshot",
        resolved_media_url="https://cdn.example.com/creative.mp4",
        local_path="/tmp/creative.mp4",
        asset_type="video",
        mime_type="video/mp4",
    )
    pipeline = AdsPipeline(
        meta_client=None,  # type: ignore[arg-type]
        media_processor=FakeMediaProcessor(media_result),  # type: ignore[arg-type]
        session_factory=session_factory,
        assemblyai_client=None,
        nexos_client=None,
    )

    with session_factory() as session:
        returned_media, transcript = pipeline._ingest_media_and_transcript(session, build_normalized_ad())
        stored = session.query(VideoTranscript).filter(VideoTranscript.meta_ad_id == "123").first()

    assert returned_media is not None
    assert returned_media.local_path == "/tmp/creative.mp4"
    assert transcript is not None
    assert transcript.status == "skipped"
    assert stored is not None
    assert stored.status == "skipped"
    assert stored.last_error == "ASSEMBLYAI_API_KEY is not configured."


def test_export_ads_csv_includes_media_and_transcript_fields(tmp_path: Path, monkeypatch) -> None:
    pipeline = AdsPipeline(
        meta_client=None,  # type: ignore[arg-type]
        media_processor=None,  # type: ignore[arg-type]
        session_factory=None,
        assemblyai_client=None,
        nexos_client=None,
    )
    monkeypatch.chdir(tmp_path)
    ad = build_normalized_ad()
    media_by_ad_id = {
        "123": MediaFetchResult(
            status="downloaded",
            source_url="https://example.com/snapshot",
            resolved_media_url="https://cdn.example.com/creative.mp4",
            local_path="media-cache/123/creative.mp4",
            extracted_preview_path="media-cache/123/creative_firstframe.jpg",
            asset_type="video",
            mime_type="video/mp4",
        )
    }
    transcript_by_ad_id = {
        "123": TranscriptResult(
            status="completed",
            provider="assemblyai",
            transcript_text="Hello world",
            transcript_json={},
            utterances=[
                {"start": 0, "text": "Hello world"},
                {"start": 2150, "text": "Second line"},
            ],
            words=[],
            language_code="en",
            audio_duration=3.5,
        )
    }

    csv_path = pipeline._export_ads_csv(
        run_id="run-1",
        ads=[ad],
        fingerprint_by_ad_id={"123": "abc123"},
        media_by_ad_id=media_by_ad_id,
        transcript_by_ad_id=transcript_by_ad_id,
    )

    content = (tmp_path / csv_path).read_text(encoding="utf-8")

    assert "media_local_path" in content
    assert "resolved_media_url" in content
    assert "transcript_status" in content
    assert "transcript_timestamps_text" in content
    assert "https://cdn.example.com/creative.mp4" in content
    assert "media-cache/123/creative.mp4" in content
    assert "Hello world" in content
    assert "[0.00s] Hello world | [2.15s] Second line" in content
