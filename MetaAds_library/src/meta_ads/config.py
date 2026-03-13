from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    meta_access_token: str | None = Field(None, alias="META_ACCESS_TOKEN")
    meta_api_version: str = Field("v25.0", alias="META_API_VERSION")
    meta_app_id: str | None = Field(None, alias="META_APP_ID")
    meta_app_secret: str | None = Field(None, alias="META_APP_SECRET")
    assemblyai_api_key: str | None = Field(None, alias="ASSEMBLYAI_API_KEY")
    nexos_api_key: str | None = Field(None, alias="NEXOS_API_KEY")
    nexos_model: str = Field("openai/gpt-4.1-mini", alias="NEXOS_MODEL")
    nexos_base_url: str = Field("https://api.nexos.ai/v1", alias="NEXOS_BASE_URL")
    database_url: str = Field("sqlite:///meta_ads.db", alias="DATABASE_URL")
    media_cache_dir: Path = Field(Path("media-cache"), alias="MEDIA_CACHE_DIR")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    apify_api_token: str | None = Field(None, alias="APIFY_API_TOKEN")
    apify_facebook_actor_id: str = Field("apify/facebook-ads-scraper", alias="APIFY_FACEBOOK_ACTOR_ID")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    settings = Settings()
    settings.media_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
