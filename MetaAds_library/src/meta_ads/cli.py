from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode
from typing import Annotated

import typer

from meta_ads.apify_client import (
    ApifyAdsPage,
    ApifyAdsClient,
    apify_item_to_meta_payload,
    fetch_dataset_items_from_file,
    fetch_dataset_items_from_url,
    load_and_validate_apify_from_url,
    load_and_validate_apify_json,
)
from meta_ads.assemblyai_client import AssemblyAIClient
from meta_ads.config import get_settings
from meta_ads.db import create_db_engine, create_session_factory
from meta_ads.media import MediaProcessor
from meta_ads.meta_client import MetaAdsClient
from meta_ads.models import Base
from meta_ads.nexos_client import NexosAnalysisClient
from meta_ads.pipeline import AdsPipeline


class _DummyMetaClient:
    """Placeholder when pipeline is driven only by Apify JSON file (no Meta API)."""

    def iterate_ads(self, *args: object, **kwargs: object):
        return iter([])


app = typer.Typer(help="Meta Ads Library bulk ingestion and analysis CLI.")


def _build_apify_start_urls(
    query: str | None,
    page_ids: list[str],
    countries: list[str],
    media_type: str | None,
    active_status: str,
) -> list[str]:
    """Build Meta Ad Library URLs for Apify actor input."""
    base = "https://www.facebook.com/ads/library/?"
    params = {
        "active_status": "active" if active_status == "ACTIVE" else "inactive" if active_status == "INACTIVE" else "all",
        "ad_type": "all",
        "country": countries[0] if countries else "ALL",
        "media_type": media_type or "all",
    }
    if page_ids:
        params["search_type"] = "page"
        params["view_all_page_id"] = page_ids[0]
        if len(page_ids) > 1:
            return [base + urlencode({**params, "view_all_page_id": pid}) for pid in page_ids]
    else:
        params["search_type"] = "keyword"
        params["q"] = query or ""
    return [base + urlencode(params)]


def build_pipeline(
    with_analysis: bool = True,
    csv_only: bool = False,
    source: str = "meta",
    from_apify_file: bool = False,
    use_assemblyai: bool = True,
) -> AdsPipeline:
    settings = get_settings()
    if from_apify_file:
        meta_client = _DummyMetaClient()
    else:
        if source == "meta" and not settings.meta_access_token:
            raise typer.BadParameter("`META_ACCESS_TOKEN` must be set in `.env` when using --source meta.")
        if source == "apify" and not settings.apify_api_token:
            raise typer.BadParameter("`APIFY_API_TOKEN` must be set in `.env` when using --source apify. Install optional deps: pip install meta-ads-library[apify]")
        meta_client = MetaAdsClient(
            access_token=settings.meta_access_token or "",
            api_version=settings.meta_api_version,
        )
    session_factory = None if csv_only else create_session_factory(settings.database_url)
    media_processor = MediaProcessor(
        cache_dir=settings.media_cache_dir,
        access_token=settings.meta_access_token,
    )
    assemblyai_client = None
    if use_assemblyai and settings.assemblyai_api_key:
        assemblyai_client = AssemblyAIClient(api_key=settings.assemblyai_api_key)
    nexos_client = None
    if with_analysis and not csv_only:
        if not settings.nexos_api_key:
            raise typer.BadParameter("`NEXOS_API_KEY` must be set in `.env` when `--analyze` is enabled.")
        nexos_client = NexosAnalysisClient(
            api_key=settings.nexos_api_key,
            model=settings.nexos_model,
            base_url=settings.nexos_base_url,
        )
    return AdsPipeline(
        meta_client=meta_client,
        media_processor=media_processor,
        session_factory=session_factory,
        assemblyai_client=assemblyai_client,
        nexos_client=nexos_client,
    )


def _is_apify_url(value: str) -> bool:
    return value.strip().startswith(("http://", "https://"))


