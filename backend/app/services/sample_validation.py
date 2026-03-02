"""
Sample Text Validation Service

Transcribes an audio sample using Whisper and compares the transcription
against an expected text using fuzzy matching (SequenceMatcher).
"""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata

from app.agent.stt import transcribe_audio

logger = logging.getLogger(__name__)

# Minimum fuzzy-match ratio to consider a sample valid (85 %)
FUZZY_MATCH_THRESHOLD = 0.85


def _normalise(text: str) -> str:
    """
    Lowercase, remove punctuation and collapse whitespace so that the
    comparison is not thrown off by minor formatting differences.
    """
    # Unicode normalise  → ASCII where possible
    text = unicodedata.normalize("NFKD", text)
    # Lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def validate_sample_text(
    audio_bytes: bytes,
    expected_text: str,
    sample_number: int = 0,
) -> dict:
    """Transcribe *audio_bytes* with Whisper and compare against *expected_text*.

    Args:
        audio_bytes:   Raw WAV audio bytes.
        expected_text: The text the user was asked to speak.
        sample_number: 1-based sample index (for logging / response).

    Returns:
        A dict with keys:
          - ``matched``      (bool)   – True when similarity ≥ threshold.
          - ``transcription``(str)    – What Whisper heard.
          - ``similarity``   (float)  – Normalised SequenceMatcher ratio 0-1.
          - ``sample_number``(int)    – Echo of the input arg.
    """
    logger.info(
        "[SampleValidation] Transcribing sample %d (%d bytes)",
        sample_number,
        len(audio_bytes),
    )

    transcription = await transcribe_audio(audio_bytes)

    if not transcription:
        logger.warning(
            "[SampleValidation] Whisper returned empty transcription for sample %d",
            sample_number,
        )
        return {
            "matched": False,
            "transcription": "",
            "similarity": 0.0,
            "sample_number": sample_number,
        }

    norm_expected = _normalise(expected_text)
    norm_actual = _normalise(transcription)

    similarity = difflib.SequenceMatcher(
        None, norm_expected, norm_actual
    ).ratio()

    matched = similarity >= FUZZY_MATCH_THRESHOLD

    logger.info(
        "[SampleValidation] Sample %d: similarity=%.3f matched=%s "
        "expected=%r actual=%r",
        sample_number,
        similarity,
        matched,
        norm_expected[:60],
        norm_actual[:60],
    )

    return {
        "matched": matched,
        "transcription": transcription,
        "similarity": round(similarity, 4),
        "sample_number": sample_number,
    }
