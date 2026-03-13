#!/usr/bin/env python3
"""
Proof-of-concept: load Apify scraping JSON, find 'videoHdUrl', and download the video.

Usage:
  python scripts/download_apify_video_poc.py <path-to-apify-json>
  python scripts/download_apify_video_poc.py <path-to-apify-json> --output my_video.mp4

If no file is given, uses a built-in sample URL (single video).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx


def find_video_hd_urls(obj, into: list[str]) -> None:
    """Recursively find all 'videoHdUrl' string values in a JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "videoHdUrl" and isinstance(v, str) and v.strip():
                into.append(v.strip())
            else:
                find_video_hd_urls(v, into)
    elif isinstance(obj, list):
        for item in obj:
            find_video_hd_urls(item, into)


def load_json(path: Path) -> object:
    """Load JSON from file."""
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def download_video(url: str, output_path: Path, timeout: float = 60.0) -> None:
    """Download video from URL to output_path."""
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout) as r:
        r.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=65536):
                f.write(chunk)
    print(f"Downloaded {r.num_bytes_downloaded or 0} bytes -> {output_path}")


def main() -> None:
    output = Path("downloaded_apify_video.mp4")
    json_path: Path | None = None

    args = list(sys.argv[1:])
    if "--output" in args:
        i = args.index("--output")
        output = Path(args[i + 1])
        args.pop(i)
        args.pop(i)
    if args:
        json_path = Path(args[0])

    urls: list[str] = []

    if json_path and json_path.exists():
        data = load_json(json_path)
        find_video_hd_urls(data, urls)
        print(f"Loaded {json_path}: found {len(urls)} videoHdUrl(s).")
    else:
        # No file or missing: use built-in sample URL (same as user's POC example)
        sample = "https://video-det1-1.xx.fbcdn.net/o1/v/t2/f2/m367/AQMd3P0E2K2ZXBbCXTbYenJbLJfzcc4ZwXqVBRa6FtPZVg3yuleIY4YIkhTCb5-Op9Pxah9vMEIAa5WnCmj8zT9JIEa6r-kCZVy3qAAiXg.mp4?_nc_cat=105&_nc_sid=8bf8fe&_nc_ht=video-det1-1.xx.fbcdn.net&_nc_ohc=3m-dqTQWeu0Q7kNvwHyTCAy&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5WSV9VU0VDQVNFX1BST0RVQ1RfVFlQRS4uQzMuNzIwLnByb2dyZXNzaXZlX2gyNjQtYmFzaWMtZ2VuMl83MjBwIiwieHB2X2Fzc2V0X2lkIjoxNzg4NTQ0MTA5NDQ0ODQ1MywiYXNzZXRfYWdlX2RheXMiOjE4LCJ2aV91c2VjYXNlX2lkIjoxMDA5OSwiZHVyYXRpb25fcyI6MTAwLCJ1cmxnZW5fc291cmNlIjoid3d3In0%3D&ccb=17-1&_nc_gid=dHnyaZdMZ6jd-RdP8jmbaA&_nc_ss=8&_nc_zt=28&oh=00_AfwLU5lcEx_TeUC5IbQga1hMJXzib0xJbB7M3EwVaOy9gQ&oe=69B9BC75"
        urls = [sample]
        print("No JSON file given or file missing; using built-in sample videoHdUrl.")

    if not urls:
        print("No videoHdUrl found in JSON. Exiting.")
        sys.exit(1)

    url = urls[0]
    print(f"Downloading: {url[:80]}...")
    download_video(url, output)
    print("Done.")


if __name__ == "__main__":
    main()
