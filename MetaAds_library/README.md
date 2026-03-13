# Meta Ads Library

Python pipeline for pulling ads from Meta Ads Library, storing them in SQLite by default, deduplicating long-running creatives, and preparing the data for later analysis.

## What It Does

- fetches Meta Ads Library results for a query or page IDs,
- stores both raw payloads and normalized ads in SQLite by default,
- derives whether an ad has been running for 30+ days,
- clusters near-duplicate creatives by normalized text fingerprint,
- fetches snapshot media when possible,
- can optionally transcribe downloaded video creatives with AssemblyAI and timestamps,
- keeps optional Nexos analysis code available for a later iteration.

## Project Layout

- `src/meta_ads/cli.py`: CLI entrypoints
- `src/meta_ads/meta_client.py`: Meta Ads Library API client
- `src/meta_ads/models.py`: SQLAlchemy models
- `src/meta_ads/pipeline.py`: orchestration for ingest, dedupe, and analysis
- `src/meta_ads/media.py`: snapshot/media download and first-frame extraction
- `src/meta_ads/assemblyai_client.py`: AssemblyAI transcription integration
- `src/meta_ads/nexos_client.py`: optional Nexos chat-completions integration
- `alembic/`: database migrations

## Requirements

- Python 3.11+
- Python's built-in SQLite works out of the box for the default local setup
- `ffmpeg` installed locally if you want first-frame / first-3-second extraction for video ads
- optional but recommended: AssemblyAI API key for timestamped video transcripts
- optional: `NEXOS_API_KEY` plus an available model in Nexos for creative analysis

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If you already created `.env`, keep it as-is and skip the copy step.

Default local database:

```env
DATABASE_URL=sqlite:///meta_ads.db
```

Fill in `.env`:

- `META_ACCESS_TOKEN` (required for `--source meta`)
- `DATABASE_URL`
- optional: `APIFY_API_TOKEN` and install `pip install -e ".[apify]"` for `--source apify` when snapshot fetch fails (e.g. 400)
- optional: `APIFY_FACEBOOK_ACTOR_ID` (default: `apify/facebook-ads-scraper`)
- optional: `ASSEMBLYAI_API_KEY`
- optional: `NEXOS_API_KEY`
- optional: `NEXOS_MODEL`
- optional: `NEXOS_BASE_URL`

## Database Bootstrapping

Quick local bootstrap:

```bash
source .venv/bin/activate
meta-ads init-db
```

This creates tables in the local `meta_ads.db` SQLite file.

Or run Alembic manually:

```bash
alembic upgrade head
```

## Usage

### Main flow: Apify import (no Meta API)

The primary workflow is to use **Apify** to scrape the Ads Library, export the run as JSON, then run the pipeline locally:

1. **Manual input**: Run the Apify Facebook Ads Scraper, download the dataset as JSON, and save it locally.
2. **Validate and process**: Run `apify-import` with that JSON file. The script will:
   - Load and validate the JSON (syntax and expected Apify structure),
   - For each **video** ad: send the video URL to AssemblyAI for transcription (with timestamps) and **in parallel** download the video locally,
   - For each **image** ad: download the image locally,
   - Gather all valuable information (ad metadata, transcripts, local paths) and write a single CSV.

```bash
# From a local JSON file
meta-ads apify-import path/to/apify_export.json
meta-ads apify-import path/to/apify_export.json --output results.csv

# From an Apify dataset URL (quote the URL so the shell doesn't interpret ? and &)
meta-ads apify-import 'https://api.apify.com/v2/datasets/YOUR_DATASET_ID/items?format=json&clean=true'

meta-ads apify-import path/to/apify_export.json --no-transcribe   # skip AssemblyAI
```

No `META_ACCESS_TOKEN` or database is required for this flow. Set `ASSEMBLYAI_API_KEY` in `.env` to transcribe videos.

---

Fetch ads for a keyword (Meta API or Apify run):

