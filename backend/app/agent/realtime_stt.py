"""OpenAI Realtime API — STT-only session wrapper.

Replaces the custom energy-based VAD + manual Whisper call pipeline.
Streams incoming WAV chunks to OpenAI's server VAD, which detects speech
boundaries and fires a transcription.completed event via the embedded
Whisper model.

Typical lifecycle per verified agent session
--------------------------------------------
1. ``stt = RealtimeSTTSession(api_key, on_transcript, on_speech_started)``
2. ``await stt.start()``                 # opens Realtime API WebSocket
3. ``await stt.send_audio(wav_bytes)``   # called for every 100 ms chunk
4. OpenAI server VAD fires callbacks as speech is detected / completed.
5. ``await stt.close()``                 # on WebSocket disconnect / logout
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
from typing import Awaitable, Callable, Optional

import numpy as np
import soundfile as sf
import websockets
import websockets.exceptions

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_REALTIME_URL = (
    "wss://api.openai.com/v1/realtime"
    "?model=gpt-4o-realtime-preview-2024-12-17"
)

# Sample rate our frontend sends (16 kHz) vs what the Realtime API expects (24 kHz).
_ORIG_SR: int = 16_000
_TARGET_SR: int = 24_000

# Session update payload: configure STT-only mode.
#   - modalities: ["text"]       → no audio response from the LLM
#   - create_response: false     → server VAD does NOT auto-generate model replies
#   - server_vad                 → OpenAI detects speech end; triggers Whisper
_SESSION_UPDATE: dict = {
    "type": "session.update",
    "session": {
        "modalities": ["text"],
        "instructions": "",
        "input_audio_format": "pcm16",
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "silence_duration_ms": 1200,
            "prefix_padding_ms": 300,
            "create_response": False,
        },
        "input_audio_transcription": {
            "model": "whisper-1",
            "language": "en",
        },
    },
}


# ---------------------------------------------------------------------------
# Audio conversion helpers
# ---------------------------------------------------------------------------

def _resample_linear(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample *samples* from *orig_sr* to *target_sr* using linear interpolation.

    Does not require scipy — uses ``numpy.interp``.
    """
    if orig_sr == target_sr:
        return samples
    target_len = int(len(samples) * target_sr / orig_sr)
    if target_len == 0:
        return np.zeros(0, dtype=np.float32)
    x_orig = np.arange(len(samples), dtype=np.float64)
    x_target = np.linspace(0.0, len(samples) - 1, target_len)
    return np.interp(x_target, x_orig, samples).astype(np.float32)


def _float32_to_pcm16_bytes(samples: np.ndarray) -> bytes:
    """Convert float32 [-1, 1] PCM samples to little-endian int16 bytes."""
    samples = np.clip(samples, -1.0, 1.0)
    return (samples * 32767.0).astype("<i2").tobytes()


def _wav_bytes_to_realtime_pcm(audio_bytes: bytes) -> bytes:
    """Decode WAV/raw bytes → 24 kHz int16 PCM bytes expected by the Realtime API.

    Steps:
    1. Decode via soundfile (handles WAV headers produced by the browser).
    2. Resample from 16 kHz → 24 kHz using linear interpolation.
    3. Convert float32 → int16 little-endian.
    """
    try:
        samples, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=False)
        # If mono is returned as 2-D, flatten
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        resampled = _resample_linear(samples, orig_sr=sr or _ORIG_SR, target_sr=_TARGET_SR)
        return _float32_to_pcm16_bytes(resampled)
    except Exception as exc:
        logger.debug("[RealtimeSTT] Audio decode error (skipping chunk): %s", exc)
        return b""


# ---------------------------------------------------------------------------
# RealtimeSTTSession
# ---------------------------------------------------------------------------

