from meta_ads.assemblyai_client import TranscriptResult
from meta_ads.nexos_client import _format_transcript


def test_format_transcript_uses_timestamps() -> None:
    transcript = TranscriptResult(
        status="completed",
        provider="assemblyai",
        transcript_text="Hello world",
        transcript_json={},
        utterances=[
            {"start": 0, "text": "Stop the scroll."},
            {"start": 2150, "text": "This serum fixes dry skin."},
        ],
        words=[],
        language_code="en",
        audio_duration=6.5,
    )

    formatted = _format_transcript(transcript)

    assert "[0.00s] Stop the scroll." in formatted
    assert "[2.15s] This serum fixes dry skin." in formatted