@app.command("apify-import")
def apify_import(
    json_input: Annotated[str, typer.Argument(help="Path to Apify JSON file, or Apify dataset items URL (e.g. https://api.apify.com/v2/datasets/XXX/items?format=json&clean=true).")],
    no_transcribe: Annotated[bool, typer.Option("--no-transcribe", help="Skip AssemblyAI transcription for videos.")] = False,
    output_csv: Annotated[Path | None, typer.Option("--output", "-o", help="Write CSV to this path (default: exports/<run_id>.csv).")] = None,
) -> None:
    """
    Main flow: load Apify JSON (file or URL), validate, process each ad (video → transcribe + download; image → download), export CSV.

    Steps: (a) load and validate JSON from Apify, (b) analyze structure,
    (c) for video ads: transcribe via AssemblyAI and download video in parallel,
    (d) for image ads: download image locally, (e) save all valuable info to CSV.
    """
    json_input = json_input.strip()
    if _is_apify_url(json_input):
        typer.echo(f"Fetching and validating Apify JSON from URL...")
        try:
            raw_items = load_and_validate_apify_from_url(json_input)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"Failed to fetch URL: {e}", err=True)
            raise typer.Exit(1)
    else:
        path = Path(json_input)
        if not path.exists():
            raise typer.BadParameter(f"JSON file not found: {path}")

        typer.echo(f"Loading and validating Apify JSON: {path}")
        try:
            raw_items = load_and_validate_apify_json(path)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1)

    typer.echo(f"Valid syntax: {len(raw_items)} ad(s). Converting to pipeline format...")
    payloads = [apify_item_to_meta_payload(item) for item in raw_items]
    videos = sum(1 for p in payloads if p.get("_resolved_media_type") == "video")
    images = sum(1 for p in payloads if p.get("_resolved_media_type") == "image")
    typer.echo(f"Media: {videos} video(s), {images} image(s).")

    pipeline = build_pipeline(
        with_analysis=False,
        csv_only=True,
        from_apify_file=True,
        use_assemblyai=not no_transcribe,
    )
    ads_pages = [ApifyAdsPage(ads=payloads)]

    typer.echo("Processing: downloading media, transcribing videos (AssemblyAI)...")
    result = pipeline.run(
        query="",
        countries=[],
        page_ids=[],
        analyze=False,
        save_to_db=False,
        ads_pages=ads_pages,
    )

    if output_csv is not None:
        import shutil
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(result.csv_path, output_csv)
        typer.echo(f"CSV written to: {output_csv}")
    else:
        typer.echo(f"CSV written to: {result.csv_path}")

    typer.echo(
        "\n".join(
            [
                f"Processed ads: {result.total_fetched}",
                f"30d+ ads: {result.total_30d_plus}",
                f"Dedupe clusters: {result.total_clusters}",
            ]
        )
    )


@app.command("init-db")
def init_db() -> None:
    """Create tables directly for local bootstrapping."""
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    typer.echo("Database tables created.")


