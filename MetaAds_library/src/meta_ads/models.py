from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def uuid_str() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IngestRun(TimestampMixin, Base):
    __tablename__ = "ingest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    query: Mapped[str | None] = mapped_column(String(100))
    countries: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    page_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(20))
    active_status: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    search_type: Mapped[str] = mapped_column(String(32), default="KEYWORD_UNORDERED", nullable=False)
    publisher_platforms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    delivery_date_min: Mapped[str | None] = mapped_column(String(10))
    delivery_date_max: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    total_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_30d_plus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_clusters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_page_cursor: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    raw_ads: Mapped[list["AdRaw"]] = relationship(back_populates="ingest_run")


class AdRaw(TimestampMixin, Base):
    __tablename__ = "ads_raw"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    ingest_run_id: Mapped[str] = mapped_column(ForeignKey("ingest_runs.id", ondelete="CASCADE"), nullable=False)
    meta_ad_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    ingest_run: Mapped[IngestRun] = relationship(back_populates="raw_ads")


class CreativeFingerprint(TimestampMixin, Base):
    __tablename__ = "creative_fingerprints"

    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_meta_ad_id: Mapped[str | None] = mapped_column(ForeignKey("ads.meta_ad_id", ondelete="SET NULL"))
    ad_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    ads: Mapped[list["Ad"]] = relationship(back_populates="fingerprint", foreign_keys="Ad.dedupe_fingerprint")


class Ad(TimestampMixin, Base):
    __tablename__ = "ads"

    meta_ad_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    page_id: Mapped[str | None] = mapped_column(String(64), index=True)
    page_name: Mapped[str | None] = mapped_column(String(255))
    ad_creation_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ad_delivery_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ad_delivery_stop_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ad_snapshot_url: Mapped[str | None] = mapped_column(Text)
    ad_creative_bodies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    ad_creative_link_captions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    ad_creative_link_descriptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    ad_creative_link_titles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    publisher_platforms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    media_type_guess: Mapped[str] = mapped_column(String(20), default="UNKNOWN", nullable=False)
    duration_days: Mapped[float | None] = mapped_column(Float)
    is_running_30d_plus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    dedupe_fingerprint: Mapped[str | None] = mapped_column(
        ForeignKey("creative_fingerprints.fingerprint", ondelete="SET NULL"),
        index=True,
    )

    fingerprint: Mapped[CreativeFingerprint | None] = relationship(
        back_populates="ads",
        foreign_keys=[dedupe_fingerprint],
    )
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="ad")
    analysis_jobs: Mapped[list["AnalysisJob"]] = relationship(back_populates="ad")
    analyses: Mapped[list["AdAnalysis"]] = relationship(back_populates="ad")


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meta_ad_id: Mapped[str] = mapped_column(ForeignKey("ads.meta_ad_id", ondelete="CASCADE"), index=True, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str | None] = mapped_column(Text)
    snapshot_html_path: Mapped[str | None] = mapped_column(Text)
    extracted_preview_path: Mapped[str | None] = mapped_column(Text)
    asset_type: Mapped[str | None] = mapped_column(String(20))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)

    ad: Mapped[Ad] = relationship(back_populates="media_assets")
    transcripts: Mapped[list["VideoTranscript"]] = relationship(back_populates="media_asset")


class AnalysisJob(TimestampMixin, Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meta_ad_id: Mapped[str] = mapped_column(ForeignKey("ads.meta_ad_id", ondelete="CASCADE"), index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(20), default="creative_analysis", nullable=False)
    requested_model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ad: Mapped[Ad] = relationship(back_populates="analysis_jobs")
    analyses: Mapped[list["AdAnalysis"]] = relationship(back_populates="job")


class AdAnalysis(TimestampMixin, Base):
    __tablename__ = "ad_analyses"
    __table_args__ = (UniqueConstraint("analysis_job_id", name="uq_analysis_job_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meta_ad_id: Mapped[str] = mapped_column(ForeignKey("ads.meta_ad_id", ondelete="CASCADE"), index=True, nullable=False)
    analysis_job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(20), default="creative", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_partial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hook: Mapped[str | None] = mapped_column(Text)
    primary_angle: Mapped[str | None] = mapped_column(Text)
    desire: Mapped[str | None] = mapped_column(Text)
    offer: Mapped[str | None] = mapped_column(Text)
    audience: Mapped[str | None] = mapped_column(Text)
    cta: Mapped[str | None] = mapped_column(Text)
    creative_notes: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    proof_elements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    ad: Mapped[Ad] = relationship(back_populates="analyses")
    job: Mapped[AnalysisJob] = relationship(back_populates="analyses")


class VideoTranscript(TimestampMixin, Base):
    __tablename__ = "video_transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    meta_ad_id: Mapped[str] = mapped_column(ForeignKey("ads.meta_ad_id", ondelete="CASCADE"), index=True, nullable=False)
    media_asset_id: Mapped[str | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(20))
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float)
    transcript_text: Mapped[str | None] = mapped_column(Text)
    utterances_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    words_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)

    ad: Mapped[Ad] = relationship()
    media_asset: Mapped[MediaAsset | None] = relationship(back_populates="transcripts")
