from __future__ import annotations

import io
import time
from typing import Optional

import numpy as np
import soundfile as sf


class UtteranceDetector:
    """Energy-based Voice Activity Detector.

    Accumulates **decoded PCM samples** while speech is active (or in the
    silence window after speech).  On utterance completion the accumulated
    samples are re-encoded as a single, self-consistent WAV file and returned.

    Accumulating raw PCM instead of raw bytes avoids the common bug where
    each incoming 100 ms chunk carries its own RIFF/WAV header — concatenating
    those headers produces an invalid file that Whisper cannot parse.

    Return value of process_chunk()
    --------------------------------
    (speech_just_started, utterance_complete, captured_audio)

    speech_just_started : True on the very first chunk where speech is
                          detected (RMS crosses threshold from silence).
    utterance_complete  : True when an utterance has just finished (speech
                          followed by >= silence_duration_ms of silence).
                          The captured audio is a valid mono WAV file.
    captured_audio      : Non-empty bytes only when utterance_complete=True.
    """

    def __init__(self, silence_threshold_rms: float, silence_duration_ms: int) -> None:
        self._threshold = silence_threshold_rms
        self._silence_duration_ms = silence_duration_ms

        # Per-utterance state — store decoded samples, not raw bytes
        self._sample_chunks: list[np.ndarray] = []
        self._sample_rate: Optional[int] = None
        self._speech_detected: bool = False
        self._last_speech_ts: float = 0.0

    def process_chunk(
        self, audio_bytes: bytes, sample_rate: int
    ) -> tuple[bool, bool, bytes]:
        """Feed a raw audio chunk and detect utterance completion.

        Args:
            audio_bytes: WAV (or raw PCM) bytes for this chunk.
            sample_rate: Expected sample rate of the audio (e.g. 16 000).

        Returns:
            (speech_just_started, utterance_complete, captured_audio)
        """
        # --- Decode audio -------------------------------------------------------
        try:
            samples, detected_sr = sf.read(
                io.BytesIO(audio_bytes),
                dtype="float32",
                always_2d=False,
            )
            # Trust the file header if present, otherwise fall back to argument.
            sr = detected_sr if detected_sr else sample_rate
        except Exception:
            # Undecodable chunk — treat as silence
            samples = np.zeros(1, dtype="float32")
            sr = sample_rate

        if self._sample_rate is None:
            self._sample_rate = sr

        # --- Compute RMS --------------------------------------------------------
        rms: float = float(np.sqrt(np.mean(samples ** 2)))

        now = time.monotonic()

        if rms >= self._threshold:
            speech_just_started = not self._speech_detected
            self._speech_detected = True
            self._last_speech_ts = now
            self._sample_chunks.append(samples)
            return (speech_just_started, False, b"")

        # Below threshold (silence)
        if self._speech_detected:
            # Buffer inter-word silence so Whisper receives continuous audio
            # with natural pauses rather than clipped speech bursts.
            self._sample_chunks.append(samples)

            if (now - self._last_speech_ts) * 1000 >= self._silence_duration_ms:
                # Utterance complete — encode accumulated samples as one WAV
                captured = self._encode_wav()
                self._sample_chunks = []
                self._sample_rate = None
                self._speech_detected = False
                self._last_speech_ts = 0.0
                return (False, True, captured)

        return (False, False, b"")

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _encode_wav(self) -> bytes:
        """Concatenate all buffered PCM chunks and encode as a WAV byte string."""
        if not self._sample_chunks:
            return b""
        combined = np.concatenate(self._sample_chunks).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, combined, self._sample_rate or 16000, format="WAV", subtype="FLOAT")
        return buf.getvalue()
