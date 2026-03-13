from __future__ import annotations

import base64
import mimetypes
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx


MEDIA_URL_PATTERNS = [
    # Double-quoted meta tags (common)
    (r'property="og:video"\s+content="([^"]+)"', "video"),
    (r'property="og:image"\s+content="([^"]+)"', "image"),
    (r'content="([^"]+)"[^>]*property="og:video"', "video"),
    (r'content="([^"]+)"[^>]*property="og:image"', "image"),
    # Single-quoted meta tags (Meta sometimes uses these)
    (r"property='og:video'\s+content='([^']+)'", "video"),
    (r"property='og:image'\s+content='([^']+)'", "image"),
    (r"content='([^']+)'[^>]*property='og:video'", "video"),
    (r"content='([^']+)'[^>]*property='og:image'", "image"),
    # <video src=""> – exact URL to fetch, push to AssemblyAI, and download
    (r'<video[^>]+src="([^"]+)"', "video"),
    (r"<video[^>]+src='([^']+)'", "video"),
    (r'<source[^>]+src="([^"]+)"', "video"),
    (r'<source[^>]+src=\'([^\']+)\'', "video"),
    (r'"playable_url"\s*:\s*"([^"]+)"', "video"),
    (r"'playable_url'\s*:\s*'([^']+)'", "video"),
    # JSON-style escaped URL (e.g. "playable_url":"https:\/\/...")
    (r'"playable_url"\s*:\s*"((?:[^"\\]|\\.)*)"', "video"),
]


@dataclass(slots=True)
class ResolvedSnapshotMedia:
    """Exact media URL(s) parsed from ad_snapshot_url (HTML or redirect)."""

    resolved_url: str | None
    asset_type: str  # "video" | "image" | "unknown"
    extracted_url: str | None  # raw URL from HTML before redirects
    snapshot_html_path: str | None = None


@dataclass(slots=True)
class MediaFetchResult:
    status: str
    source_url: str
    resolved_media_url: str | None = None
    """URL used for download (after redirects). Also written to CSV as video_url."""
    extracted_media_url: str | None = None
    """URL as parsed from snapshot HTML (before redirects). Written to CSV for debugging."""
    local_path: str | None = None
    snapshot_html_path: str | None = None
    extracted_preview_path: str | None = None
    asset_type: str | None = None
    mime_type: str | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)
    last_error: str | None = None


