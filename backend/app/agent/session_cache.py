from __future__ import annotations

from app.agent.vad import UtteranceDetector
from app.core.config import settings

_cache: dict[str, dict] = {}


def set_verified(client_id: str, phone_number: str) -> None:
    """Create (or overwrite) a verified session entry for *client_id*."""
    _cache[client_id] = {
        "verified": True,
        "phone_number": phone_number,
        "vad": UtteranceDetector(
            settings.VAD_SILENCE_THRESHOLD_RMS,
            settings.VAD_SILENCE_DURATION_MS,
        ),
        "conversation_history": [],
    }


def get(client_id: str) -> dict | None:
    """Return the session dict for *client_id*, or None if not present."""
    return _cache.get(client_id)


def delete(client_id: str) -> None:
    """Remove the session entry for *client_id* (no-op if absent)."""
    _cache.pop(client_id, None)


def update(client_id: str, **kwargs) -> None:
    """Merge *kwargs* into an existing session entry.

    No-op when *client_id* is not in the cache.
    """
    entry = _cache.get(client_id)
    if entry is None:
        return
    entry.update(kwargs)
