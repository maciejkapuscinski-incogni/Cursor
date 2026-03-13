from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(slots=True)
class TranscriptResult:
    status: str
    provider: str
    transcript_text: str | None
    transcript_json: dict[str, Any]
    utterances: list[dict[str, Any]]
    words: list[dict[str, Any]]
    language_code: str | None
    audio_duration: float | None
    last_error: str | None = None


class AssemblyAIClient:
    def __init__(self, api_key: str, timeout: float = 120.0, poll_interval_seconds: float = 3.0) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.poll_interval_seconds = poll_interval_seconds
        self.base_url = "https://api.assemblyai.com/v2"

    @property
    def headers(self) -> dict[str, str]:
        return {"authorization": self.api_key}

    def _upload(self, video_path: str) -> str:
        path = Path(video_path)
        with path.open("rb") as handle, httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            response = client.post(f"{self.base_url}/upload", content=handle)
            response.raise_for_status()
            return response.json()["upload_url"]

    def _request_transcript(self, audio_url: str) -> TranscriptResult:
        transcript_request = {
            "audio_url": audio_url,
            "speech_models": ["universal-2"],
            "speaker_labels": False,
            "auto_chapters": False,
            "punctuate": True,
            "format_text": True,
        }

        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            create_response = client.post(f"{self.base_url}/transcript", json=transcript_request)
            if create_response.status_code != 200:
                try:
                    err_body = create_response.json()
                    msg = err_body.get("error") or err_body.get("message") or create_response.text
                except Exception:
                    msg = create_response.text or f"{create_response.status_code}"
                return TranscriptResult(
                    status="failed",
                    provider="assemblyai",
                    transcript_text=None,
                    transcript_json={},
                    utterances=[],
                    words=[],
                    language_code=None,
                    audio_duration=None,
                    last_error=f"{create_response.status_code} {create_response.reason_phrase}: {msg}",
                )
            transcript_id = create_response.json()["id"]

            while True:
                polling_response = client.get(f"{self.base_url}/transcript/{transcript_id}")
                polling_response.raise_for_status()
                payload = polling_response.json()
                status = payload["status"]
                if status == "completed":
                    return TranscriptResult(
                        status="completed",
                        provider="assemblyai",
                        transcript_text=payload.get("text"),
                        transcript_json=payload,
                        utterances=list(payload.get("utterances") or []),
                        words=list(payload.get("words") or []),
                        language_code=payload.get("language_code"),
                        audio_duration=payload.get("audio_duration"),
                    )
                if status == "error":
                    return TranscriptResult(
                        status="failed",
                        provider="assemblyai",
                        transcript_text=None,
                        transcript_json=payload,
                        utterances=[],
                        words=[],
                        language_code=payload.get("language_code"),
                        audio_duration=payload.get("audio_duration"),
                        last_error=payload.get("error") or "AssemblyAI transcription failed.",
                    )
                time.sleep(self.poll_interval_seconds)

    def transcribe_from_url(self, video_or_audio_url: str) -> TranscriptResult:
        """Transcribe from a public media URL (no file upload). Use for video/image CDN URLs."""
        return self._request_transcript(video_or_audio_url)

    def transcribe_video(self, video_path: str) -> TranscriptResult:
        upload_url = self._upload(video_path)
        return self._request_transcript(upload_url)