class RealtimeSTTSession:
    """Manages a single OpenAI Realtime API WebSocket for STT.

    Receives WAV audio chunks, streams them to the Realtime API, and fires:
    - ``on_speech_started()``       when the server VAD detects speech.
    - ``on_transcript(text: str)``  when Whisper returns a full utterance.

    Both callbacks must be async callables (coroutines or ``asyncio.Task``
    factories).
    """

    def __init__(
        self,
        api_key: str,
        on_transcript: Callable[[str], Awaitable[None]],
        on_speech_started: Callable[[], Awaitable[None]],
    ) -> None:
        self._api_key = api_key
        self._on_transcript = on_transcript
        self._on_speech_started = on_speech_started

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._started: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Open the Realtime API WebSocket and configure the session.

        Safe to call only once per instance.  Subsequent calls are no-ops.
        """
        if self._started:
            return
        self._started = True  # mark early to prevent duplicate start races

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        try:
            self._ws = await websockets.connect(
                _REALTIME_URL,
                additional_headers=headers,
                max_size=10 * 1024 * 1024,
                open_timeout=10,
            )
            # Consume the initial "session.created" event before configuring.
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
            first_event = json.loads(raw)
            logger.info(
                "[RealtimeSTT] Connected | initial_event_type=%s",
                first_event.get("type"),
            )

            # Configure STT-only mode (server VAD + Whisper, no auto-reply).
            await self._ws.send(json.dumps(_SESSION_UPDATE))

            # Start the background event listener.
            self._listener_task = asyncio.create_task(
                self._listen(), name="realtime_stt_listener"
            )
            logger.info("[RealtimeSTT] Session ready")

        except Exception as exc:
            logger.error("[RealtimeSTT] start() failed: %s", exc)
            self._started = False
            self._ws = None

    async def close(self) -> None:
        """Gracefully cancel the listener and close the WebSocket."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        logger.info("[RealtimeSTT] Session closed")

    # ------------------------------------------------------------------
    # Audio streaming
    # ------------------------------------------------------------------

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Accept WAV bytes, convert to 24 kHz PCM16, send to Realtime API.

        Called for every 100 ms audio chunk from the browser.
        Returns silently if the session is not yet started or already closed.
        """
        if not self._started or self._ws is None:
            return
        pcm16 = _wav_bytes_to_realtime_pcm(audio_bytes)
        if not pcm16:
            return
        audio_b64 = base64.b64encode(pcm16).decode("ascii")
        try:
            await self._ws.send(
                json.dumps({"type": "input_audio_buffer.append", "audio": audio_b64})
            )
        except websockets.exceptions.ConnectionClosed:
            logger.warning("[RealtimeSTT] send_audio: connection already closed")
        except Exception as exc:
            logger.warning("[RealtimeSTT] send_audio error: %s", exc)

    # ------------------------------------------------------------------
    # Event listener (background task)
    # ------------------------------------------------------------------

    async def _listen(self) -> None:
        """Receive and dispatch events from the Realtime API.

        Runs as a long-lived asyncio Task for the lifetime of the session.
        """
        assert self._ws is not None  # guaranteed by start()
        try:
            async for raw in self._ws:
                try:
                    event = json.loads(raw)
                except (json.JSONDecodeError, Exception):
                    continue

                etype: str = event.get("type", "")

                if etype == "input_audio_buffer.speech_started":
                    logger.info("[RealtimeSTT] Speech detected — forwarding agent_listening")
                    try:
                        await self._on_speech_started()
                    except Exception as cb_exc:
                        logger.warning("[RealtimeSTT] on_speech_started error: %s", cb_exc)

                elif etype == "conversation.item.input_audio_transcription.completed":
                    transcript: str = event.get("transcript", "").strip()
                    logger.info("[RealtimeSTT] Whisper transcript: %r", transcript)
                    if transcript:
                        try:
                            await self._on_transcript(transcript)
                        except Exception as cb_exc:
                            logger.error(
                                "[RealtimeSTT] on_transcript callback error: %s", cb_exc
                            )

                elif etype == "error":
                    err = event.get("error", {})
                    logger.error(
                        "[RealtimeSTT] API error: code=%s message=%s",
                        err.get("code"),
                        err.get("message"),
                    )

                # All other events (session.created/updated, speech_stopped,
                # response.*, etc.) are intentionally ignored — we only care
                # about transcription.

        except websockets.exceptions.ConnectionClosed as cc:
            logger.info("[RealtimeSTT] WebSocket closed: %s", cc)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("[RealtimeSTT] Listener crashed: %s", exc)
