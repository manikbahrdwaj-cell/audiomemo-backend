from __future__ import annotations

import io
import time

import numpy as np
import soundfile as sf


class UtteranceDetector:
    """Energy-based Voice Activity Detector.

    Accumulates audio while speech is detected (RMS >= threshold).
    Returns the captured audio once a sustained silence of
    *silence_duration_ms* milliseconds has followed the speech burst.
    """

    def __init__(self, silence_threshold_rms: float, silence_duration_ms: int) -> None:
        self._threshold = silence_threshold_rms
        self._silence_duration_ms = silence_duration_ms

        # Per-utterance state
        self._buffer: bytes = b""
        self._speech_detected: bool = False
        self._last_speech_ts: float = 0.0

    def process_chunk(self, audio_bytes: bytes, sample_rate: int) -> tuple[bool, bytes]:
        """Feed a raw audio chunk and detect utterance completion.

        Args:
            audio_bytes: Raw PCM / WAV bytes for this chunk.
            sample_rate:  Sample rate of the audio (e.g. 16000).

        Returns:
            (True, captured_audio) when an utterance has just completed
            (speech followed by >= silence_duration_ms of silence).
            (False, b'') in all other cases.
        """
        # --- Decode audio -------------------------------------------------------
        try:
            samples, _ = sf.read(
                io.BytesIO(audio_bytes),
                dtype="float32",
                always_2d=False,
            )
        except Exception:
            # Undecodable chunk — treat as silence
            samples = np.zeros(1, dtype="float32")

        # --- Compute RMS --------------------------------------------------------
        rms: float = float(np.sqrt(np.mean(samples ** 2)))

        now = time.monotonic()

        if rms >= self._threshold:
            # Active speech
            self._speech_detected = True
            self._last_speech_ts = now
            self._buffer += audio_bytes
            return (False, b"")

        # Below threshold (silence)
        if (
            self._speech_detected
            and (now - self._last_speech_ts) * 1000 >= self._silence_duration_ms
        ):
            # Utterance complete — capture and reset
            captured = self._buffer
            self._buffer = b""
            self._speech_detected = False
            self._last_speech_ts = 0.0
            return (True, captured)

        return (False, b"")