class MediaProcessor:
    def __init__(
        self,
        cache_dir: Path,
        timeout: float = 60.0,
        access_token: str | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.access_token = access_token

    def _snapshot_url_with_token(self, snapshot_url: str) -> str:
        """Append Meta access token to Facebook render_ad URLs if missing (so we can fetch the page)."""
        if not self.access_token:
            return snapshot_url
        if "access_token=" in snapshot_url:
            return snapshot_url
        if "facebook.com/ads/archive/render_ad" not in snapshot_url and "fb.com/ads/archive/render_ad" not in snapshot_url:
            return snapshot_url
        parsed = urlparse(snapshot_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs["access_token"] = [self.access_token]
        new_query = urlencode(qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    def _safe_stem(self, meta_ad_id: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", meta_ad_id)

    def _normalize_extracted_url(self, raw: str) -> str:
        return raw.encode("utf-8").decode("unicode_escape").replace("\\/", "/")

    def _extract_media_url(self, html: str) -> str | None:
        for pattern, _ in MEDIA_URL_PATTERNS:
            match = re.search(pattern, html)
            if match:
                return self._normalize_extracted_url(match.group(1))
        return None

    def _extract_all_media_urls(self, html: str) -> list[tuple[str, str]]:
        """Return exact video/image URLs from HTML: list of (asset_type, url)."""
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for pattern, kind in MEDIA_URL_PATTERNS:
            match = re.search(pattern, html)
            if match:
                url = self._normalize_extracted_url(match.group(1))
                if url and url not in seen:
                    seen.add(url)
                    out.append((kind, url))
        return out

    def resolve_snapshot_media(
        self,
        snapshot_url: str,
        meta_ad_id: str | None = None,
        debug_snapshot_path: Path | None = None,
    ) -> ResolvedSnapshotMedia:
        """
        Fetch ad_snapshot_url in memory and parse exact video or image URL from the HTML.
        Does not save the snapshot HTML to cache. Once the media URL (e.g. MP4) is found,
        it is used for AssemblyAI and for downloading the asset only.
        If debug_snapshot_path is set, the raw snapshot HTML is written there for inspection.
        """
        fetch_url = self._snapshot_url_with_token(snapshot_url)
        # Use a browser-like User-Agent so Facebook may return richer content
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            try:
                snapshot_response = client.get(fetch_url, follow_redirects=True)
                snapshot_response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    raise ValueError(
                        "Facebook returned 400 Bad Request for the snapshot URL. "
                        "Check that META_ACCESS_TOKEN in .env is valid and not expired. "
                        "If the same URL works in a browser, Facebook may be blocking programmatic access."
                    ) from e
                raise

            html_text = snapshot_response.text
            if debug_snapshot_path is not None:
                debug_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                debug_snapshot_path.write_text(html_text, encoding="utf-8")

            content_type = snapshot_response.headers.get("content-type", "")
            if content_type.startswith("video/") or content_type.startswith("image/"):
                resolved = str(snapshot_response.url)
                kind = "video" if content_type.startswith("video/") else "image"
                return ResolvedSnapshotMedia(
                    resolved_url=resolved,
                    asset_type=kind,
                    extracted_url=None,
                )

            # Parse media URL from HTML in memory (no snapshot saved to disk)
            all_urls = self._extract_all_media_urls(html_text)
            # Facebook often serves a JS app shell; try noscript fallback for server-rendered ad HTML
            if not all_urls and "facebook.com/ads/archive/render_ad" in snapshot_url:
                noscript_url = fetch_url + ("&" if "?" in fetch_url else "?") + "_fb_noscript=1"
                try:
                    noscript_response = client.get(noscript_url, follow_redirects=True)
                    noscript_response.raise_for_status()
                    html_text = noscript_response.text
                    if debug_snapshot_path is not None:
                        debug_snapshot_path.write_text(html_text, encoding="utf-8")
                    all_urls = self._extract_all_media_urls(html_text)
                except (httpx.HTTPStatusError, httpx.RequestError):
                    # _fb_noscript=1 often returns 400 or other errors; ignore and keep "no URL"
                    pass
            if not all_urls:
                return ResolvedSnapshotMedia(
                    resolved_url=None,
                    asset_type="unknown",
                    extracted_url=None,
                )
            # Prefer first video, then first image
            video_url = next((u for k, u in all_urls if k == "video"), None)
            image_url = next((u for k, u in all_urls if k == "image"), None)
            extracted = video_url or image_url
            kind = "video" if video_url else "image"
            # Resolve final URL (follow redirects)
            try:
                r = client.get(extracted, follow_redirects=True)
                r.raise_for_status()
                resolved = str(r.url)
            except Exception:
                resolved = extracted
            return ResolvedSnapshotMedia(
                resolved_url=resolved,
                asset_type=kind,
                extracted_url=extracted,
            )

    def _download_file(self, client: httpx.Client, url: str, target_path: Path) -> tuple[str | None, str, str]:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        mime_type = response.headers.get("content-type") or mimetypes.guess_type(str(target_path))[0] or "application/octet-stream"
        return mime_type, str(target_path), str(response.url)

    def _extract_preview(self, asset_path: Path) -> tuple[str | None, dict[str, object]]:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None, {"ffmpeg_available": False}

        clip_path = asset_path.with_name(f"{asset_path.stem}_first3s.mp4")
        frame_path = asset_path.with_name(f"{asset_path.stem}_firstframe.jpg")
        subprocess.run(
            [ffmpeg, "-y", "-i", str(asset_path), "-t", "3", str(clip_path)],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            [ffmpeg, "-y", "-i", str(asset_path), "-vf", "select=eq(n\\,0)", "-vframes", "1", str(frame_path)],
            check=False,
            capture_output=True,
        )
        metadata: dict[str, object] = {
            "ffmpeg_available": True,
            "preview_clip_path": str(clip_path) if clip_path.exists() else None,
        }
        if frame_path.exists():
            return str(frame_path), metadata
        return None, {**metadata, "preview_extracted": False}

    def fetch_media(self, meta_ad_id: str, snapshot_url: str) -> MediaFetchResult:
        ad_dir = self.cache_dir / self._safe_stem(meta_ad_id)
        ad_dir.mkdir(parents=True, exist_ok=True)
        snapshot_html_path = ad_dir / "snapshot.html"

        with httpx.Client(timeout=self.timeout, headers={"User-Agent": "meta-ads-library/0.1"}) as client:
            snapshot_response = client.get(snapshot_url, follow_redirects=True)
            snapshot_response.raise_for_status()

            content_type = snapshot_response.headers.get("content-type", "")
            if content_type.startswith("video/") or content_type.startswith("image/"):
                extension = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".bin"
                asset_path = ad_dir / f"creative{extension}"
                asset_path.write_bytes(snapshot_response.content)
                preview_path = None
                resolved_media_url = str(snapshot_response.url)
                metadata: dict[str, object] = {"resolved_media_url": resolved_media_url}
                asset_type = "video" if content_type.startswith("video/") else "image"
                if asset_type == "video":
                    preview_path, metadata = self._extract_preview(asset_path)
                    metadata["resolved_media_url"] = resolved_media_url
                return MediaFetchResult(
                    status="downloaded",
                    source_url=snapshot_url,
                    resolved_media_url=resolved_media_url,
                    local_path=str(asset_path),
                    extracted_preview_path=preview_path,
                    asset_type=asset_type,
                    mime_type=content_type.split(";")[0].strip(),
                    metadata_json=metadata,
                )

            snapshot_html_path.write_text(snapshot_response.text, encoding="utf-8")
            media_url = self._extract_media_url(snapshot_response.text)
            if not media_url:
                return MediaFetchResult(
                    status="media_fetch_failed",
                    source_url=snapshot_url,
                    snapshot_html_path=str(snapshot_html_path),
                    last_error="No media URL could be extracted from the snapshot page.",
                )

            parsed = urlparse(media_url)
            filename = Path(parsed.path).name or "creative.bin"
            asset_path = ad_dir / filename
            mime_type, local_path, resolved_media_url = self._download_file(client, media_url, asset_path)
            asset_type = "video" if (mime_type or "").startswith("video/") else "image"
            preview_path = None
            metadata = {"resolved_media_url": resolved_media_url, "extracted_media_url": media_url}
            if asset_type == "video":
                preview_path, extra = self._extract_preview(asset_path)
                metadata.update(extra)

            return MediaFetchResult(
                status="downloaded",
                source_url=snapshot_url,
                resolved_media_url=resolved_media_url,
                local_path=local_path,
                snapshot_html_path=str(snapshot_html_path),
                extracted_preview_path=preview_path,
                asset_type=asset_type,
                mime_type=mime_type,
                metadata_json=metadata,
            )

    def download_media_from_url(
        self,
        meta_ad_id: str,
        media_url: str,
        source_snapshot_url: str,
        extracted_url: str | None = None,
    ) -> MediaFetchResult:
        """Download asset from exact media URL (e.g. from resolve_snapshot_media) and save to cache."""
        ad_dir = self.cache_dir / self._safe_stem(meta_ad_id)
        ad_dir.mkdir(parents=True, exist_ok=True)
        parsed = urlparse(media_url)
        filename = Path(parsed.path).name or "creative.bin"
        asset_path = ad_dir / filename
        metadata: dict[str, object] = {
            "resolved_media_url": media_url,
        }
        if extracted_url:
            metadata["extracted_media_url"] = extracted_url

        with httpx.Client(timeout=self.timeout, headers={"User-Agent": "meta-ads-library/0.1"}) as client:
            mime_type, local_path, final_url = self._download_file(client, media_url, asset_path)
        asset_type = "video" if (mime_type or "").startswith("video/") else "image"
        preview_path = None
        if asset_type == "video":
            preview_path, extra = self._extract_preview(asset_path)
            metadata.update(extra)

        return MediaFetchResult(
            status="downloaded",
            source_url=source_snapshot_url,
            resolved_media_url=final_url,
            extracted_media_url=extracted_url or media_url,
            local_path=local_path,
            snapshot_html_path=None,
            extracted_preview_path=preview_path,
            asset_type=asset_type,
            mime_type=mime_type,
            metadata_json=metadata,
        )


def file_to_data_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    path = Path(file_path)
    if not path.exists():
        return None
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"
