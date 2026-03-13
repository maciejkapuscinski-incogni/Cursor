"""initial schema

Revision ID: 20260311_000001
Revises:
Create Date: 2026-03-11 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("query", sa.String(length=100), nullable=True),
        sa.Column("countries", sa.JSON(), nullable=False),
        sa.Column("page_ids", sa.JSON(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=True),
        sa.Column("active_status", sa.String(length=20), nullable=False),
        sa.Column("search_type", sa.String(length=32), nullable=False),
        sa.Column("publisher_platforms", sa.JSON(), nullable=False),
        sa.Column("delivery_date_min", sa.String(length=10), nullable=True),
        sa.Column("delivery_date_max", sa.String(length=10), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_fetched", sa.Integer(), nullable=False),
        sa.Column("total_30d_plus", sa.Integer(), nullable=False),
        sa.Column("total_clusters", sa.Integer(), nullable=False),
        sa.Column("next_page_cursor", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ads",
        sa.Column("meta_ad_id", sa.String(length=64), primary_key=True),
        sa.Column("page_id", sa.String(length=64), nullable=True),
        sa.Column("page_name", sa.String(length=255), nullable=True),
        sa.Column("ad_creation_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ad_delivery_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ad_delivery_stop_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ad_snapshot_url", sa.Text(), nullable=True),
        sa.Column("ad_creative_bodies", sa.JSON(), nullable=False),
        sa.Column("ad_creative_link_captions", sa.JSON(), nullable=False),
        sa.Column("ad_creative_link_descriptions", sa.JSON(), nullable=False),
        sa.Column("ad_creative_link_titles", sa.JSON(), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("publisher_platforms", sa.JSON(), nullable=False),
        sa.Column("media_type_guess", sa.String(length=20), nullable=False),
        sa.Column("duration_days", sa.Float(), nullable=True),
        sa.Column("is_running_30d_plus", sa.Boolean(), nullable=False),
        sa.Column("dedupe_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "creative_fingerprints",
        sa.Column("fingerprint", sa.String(length=64), primary_key=True),
        sa.Column("canonical_meta_ad_id", sa.String(length=64), nullable=True),
        sa.Column("ad_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_meta_ad_id"], ["ads.meta_ad_id"], ondelete="SET NULL"),
    )

    op.create_foreign_key(
        "fk_ads_dedupe_fingerprint",
        "ads",
        "creative_fingerprints",
        ["dedupe_fingerprint"],
        ["fingerprint"],
        ondelete="SET NULL",
    )

    op.create_table(
        "ads_raw",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ingest_run_id", sa.String(length=36), nullable=False),
        sa.Column("meta_ad_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ingest_run_id"], ["ingest_runs.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("meta_ad_id", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("snapshot_html_path", sa.Text(), nullable=True),
        sa.Column("extracted_preview_path", sa.Text(), nullable=True),
        sa.Column("asset_type", sa.String(length=20), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["meta_ad_id"], ["ads.meta_ad_id"], ondelete="CASCADE"),
    )

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("meta_ad_id", sa.String(length=64), nullable=False),
        sa.Column("job_type", sa.String(length=20), nullable=False),
        sa.Column("requested_model", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["meta_ad_id"], ["ads.meta_ad_id"], ondelete="CASCADE"),
    )

    op.create_table(
        "ad_analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("meta_ad_id", sa.String(length=64), nullable=False),
        sa.Column("analysis_job_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_type", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("is_partial", sa.Boolean(), nullable=False),
        sa.Column("hook", sa.Text(), nullable=True),
        sa.Column("primary_angle", sa.Text(), nullable=True),
        sa.Column("desire", sa.Text(), nullable=True),
        sa.Column("offer", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("cta", sa.Text(), nullable=True),
        sa.Column("creative_notes", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("proof_elements", sa.JSON(), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meta_ad_id"], ["ads.meta_ad_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("analysis_job_id", name="uq_analysis_job_id"),
    )

    op.create_table(
        "video_transcripts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("meta_ad_id", sa.String(length=64), nullable=False),
        sa.Column("media_asset_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("language_code", sa.String(length=20), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("utterances_json", sa.JSON(), nullable=False),
        sa.Column("words_json", sa.JSON(), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["meta_ad_id"], ["ads.meta_ad_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_ads_page_id", "ads", ["page_id"])
    op.create_index("ix_ads_start_time", "ads", ["ad_delivery_start_time"])
    op.create_index("ix_ads_is_running_30d_plus", "ads", ["is_running_30d_plus"])
    op.create_index("ix_ads_dedupe_fingerprint", "ads", ["dedupe_fingerprint"])
    op.create_index("ix_ads_raw_meta_ad_id", "ads_raw", ["meta_ad_id"])
    op.create_index("ix_media_assets_meta_ad_id", "media_assets", ["meta_ad_id"])
    op.create_index("ix_analysis_jobs_meta_ad_id", "analysis_jobs", ["meta_ad_id"])
    op.create_index("ix_ad_analyses_meta_ad_id", "ad_analyses", ["meta_ad_id"])
    op.create_index("ix_video_transcripts_meta_ad_id", "video_transcripts", ["meta_ad_id"])
    op.create_index("ix_video_transcripts_media_asset_id", "video_transcripts", ["media_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_ad_analyses_meta_ad_id", table_name="ad_analyses")
    op.drop_index("ix_analysis_jobs_meta_ad_id", table_name="analysis_jobs")
    op.drop_index("ix_media_assets_meta_ad_id", table_name="media_assets")
    op.drop_index("ix_video_transcripts_media_asset_id", table_name="video_transcripts")
    op.drop_index("ix_video_transcripts_meta_ad_id", table_name="video_transcripts")
    op.drop_index("ix_ads_raw_meta_ad_id", table_name="ads_raw")
    op.drop_index("ix_ads_dedupe_fingerprint", table_name="ads")
    op.drop_index("ix_ads_is_running_30d_plus", table_name="ads")
    op.drop_index("ix_ads_start_time", table_name="ads")
    op.drop_index("ix_ads_page_id", table_name="ads")
    op.drop_table("ad_analyses")
    op.drop_table("analysis_jobs")
    op.drop_table("video_transcripts")
    op.drop_table("media_assets")
    op.drop_table("ads_raw")
    op.drop_constraint("fk_ads_dedupe_fingerprint", "ads", type_="foreignkey")
    op.drop_table("creative_fingerprints")
    op.drop_table("ads")
    op.drop_table("ingest_runs")