```bash
source .venv/bin/activate
meta-ads fetch --query "anti aging serum" --country US --media-type VIDEO
```

If you prefer not to activate the virtualenv in each shell, you can run the binary directly:

```bash
.venv/bin/meta-ads fetch --query "anti aging serum" --country US --media-type VIDEO
```

Each successful fetch writes a CSV export under `exports/` named with the ingest run ID.
When media extraction works, the CSV includes both local file paths and the resolved media URL behind the snapshot page.

If you later want Postgres again, install the optional adapter and point `DATABASE_URL` at your server:

```bash
pip install -e ".[postgres]"
```

Fetch from specific pages:

```bash
meta-ads fetch --page-id 123456789 --page-id 987654321 --country US --no-analyze
```

Useful flags:

- `--limit-pages 2` for safe testing
- `--platform FACEBOOK --platform INSTAGRAM`
- `--date-min 2026-01-01 --date-max 2026-03-01`
- `--active-status ACTIVE`

## Current Iteration

The current default workflow is ingestion-only:

- fetch ads from Meta Ads Library,
- store raw and normalized data,
- download image and video assets locally when available,
- transcribe downloaded videos with AssemblyAI when `ASSEMBLYAI_API_KEY` is set,
- derive 30d+ runtime flags,
- cluster duplicate creatives,
- export a CSV after each completed fetch.

No LLM analysis runs unless you explicitly pass `--analyze` and provide Nexos credentials.

## Media And Transcripts

Meta exposes `ad_snapshot_url`, but not every archived ad gives a directly downloadable video file. This project therefore treats media fetching as best effort:

- the pipeline parses the **exact video or image URL** from the snapshot HTML (e.g. `og:video`, `og:image`, `playable_url`, `<source src>`),
- for **videos**: the resolved URL is sent to AssemblyAI for transcription and the file is downloaded in **parallel**; both transcript and local path are stored in DB and CSV,
- for images (or when the snapshot redirects directly to binary): the asset is downloaded and the path and `resolved_media_url` are stored,
- if the snapshot is HTML, the extracted URL is followed to get the final CDN URL; both extracted and resolved URLs are kept in metadata,
- if video is available and `ffmpeg` is installed, a first-frame preview and 3-second clip are generated,
- if media extraction fails, optional Nexos analysis falls back to the ad text and snapshot metadata.

### Using Apify when snapshot fetch fails

If the Meta snapshot URL returns 400 or empty HTML (e.g. Facebook blocking programmatic access), use [Apify's Facebook Ads Scraper](https://apify.com/apify/facebook-ads-scraper), which runs in a browser-like environment and returns video/image URLs directly:

```bash
pip install -e ".[apify]"
# Set APIFY_API_TOKEN in .env (get it from https://console.apify.com/account/integrations)
meta-ads fetch --source apify --query "guard.io" --country US --media-type VIDEO --csv-only
```

With `--source apify`, ads and their media URLs come from Apify; the pipeline then downloads assets and runs AssemblyAI on video URLs as usual. Optional: `APIFY_FACEBOOK_ACTOR_ID` (default `apify/facebook-ads-scraper`).

### Standalone download script

To parse a snapshot URL and download the asset (and optionally transcribe video) without running a full fetch:

```bash
meta-ads download-asset --snapshot-url "https://..." [--ad-id my-ad-id] [--transcribe]
```

## Data Model Summary

- `ingest_runs`: one record per fetch
- `ads_raw`: raw Meta payloads
- `ads`: normalized ads with runtime and 30d+ flag
- `creative_fingerprints`: dedupe clusters and canonical ads
- `media_assets`: downloaded media and extraction state
- `video_transcripts`: timestamped AssemblyAI transcripts or skipped/failed transcript status for video creatives
- `analysis_jobs`: optional analysis attempts and status
- `ad_analyses`: optional structured Nexos output

## Running Tests

```bash
pytest
```