@app.command("fetch")
def fetch(
    query: Annotated[str | None, typer.Option("--query", help="Keyword query for Ads Library search.")] = None,
    country: Annotated[list[str], typer.Option("--country", help="Repeat for multiple reached countries.")] = ["US"],
    page_id: Annotated[list[str], typer.Option("--page-id", help="Repeat for multiple page IDs.")] = [],
    media_type: Annotated[str | None, typer.Option("--media-type", help="ALL, IMAGE, MEME, VIDEO, NONE.")] = None,
    active_status: Annotated[str, typer.Option("--active-status", help="ACTIVE, INACTIVE, ALL.")] = "ALL",
    search_type: Annotated[str, typer.Option("--search-type", help="KEYWORD_UNORDERED or KEYWORD_EXACT_PHRASE.")] = "KEYWORD_UNORDERED",
    platform: Annotated[list[str], typer.Option("--platform", help="Repeat to filter by publisher platform.")] = [],
    delivery_date_min: Annotated[str | None, typer.Option("--date-min", help="YYYY-mm-dd")] = None,
    delivery_date_max: Annotated[str | None, typer.Option("--date-max", help="YYYY-mm-dd")] = None,
    limit_pages: Annotated[int | None, typer.Option("--limit-pages", help="Cap pagination for testing.")] = None,
    analyze: Annotated[bool, typer.Option("--analyze/--no-analyze", help="Run optional Nexos analysis for canonical 30d+ creatives.")] = False,
    csv_only: Annotated[bool, typer.Option("--csv-only", help="Do not use the database; save results only to CSV (avoids large DB file).")] = False,
    source: Annotated[str, typer.Option("--source", help="Where to fetch ads: meta (Ads Library API) or apify (Apify scraper; use when snapshot fetch fails).")] = "meta",
) -> None:
    """Fetch ads, dedupe 30d+ creatives, and write CSV. Use --source apify when Meta snapshot returns 400/empty."""
    pipeline = build_pipeline(
        with_analysis=analyze and not csv_only,
        csv_only=csv_only,
        source=source,
    )
    ads_pages = None
    if source == "apify":
        settings = get_settings()
        apify_client = ApifyAdsClient(
            api_token=settings.apify_api_token,
            actor_id=settings.apify_facebook_actor_id,
        )
        start_urls = _build_apify_start_urls(
            query=query,
            page_ids=page_id,
            countries=country,
            media_type=media_type,
            active_status=active_status,
        )
        typer.echo(f"Running Apify actor with {len(start_urls)} start URL(s)...")
        payloads = apify_client.run_and_fetch(start_urls=start_urls, max_ads=limit_pages * 25 if limit_pages else None)
        ads_pages = [ApifyAdsPage(ads=payloads)] if payloads else []
        if not payloads:
            typer.echo("No ads returned from Apify.")
            raise typer.Exit(0)
    result = pipeline.run(
        query=query,
        countries=country,
        page_ids=page_id,
        media_type=media_type,
        active_status=active_status,
        search_type=search_type,
        publisher_platforms=platform,
        delivery_date_min=delivery_date_min,
        delivery_date_max=delivery_date_max,
        limit_pages=limit_pages,
        analyze=analyze and not csv_only,
        save_to_db=not csv_only,
        ads_pages=ads_pages,
    )

    typer.echo(
        "\n".join(
            [
                f"Ingest run: {result.ingest_run_id}",
                f"Fetched ads: {result.total_fetched}",
                f"30d+ ads: {result.total_30d_plus}",
                f"Dedupe clusters: {result.total_clusters}",
                f"Analyzed ads: {result.analyzed_ads}",
                f"CSV export: {result.csv_path}",
            ]
        )
    )


