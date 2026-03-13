from pathlib import Path

from meta_ads.media import MediaProcessor


def test_extract_media_url_prefers_embedded_media() -> None:
    processor = MediaProcessor(cache_dir=Path(".pytest_cache/media"))
    html = """
    <html>
      <head>
        <meta property="og:image" content="https://cdn.example.com/image.jpg" />
      </head>
    </html>
    """

    assert processor._extract_media_url(html) == "https://cdn.example.com/image.jpg"
