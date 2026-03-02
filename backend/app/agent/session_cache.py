from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}


def set_verified(client_id: str, phone_number: str, user_id: str) -> None:
    """Create (or overwrite) a verified session entry for *client_id*.

    Args:
        client_id:    WebSocket session identifier (used as cache key).
        phone_number: Human-readable phone number (kept for display/logging).
        user_id:      str(_id) of the voice_embeddings document — the
                      immutable identifier used to scope transaction queries.
    """
    _cache[client_id] = {
        "verified": True,
        "phone_number": phone_number,
        "user_id": user_id,
        # realtime_stt: RealtimeSTTSession — created lazily on first audio chunk
        # inside voice_agent.py so the event loop is running when start() is called.
        "realtime_stt": None,
        # send_ws: stored on each process_audio_chunk call so callbacks can
        # reach the WebSocket after an async transcript event fires.
        "send_ws": None,
        "conversation_history": [],
        # tts_playing: True while agent TTS audio is being played on the client.
        # Audio chunks are suppressed during this window to prevent STT from
        # transcribing the speaker echo back into the pipeline.
        "tts_playing": False,
    }


def get(client_id: str) -> dict | None:
    """Return the session dict for *client_id*, or None if not present."""
    return _cache.get(client_id)


def delete(client_id: str) -> None:
    """Remove the session entry for *client_id* and close any Realtime STT session."""
    entry = _cache.pop(client_id, None)
    if entry is None:
        return
    stt = entry.get("realtime_stt")
    if stt is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(stt.close())
        except Exception as exc:
            logger.warning("[SessionCache] Failed to schedule stt.close(): %s", exc)


def update(client_id: str, **kwargs) -> None:
    """Merge *kwargs* into an existing session entry.

    No-op when *client_id* is not in the cache.
    """
    entry = _cache.get(client_id)
    if entry is None:
        return
    entry.update(kwargs)
