from __future__ import annotations

import io
import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, language: str = "en") -> str:
    """Transcribe *audio_bytes* using OpenAI Whisper.

    Args:
        audio_bytes: Raw WAV audio to transcribe.
        language:    BCP-47 language code (default: ``"en"``).

    Returns:
        Transcribed text, or ``""`` on any API / network error.
    """
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("[STT] Sending %d bytes to Whisper", len(audio_bytes))
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", io.BytesIO(audio_bytes), "audio/wav"),
            language=language,
        )
        text = response.text
        logger.info("[STT] ← Heard: %r  (%d words)", text, len(text.split()))
        return text
    except Exception as exc:
        logger.warning("[STT] Whisper STT failed: %s", exc)
        return ""
