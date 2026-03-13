from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from meta_ads.assemblyai_client import TranscriptResult
from meta_ads.media import MediaFetchResult, file_to_data_url


class AdLike(Protocol):
    meta_ad_id: str
    page_name: str | None
    ad_creative_bodies: list[str]
    ad_creative_link_titles: list[str]
    ad_creative_link_descriptions: list[str]
    ad_creative_link_captions: list[str]
    duration_days: float | None
    media_type_guess: str
    ad_snapshot_url: str | None


def _build_ad_text(ad: AdLike) -> str:
    return "\n".join(
        [
            f"Meta ad id: {ad.meta_ad_id}",
            f"Page name: {ad.page_name or 'Unknown'}",
            f"Runtime days: {ad.duration_days if ad.duration_days is not None else 'Unknown'}",
            f"Media type guess: {ad.media_type_guess}",
            f"Bodies: {' | '.join(ad.ad_creative_bodies) or 'None'}",
            f"Titles: {' | '.join(ad.ad_creative_link_titles) or 'None'}",
            f"Descriptions: {' | '.join(ad.ad_creative_link_descriptions) or 'None'}",
            f"Captions: {' | '.join(ad.ad_creative_link_captions) or 'None'}",
            f"Snapshot URL: {ad.ad_snapshot_url or 'None'}",
        ]
    )


def _format_transcript(transcript: TranscriptResult | None) -> str:
    if transcript is None:
        return "No transcript available."
    if transcript.utterances:
        lines: list[str] = []
        for utterance in transcript.utterances:
            start_ms = int(utterance.get("start", 0))
            seconds = round(start_ms / 1000, 2)
            text = str(utterance.get("text", "")).strip()
            if text:
                lines.append(f"[{seconds:0.2f}s] {text}")
        if lines:
            return "\n".join(lines)
    return transcript.transcript_text or "Transcript returned no text."


class NexosAnalysisClient:
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.nexos.ai/v1", timeout: float = 120.0) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _build_messages(
        self,
        ad: AdLike,
        media_asset: MediaFetchResult | None,
        transcript: TranscriptResult | None,
    ) -> list[dict[str, Any]]:
        system_prompt = (
            "You are analyzing winning Meta ads. Return only JSON with keys: "
            "hook, primary_angle, desire, offer, audience, cta, proof_elements, creative_notes, confidence."
        )

        user_prompt = (
            "Analyze this ad creative. Focus on why the ad likely persists for 30+ days.\n\n"
            f"{_build_ad_text(ad)}\n\n"
            f"Timestamped transcript:\n{_format_transcript(transcript)}\n\n"
            "If the ad is video, identify the hook in the first 3 seconds using both the available preview image(s) "
            "and the early transcript lines. Then analyze the main angle or desire, the offer, and the CTA. "
            "If evidence is incomplete, still provide your best structured estimate and keep confidence lower."
        )

        user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        if media_asset:
            data_url = file_to_data_url(media_asset.extracted_preview_path or media_asset.local_path)
            if data_url and (media_asset.asset_type == "image" or media_asset.extracted_preview_path):
                user_content.append({"type": "image_url", "image_url": {"url": data_url}})

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def analyze_creative(
        self,
        ad: AdLike,
        media_asset: MediaFetchResult | None = None,
        transcript: TranscriptResult | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": self._build_messages(ad, media_asset=media_asset, transcript=transcript),
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            response_payload = response.json()

        content = (
            response_payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {
                "hook": None,
                "primary_angle": None,
                "desire": None,
                "offer": None,
                "audience": None,
                "cta": None,
                "proof_elements": [],
                "creative_notes": content,
                "confidence": 0.2,
            }

        parsed["raw_response"] = response_payload
        return parsed
