from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session, sessionmaker

from meta_ads.assemblyai_client import AssemblyAIClient, TranscriptResult
from meta_ads.dedupe import cluster_ads
from meta_ads.media import MediaFetchResult, MediaProcessor, ResolvedSnapshotMedia
from meta_ads.meta_client import MetaAdsClient
from meta_ads.models import Ad, AdAnalysis, AdRaw, AnalysisJob, CreativeFingerprint, IngestRun, MediaAsset, VideoTranscript
from meta_ads.nexos_client import NexosAnalysisClient
from meta_ads.normalize import NormalizedAd, normalize_ad


@dataclass(slots=True)
class PipelineResult:
    ingest_run_id: str
    total_fetched: int
    total_30d_plus: int
    total_clusters: int
    analyzed_ads: int
    csv_path: str


class AdsPipeline:
    def __init__(
        self,
        meta_client: MetaAdsClient,
        media_processor: MediaProcessor,
        session_factory: sessionmaker[Session] | None = None,
        assemblyai_client: AssemblyAIClient | None = None,
        nexos_client: NexosAnalysisClient | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.meta_client = meta_client
        self.media_processor = media_processor
        self.assemblyai_client = assemblyai_client
        self.nexos_client = nexos_client

    @staticmethod
    def _failed_transcript_result(message: str, status: str = "failed") -> TranscriptResult:
        return TranscriptResult(
            status=status,
            provider="assemblyai",
            transcript_text=None,
            transcript_json={},
            utterances=[],
            words=[],
            language_code=None,
            audio_duration=None,
            last_error=message,
        )

    @staticmethod
    def _media_result_from_asset(asset: MediaAsset) -> MediaFetchResult:
        meta = asset.metadata_json or {}
        resolved = meta.get("resolved_media_url")
        extracted = meta.get("extracted_media_url")
        return MediaFetchResult(
            status=asset.status,
            source_url=asset.source_url,
            resolved_media_url=str(resolved) if resolved else None,
            extracted_media_url=str(extracted) if extracted else None,
            local_path=asset.local_path,
            snapshot_html_path=asset.snapshot_html_path,
            extracted_preview_path=asset.extracted_preview_path,
            asset_type=asset.asset_type,
            mime_type=asset.mime_type,
            metadata_json=asset.metadata_json,
            last_error=asset.last_error,
        )

    @staticmethod
    def _transcript_result_from_record(record: VideoTranscript) -> TranscriptResult:
        return TranscriptResult(
            status=record.status,
            provider=record.provider,
            transcript_text=record.transcript_text,
            transcript_json=record.raw_response,
            utterances=record.utterances_json,
            words=record.words_json,
            language_code=record.language_code,
            audio_duration=record.audio_duration_seconds,
            last_error=record.last_error,
        )

    @staticmethod
    def _format_transcript_utterances(utterances: list[dict[str, object]]) -> str:
        formatted: list[str] = []
        for utterance in utterances:
            text = str(utterance.get("text") or "").strip()
            if not text:
                continue
            start_value = utterance.get("start", 0)
            try:
                seconds = float(start_value) / 1000
            except (TypeError, ValueError):
                seconds = 0.0
            formatted.append(f"[{seconds:0.2f}s] {text}")
        return " | ".join(formatted)

    def _export_ads_csv(
        self,
        run_id: str,
        ads: Iterable[NormalizedAd],
        fingerprint_by_ad_id: dict[str, str],
        media_by_ad_id: dict[str, MediaFetchResult],
        transcript_by_ad_id: dict[str, TranscriptResult],
    ) -> str:
        export_dir = Path("exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        csv_path = export_dir / f"{run_id}.csv"
        fieldnames = [
            "meta_ad_id",
            "page_id",
            "page_name",
            "ad_creation_time",
            "ad_delivery_start_time",
            "ad_delivery_stop_time",
            "ad_snapshot_url",
            "ad_creative_bodies",
            "ad_creative_link_captions",
            "ad_creative_link_descriptions",
            "ad_creative_link_titles",
            "languages",
            "publisher_platforms",
            "media_type_guess",
            "duration_days",
            "is_running_30d_plus",
            "dedupe_fingerprint",
            "media_status",
            "media_asset_type",
            "media_mime_type",
            "video_url",
            "resolved_media_url",
            "extracted_media_url",
            "media_local_path",
            "media_snapshot_html_path",
            "media_preview_path",
            "media_last_error",
            "transcript_status",
            "transcript_language_code",
            "transcript_audio_duration_seconds",
            "transcript_text",
            "transcript_timestamps_text",
            "transcript_utterances_json",
            "transcript_words_json",
            "transcript_last_error",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for ad in ads:
                media_result = media_by_ad_id.get(ad.meta_ad_id)
                transcript_result = transcript_by_ad_id.get(ad.meta_ad_id)
                writer.writerow(
                    {
                        "meta_ad_id": ad.meta_ad_id,
                        "page_id": ad.page_id,
                        "page_name": ad.page_name,
                        "ad_creation_time": ad.ad_creation_time.isoformat() if ad.ad_creation_time else "",
                        "ad_delivery_start_time": ad.ad_delivery_start_time.isoformat() if ad.ad_delivery_start_time else "",
                        "ad_delivery_stop_time": ad.ad_delivery_stop_time.isoformat() if ad.ad_delivery_stop_time else "",
                        "ad_snapshot_url": ad.ad_snapshot_url or "",
                        "ad_creative_bodies": json.dumps(ad.ad_creative_bodies, ensure_ascii=False),
                        "ad_creative_link_captions": json.dumps(ad.ad_creative_link_captions, ensure_ascii=False),
                        "ad_creative_link_descriptions": json.dumps(ad.ad_creative_link_descriptions, ensure_ascii=False),
                        "ad_creative_link_titles": json.dumps(ad.ad_creative_link_titles, ensure_ascii=False),
                        "languages": json.dumps(ad.languages, ensure_ascii=False),
                        "publisher_platforms": json.dumps(ad.publisher_platforms, ensure_ascii=False),
                        "media_type_guess": ad.media_type_guess,
                        "duration_days": ad.duration_days if ad.duration_days is not None else "",
                        "is_running_30d_plus": ad.is_running_30d_plus,
                        "dedupe_fingerprint": fingerprint_by_ad_id.get(ad.meta_ad_id, ""),
                        "media_status": media_result.status if media_result else "",
                        "media_asset_type": media_result.asset_type if media_result else "",
                        "media_mime_type": media_result.mime_type if media_result else "",
                        "video_url": (media_result.resolved_media_url or media_result.extracted_media_url) if media_result else "",
                        "resolved_media_url": media_result.resolved_media_url if media_result else "",
                        "extracted_media_url": media_result.extracted_media_url if media_result else "",
                        "media_local_path": media_result.local_path if media_result else "",
                        "media_snapshot_html_path": media_result.snapshot_html_path if media_result else "",
                        "media_preview_path": media_result.extracted_preview_path if media_result else "",
                        "media_last_error": media_result.last_error if media_result else "",
                        "transcript_status": transcript_result.status if transcript_result else "",
                        "transcript_language_code": transcript_result.language_code if transcript_result else "",
                        "transcript_audio_duration_seconds": transcript_result.audio_duration if transcript_result else "",
                        "transcript_text": transcript_result.transcript_text if transcript_result else "",
                        "transcript_timestamps_text": self._format_transcript_utterances(transcript_result.utterances) if transcript_result else "",
                        "transcript_utterances_json": json.dumps(transcript_result.utterances, ensure_ascii=False) if transcript_result else "",
                        "transcript_words_json": json.dumps(transcript_result.words, ensure_ascii=False) if transcript_result else "",
                        "transcript_last_error": transcript_result.last_error if transcript_result else "",
                    }
                )
        return str(csv_path)

    def _create_run(
        self,
        query: str | None,
        countries: Iterable[str],
        page_ids: Iterable[str],
        media_type: str | None,
        active_status: str,
        search_type: str,
        publisher_platforms: Iterable[str],
        delivery_date_min: str | None,
        delivery_date_max: str | None,
    ) -> str:
        with self.session_factory() as session:
            run = IngestRun(
                query=query,
                countries=list(countries),
                page_ids=list(page_ids),
                media_type=media_type,
                active_status=active_status,
                search_type=search_type,
                publisher_platforms=list(publisher_platforms),
                delivery_date_min=delivery_date_min,
                delivery_date_max=delivery_date_max,
                status="queued",
            )
            session.add(run)
            session.commit()
            return run.id

    def _set_run_status(self, run_id: str, status: str, **updates: object) -> None:
        with self.session_factory() as session:
            run = session.get(IngestRun, run_id)
            if run is None:
                return
            run.status = status
            for key, value in updates.items():
                setattr(run, key, value)
            if status in {"completed", "failed"}:
                run.completed_at = datetime.now(UTC)
            session.commit()

    def _upsert_ad(self, session: Session, normalized: NormalizedAd) -> None:
        ad = session.get(Ad, normalized.meta_ad_id)
        if ad is None:
            ad = Ad(meta_ad_id=normalized.meta_ad_id)
            session.add(ad)

        ad.page_id = normalized.page_id
        ad.page_name = normalized.page_name
        ad.ad_creation_time = normalized.ad_creation_time
        ad.ad_delivery_start_time = normalized.ad_delivery_start_time
        ad.ad_delivery_stop_time = normalized.ad_delivery_stop_time
        ad.ad_snapshot_url = normalized.ad_snapshot_url
        ad.ad_creative_bodies = normalized.ad_creative_bodies
        ad.ad_creative_link_captions = normalized.ad_creative_link_captions
        ad.ad_creative_link_descriptions = normalized.ad_creative_link_descriptions
        ad.ad_creative_link_titles = normalized.ad_creative_link_titles
        ad.languages = normalized.languages
        ad.publisher_platforms = normalized.publisher_platforms
        ad.media_type_guess = normalized.media_type_guess
        ad.duration_days = normalized.duration_days
        ad.is_running_30d_plus = normalized.is_running_30d_plus

    def _store_fingerprint_clusters(self, clusters: list, session: Session) -> None:
        for cluster in clusters:
            fingerprint = session.get(CreativeFingerprint, cluster.fingerprint)
            if fingerprint is None:
                fingerprint = CreativeFingerprint(fingerprint=cluster.fingerprint)
                session.add(fingerprint)
            fingerprint.canonical_meta_ad_id = cluster.canonical_meta_ad_id
            fingerprint.ad_count = len(cluster.ad_ids)
            for ad_id in cluster.ad_ids:
                ad = session.get(Ad, ad_id)
                if ad:
                    ad.dedupe_fingerprint = cluster.fingerprint

    def _upsert_media_asset(self, session: Session, meta_ad_id: str, media_result: MediaFetchResult) -> MediaAsset:
        existing = session.query(MediaAsset).filter(MediaAsset.meta_ad_id == meta_ad_id).first()
        asset = existing or MediaAsset(meta_ad_id=meta_ad_id, source_url=media_result.source_url)
        if existing is None:
            session.add(asset)
        asset.source_url = media_result.source_url
        asset.local_path = media_result.local_path
        asset.snapshot_html_path = media_result.snapshot_html_path
        asset.extracted_preview_path = media_result.extracted_preview_path
        asset.asset_type = media_result.asset_type
        asset.mime_type = media_result.mime_type
        asset.status = media_result.status
        asset.metadata_json = media_result.metadata_json
        asset.last_error = media_result.last_error
        return asset

    def _store_transcript(
        self,
        session: Session,
        meta_ad_id: str,
        media_asset_id: str | None,
        transcript: TranscriptResult,
    ) -> VideoTranscript:
        existing = session.query(VideoTranscript).filter(VideoTranscript.meta_ad_id == meta_ad_id).first()
        record = existing or VideoTranscript(meta_ad_id=meta_ad_id, provider=transcript.provider)
        if existing is None:
            session.add(record)
        record.media_asset_id = media_asset_id
        record.provider = transcript.provider
        record.status = transcript.status
        record.language_code = transcript.language_code
        record.audio_duration_seconds = transcript.audio_duration
        record.transcript_text = transcript.transcript_text
        record.utterances_json = transcript.utterances
        record.words_json = transcript.words
        record.raw_response = transcript.transcript_json
        record.last_error = transcript.last_error
        return record

    def _ingest_media_and_transcript(
        self,
        session: Session | None,
        normalized: NormalizedAd,
    ) -> tuple[MediaFetchResult | None, TranscriptResult | None]:
        media_result: MediaFetchResult | None = None
        transcript_result: TranscriptResult | None = None
        media_asset: MediaAsset | None = None
        snapshot_url = normalized.ad_snapshot_url or ""

        # Apify (or other sources) can provide the media URL directly; skip snapshot fetch
        if normalized.pre_resolved_media_url:
            resolved = ResolvedSnapshotMedia(
                resolved_url=normalized.pre_resolved_media_url,
                asset_type=normalized.pre_resolved_media_type or "video",
                extracted_url=normalized.pre_resolved_media_url,
            )
        elif not snapshot_url:
            return None, None
        else:
            try:
                resolved = self.media_processor.resolve_snapshot_media(snapshot_url, meta_ad_id=normalized.meta_ad_id)
            except Exception as exc:  # noqa: BLE001
                media_result = MediaFetchResult(
                    status="media_fetch_failed",
                    source_url=snapshot_url,
                    last_error=str(exc),
                )
                if session is not None:
                    self._upsert_media_asset(session, normalized.meta_ad_id, media_result)
                    session.commit()
                return media_result, None

        if not resolved.resolved_url:
            media_result = MediaFetchResult(
                status="media_fetch_failed",
                source_url=snapshot_url,
                snapshot_html_path=resolved.snapshot_html_path,
                last_error="No media URL could be extracted from the snapshot page.",
            )
            if session is not None:
                self._upsert_media_asset(session, normalized.meta_ad_id, media_result)
                session.commit()
            return media_result, None

        is_video = resolved.asset_type == "video"
        if is_video and self.assemblyai_client is not None:
            # Download video first; then transcribe by uploading the local file to AssemblyAI.
            # Facebook CDN URLs often return 400 when AssemblyAI tries to fetch them (auth/blocking),
            # so we upload our downloaded file instead of passing the CDN URL.
            try:
                media_result = self.media_processor.download_media_from_url(
                    normalized.meta_ad_id,
                    resolved.resolved_url,
                    snapshot_url,
                    resolved.extracted_url,
                )
            except Exception as exc:  # noqa: BLE001
                media_result = MediaFetchResult(
                    status="media_fetch_failed",
                    source_url=snapshot_url,
                    resolved_media_url=resolved.resolved_url,
                    extracted_media_url=resolved.extracted_url or resolved.resolved_url,
                    last_error=str(exc),
                    metadata_json={
                        "resolved_media_url": resolved.resolved_url,
                        "extracted_media_url": resolved.extracted_url or resolved.resolved_url,
                    },
                )
            try:
                if media_result.local_path:
                    transcript_result = self.assemblyai_client.transcribe_video(media_result.local_path)
                else:
                    transcript_result = self.assemblyai_client.transcribe_from_url(resolved.resolved_url)
            except Exception as exc:  # noqa: BLE001
                transcript_result = self._failed_transcript_result(str(exc))
        elif is_video and self.assemblyai_client is None:
            transcript_result = self._failed_transcript_result(
                "ASSEMBLYAI_API_KEY is not configured.",
                status="skipped",
            )
            try:
                media_result = self.media_processor.download_media_from_url(
                    normalized.meta_ad_id,
                    resolved.resolved_url,
                    snapshot_url,
                    resolved.extracted_url,
                )
            except Exception as exc:  # noqa: BLE001
                media_result = MediaFetchResult(
                    status="media_fetch_failed",
                    source_url=snapshot_url,
                    resolved_media_url=resolved.resolved_url,
                    extracted_media_url=resolved.extracted_url or resolved.resolved_url,
                    last_error=str(exc),
                    metadata_json={
                        "resolved_media_url": resolved.resolved_url,
                        "extracted_media_url": resolved.extracted_url or resolved.resolved_url,
                    },
                )
        else:
            # Image (or unknown): just download
            try:
                media_result = self.media_processor.download_media_from_url(
                    normalized.meta_ad_id,
                    resolved.resolved_url,
                    snapshot_url,
                    resolved.extracted_url,
                )
            except Exception as exc:  # noqa: BLE001
                media_result = MediaFetchResult(
                    status="media_fetch_failed",
                    source_url=snapshot_url,
                    resolved_media_url=resolved.resolved_url,
                    extracted_media_url=resolved.extracted_url or resolved.resolved_url,
                    last_error=str(exc),
                    metadata_json={
                        "resolved_media_url": resolved.resolved_url,
                        "extracted_media_url": resolved.extracted_url or resolved.resolved_url,
                    },
                )

        if session is not None and media_result is not None:
            media_asset = self._upsert_media_asset(session, normalized.meta_ad_id, media_result)
            session.commit()

        if session is not None and transcript_result is not None:
            self._store_transcript(
                session,
                meta_ad_id=normalized.meta_ad_id,
                media_asset_id=media_asset.id if media_asset else None,
                transcript=transcript_result,
            )
            session.commit()

        return media_result, transcript_result

    def _analyze_canonical_ads(self, canonical_ids: list[str]) -> int:
        if self.nexos_client is None:
            return 0

        analyzed_count = 0
        for meta_ad_id in canonical_ids:
            with self.session_factory() as session:
                ad = session.get(Ad, meta_ad_id)
                if ad is None:
                    continue

                job = AnalysisJob(meta_ad_id=meta_ad_id, requested_model=self.nexos_client.model, status="running")
                session.add(job)
                session.commit()

                media_result = None
                transcript_result = None
                try:
                    media_asset = session.query(MediaAsset).filter(MediaAsset.meta_ad_id == meta_ad_id).first()
                    transcript_record = session.query(VideoTranscript).filter(VideoTranscript.meta_ad_id == meta_ad_id).first()
                    if media_asset is not None:
                        media_result = self._media_result_from_asset(media_asset)
                    if transcript_record is not None:
                        transcript_result = self._transcript_result_from_record(transcript_record)

                    analysis = self.nexos_client.analyze_creative(
                        ad,
                        media_result=media_result,
                        transcript=transcript_result,
                    )
                    record = AdAnalysis(
                        meta_ad_id=meta_ad_id,
                        analysis_job_id=job.id,
                        analysis_type="creative",
                        model_name=self.nexos_client.model,
                        is_partial=bool(
                            (media_result and media_result.status != "downloaded")
                            or (transcript_result and transcript_result.status != "completed")
                        ),
                        hook=analysis.get("hook"),
                        primary_angle=analysis.get("primary_angle"),
                        desire=analysis.get("desire"),
                        offer=analysis.get("offer"),
                        audience=analysis.get("audience"),
                        cta=analysis.get("cta"),
                        creative_notes=analysis.get("creative_notes"),
                        confidence=float(analysis["confidence"]) if analysis.get("confidence") is not None else None,
                        proof_elements=list(analysis.get("proof_elements") or []),
                        raw_response=analysis.get("raw_response") or {},
                    )
                    session.add(record)
                    job.status = "completed"
                    job.completed_at = datetime.now(UTC)
                    session.commit()
                    analyzed_count += 1
                except Exception as exc:  # noqa: BLE001
                    job.status = "failed"
                    job.error_message = str(exc)
                    job.completed_at = datetime.now(UTC)
                    session.commit()
        return analyzed_count

    def run(
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
        analyze: bool = True,
        save_to_db: bool = True,
        ads_pages: Iterable[object] | None = None,
    ) -> PipelineResult:
        """Run the pipeline. If ads_pages is provided (e.g. from Apify), use it instead of Meta API."""
        page_ids = list(page_ids or [])
        countries = list(countries)
        publisher_platforms = list(publisher_platforms or [])

        if ads_pages is None and not query and not page_ids:
            raise ValueError("Provide either a search query or one or more page IDs.")
        if ads_pages is None and not countries:
            raise ValueError("At least one reached country must be provided.")
        if save_to_db and self.session_factory is None:
            raise ValueError("Pipeline was built without a database; use save_to_db=False (e.g. --csv-only).")

        if save_to_db:
            run_id = self._create_run(
                query=query,
                countries=countries,
                page_ids=page_ids,
                media_type=media_type,
                active_status=active_status,
                search_type=search_type,
                publisher_platforms=publisher_platforms,
                delivery_date_min=delivery_date_min,
                delivery_date_max=delivery_date_max,
            )
            self._set_run_status(run_id, "running")
        else:
            run_id = "csv-" + str(uuid.uuid4())[:8]

        normalized_ads: dict[str, NormalizedAd] = {}
        media_by_ad_id: dict[str, MediaFetchResult] = {}
        transcript_by_ad_id: dict[str, TranscriptResult] = {}
        total_fetched = 0
        analyzed_ads = 0
        last_cursor: str | None = None

        try:
            page_iter = ads_pages if ads_pages is not None else self.meta_client.iterate_ads(
                query=query,
                countries=countries,
                page_ids=page_ids,
                media_type=media_type,
                active_status=active_status,
                search_type=search_type,
                publisher_platforms=publisher_platforms,
                delivery_date_min=delivery_date_min,
                delivery_date_max=delivery_date_max,
                limit_pages=limit_pages,
            )
            for page in page_iter:
                last_cursor = page.next_cursor
                if save_to_db:
                    with self.session_factory() as session:
                        for payload in page.ads:
                            normalized = normalize_ad(payload, requested_media_type=media_type)
                            normalized_ads[normalized.meta_ad_id] = normalized
                            session.add(AdRaw(ingest_run_id=run_id, meta_ad_id=normalized.meta_ad_id, payload=payload))
                            self._upsert_ad(session, normalized)
                            session.commit()

                            media_result, transcript_result = self._ingest_media_and_transcript(session, normalized)
                            if media_result is not None:
                                media_by_ad_id[normalized.meta_ad_id] = media_result
                            if transcript_result is not None:
                                transcript_by_ad_id[normalized.meta_ad_id] = transcript_result
                            total_fetched += 1
                    self._set_run_status(run_id, "running", total_fetched=total_fetched, next_page_cursor=last_cursor)
                else:
                    for payload in page.ads:
                        normalized = normalize_ad(payload, requested_media_type=media_type)
                        normalized_ads[normalized.meta_ad_id] = normalized
                        media_result, transcript_result = self._ingest_media_and_transcript(None, normalized)
                        if media_result is not None:
                            media_by_ad_id[normalized.meta_ad_id] = media_result
                        if transcript_result is not None:
                            transcript_by_ad_id[normalized.meta_ad_id] = transcript_result
                        total_fetched += 1

            thirty_day_ads = [ad for ad in normalized_ads.values() if ad.is_running_30d_plus]
            clusters = cluster_ads(thirty_day_ads)
            fingerprint_by_ad_id = {
                ad_id: cluster.fingerprint
                for cluster in clusters
                for ad_id in cluster.ad_ids
            }

            if save_to_db:
                with self.session_factory() as session:
                    self._store_fingerprint_clusters(clusters, session)
                    session.commit()

            canonical_ids = [cluster.canonical_meta_ad_id for cluster in clusters]
            if analyze and save_to_db:
                analyzed_ads = self._analyze_canonical_ads(canonical_ids)
            csv_path = self._export_ads_csv(
                run_id=run_id,
                ads=normalized_ads.values(),
                fingerprint_by_ad_id=fingerprint_by_ad_id,
                media_by_ad_id=media_by_ad_id,
                transcript_by_ad_id=transcript_by_ad_id,
            )

            if save_to_db:
                self._set_run_status(
                    run_id,
                    "completed",
                    total_fetched=total_fetched,
                    total_30d_plus=len(thirty_day_ads),
                    total_clusters=len(clusters),
                    next_page_cursor=last_cursor,
                )
            return PipelineResult(
                ingest_run_id=run_id,
                total_fetched=total_fetched,
                total_30d_plus=len(thirty_day_ads),
                total_clusters=len(clusters),
                analyzed_ads=analyzed_ads,
                csv_path=csv_path,
            )
        except Exception as exc:  # noqa: BLE001
            if save_to_db:
                self._set_run_status(
                    run_id,
                    "failed",
                    total_fetched=total_fetched,
                    next_page_cursor=last_cursor,
                    error_message=str(exc),
                )
            raise
