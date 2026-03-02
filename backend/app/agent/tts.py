from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

PROMPT_NOT_VERIFIED = "Please speak a little more so I can verify you."
PROMPT_ASK_AGAIN = "I didn't catch a clear question. Could you please ask again?"
PROMPT_VERIFICATION_FAILED_RETRY = "Sorry, I couldn't verify you. Please say something so I can try again."


async def synthesise_speech(text: str, voice: str = "alloy") -> bytes:
    """Convert *text* to mp3 audio bytes using OpenAI TTS.

    Args:
        text:  The spoken text to synthesise.
        voice: OpenAI TTS voice name (default: ``"alloy"``).

    Returns:
        Raw mp3 bytes, or ``b""`` on any API / network error.
    """
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="mp3",
        )
        return await response.aread()
    except Exception as exc:
        logger.warning("OpenAI TTS failed: %s", exc)
        return b""