@app.command("download-asset")
def download_asset(
    snapshot_url: Annotated[str, typer.Option("--snapshot-url", help="ad_snapshot_url from Ads Library.")],
    ad_id: Annotated[str, typer.Option("--ad-id", help="Meta ad ID for cache folder name.")] = "single",
    transcribe: Annotated[bool, typer.Option("--transcribe/--no-transcribe", help="Send video URL to AssemblyAI for transcript.")] = False,
    debug_snapshot: Annotated[bool, typer.Option("--debug-snapshot", help="Save snapshot HTML to media-cache/snapshot_debug.html to inspect what was fetched.")] = False,
) -> None:
    """Parse exact video/image URL from snapshot HTML and download the asset. Optionally transcribe video from URL."""
    settings = get_settings()
    media_processor = MediaProcessor(
        cache_dir=settings.media_cache_dir,
        access_token=settings.meta_access_token,
    )
    assemblyai_client = AssemblyAIClient(api_key=settings.assemblyai_api_key) if settings.assemblyai_api_key else None

    debug_path = settings.media_cache_dir / "snapshot_debug.html" if debug_snapshot else None
    try:
        resolved = media_processor.resolve_snapshot_media(snapshot_url, debug_snapshot_path=debug_path)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    if debug_snapshot:
        typer.echo(f"Debug: snapshot HTML saved to {debug_path}")
    typer.echo(f"Resolved: {resolved.resolved_url or 'none'} (type={resolved.asset_type}, extracted={resolved.extracted_url or 'n/a'})")
    if not resolved.resolved_url:
        raise typer.Exit(1)

    media_result = media_processor.download_media_from_url(
        meta_ad_id=ad_id,
        media_url=resolved.resolved_url,
        source_snapshot_url=snapshot_url,
        extracted_url=resolved.extracted_url,
    )
    typer.echo(f"Downloaded: {media_result.local_path}")

    transcript_result = None
    if resolved.asset_type == "video" and transcribe and assemblyai_client:
        transcript_result = assemblyai_client.transcribe_from_url(resolved.resolved_url)
        preview = (transcript_result.transcript_text or "")[:80]
        if len(transcript_result.transcript_text or "") > 80:
            preview += "..."
        typer.echo(f"Transcript: {transcript_result.status} ({preview or 'n/a'})")
    elif resolved.asset_type == "video" and transcribe and not assemblyai_client:
        typer.echo("Transcribe skipped: ASSEMBLYAI_API_KEY not set.")

    typer.echo(f"resolved_media_url={media_result.resolved_media_url}")
    if transcript_result and transcript_result.utterances:
        typer.echo("Timestamped transcript:")
        for u in transcript_result.utterances[:10]:
            typer.echo(f"  [{u.get('start', 0)}ms] {u.get('text', '')}")


@app.command("fetch-dataset")
def fetch_dataset(
    dataset_url: Annotated[str | None, typer.Option("--dataset-url", help="Apify dataset items URL (e.g. https://api.apify.com/v2/datasets/XXX/items?format=json&clean=true).")] = None,
    dataset_file: Annotated[str | None, typer.Option("--dataset-file", help="Local JSON file with Apify dataset items (array).")] = None,
    csv_only: Annotated[bool, typer.Option("--csv-only", help="Do not use the database; write only CSV.")] = True,
) -> None:
    """Load Apify dataset (from URL or file), extract video/image URLs, download assets, and export CSV."""
    if not dataset_url and not dataset_file:
        raise typer.BadParameter("Provide either --dataset-url or --dataset-file.")
    if dataset_url and dataset_file:
        raise typer.BadParameter("Provide only one of --dataset-url or --dataset-file.")

    if dataset_url:
        typer.echo(f"Fetching dataset from {dataset_url[:60]}...")
        payloads = fetch_dataset_items_from_url(dataset_url)
    else:
        path = Path(dataset_file)
        if not path.exists():
            raise typer.BadParameter(f"File not found: {path}")
        typer.echo(f"Loading dataset from {path}...")
        payloads = fetch_dataset_items_from_file(path)

    if not payloads:
        typer.echo("No items in dataset.")
        raise typer.Exit(0)

    with_video = sum(1 for p in payloads if p.get("_resolved_media_url"))
    typer.echo(f"Loaded {len(payloads)} ads ({with_video} with media URL). Running pipeline...")

    pipeline = build_pipeline(with_analysis=False, csv_only=csv_only, source="meta")
    ads_pages = [ApifyAdsPage(ads=payloads)]
    result = pipeline.run(
        query="",
        countries=["US"],
        page_ids=[],
        analyze=False,
        save_to_db=not csv_only,
        ads_pages=ads_pages,
    )
    typer.echo(
        "\n".join(
            [
                f"Run ID: {result.ingest_run_id}",
                f"Fetched ads: {result.total_fetched}",
                f"30d+ ads: {result.total_30d_plus}",
                f"Dedupe clusters: {result.total_clusters}",
                f"CSV export: {result.csv_path}",
            ]
        )
    )


if __name__ == "__main__":
    app()
