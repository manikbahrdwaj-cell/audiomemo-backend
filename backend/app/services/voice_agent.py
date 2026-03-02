from __future__ import annotations

import asyncio
import base64
import logging
from typing import Callable

from langchain_core.messages import AIMessage
from websockets.exceptions import ConnectionClosed

import app.agent.session_cache as session_cache
from app.agent.graph import get_graph
from app.agent.realtime_stt import RealtimeSTTSession
from app.agent.tts import PROMPT_ASK_AGAIN, PROMPT_NOT_VERIFIED, synthesise_speech
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceAgentOrchestrator:
    """Orchestrates the voice-agent pipeline using OpenAI Realtime API for STT.

    For each audio chunk received over the WebSocket it:
    1. Guards against unverified sessions — sends a TTS prompt to authenticate.
    2. Stores the current send_ws callable so async callbacks can reach the client.
    3. Lazily creates a ``RealtimeSTTSession`` (on first chunk) which opens a
       persistent Realtime API WebSocket that handles server-side VAD + Whisper.
    4. Forwards the 100 ms WAV chunk to the Realtime API (decoded → 24 kHz PCM16).
    5. When OpenAI fires a transcription.completed event the ``_handle_transcript``
       callback asynchronously runs the LangGraph pipeline and replies via TTS.
    """

    async def process_audio_chunk(
        self,
        client_id: str,
        audio_bytes: bytes,
        sample_rate: int,
        send_ws: Callable,
    ) -> None:
        """Process one audio chunk for *client_id*.

        Args:
            client_id:   WebSocket connection identifier (matches session cache key).
            audio_bytes: Raw WAV bytes for this 100 ms chunk.
            sample_rate: Sample rate declared by the sender (e.g. 16 000 Hz).
            send_ws:     Async-or-sync callable that sends a JSON-serialisable
                         dict to the client over the WebSocket.
        """
        # ------------------------------------------------------------------
        # 1. Guard: session must exist and be verified
        # ------------------------------------------------------------------
        session = session_cache.get(client_id)
        if session is None or not session.get("verified"):
            logger.warning(
                "[Agent] client_id=%s not verified or missing session — rejecting", client_id
            )
            tts_bytes = await synthesise_speech(PROMPT_NOT_VERIFIED)
            await _send(send_ws, {
                "type": "agent_audio",
                "data": base64.b64encode(tts_bytes).decode(),
            })
            return

        # ------------------------------------------------------------------
        # 2. Keep send_ws up-to-date so transcript callbacks can reach the client.
        # ------------------------------------------------------------------
        session_cache.update(client_id, send_ws=send_ws)

        # ------------------------------------------------------------------
        # 3. Lazily create the RealtimeSTTSession on the very first chunk.
        #    Mark it in the cache *before* awaiting start() so a second
        #    concurrent chunk cannot race into a duplicate creation.
        # ------------------------------------------------------------------
        if session.get("realtime_stt") is None:
            stt = RealtimeSTTSession(
                api_key=settings.OPENAI_API_KEY,
                on_transcript=lambda text: asyncio.create_task(
                    _handle_transcript(client_id, text)
                ),
                on_speech_started=lambda: asyncio.create_task(
                    _on_speech_started(client_id)
                ),
            )
            # Store immediately (before awaiting) to prevent duplicate init races.
            session_cache.update(client_id, realtime_stt=stt)
            await stt.start()
            logger.info(
                "[Agent] RealtimeSTTSession started | client_id=%s", client_id
            )
            # Refresh local reference after update.
            session = session_cache.get(client_id)

        # ------------------------------------------------------------------
        # 4. Forward audio to the Realtime API.
        #    The API's server VAD will fire callbacks asynchronously.
        # ------------------------------------------------------------------
        realtime_stt = session.get("realtime_stt")
        if realtime_stt is not None:
            await realtime_stt.send_audio(audio_bytes)


# ---------------------------------------------------------------------------
# Async callbacks fired by RealtimeSTTSession
# ---------------------------------------------------------------------------

async def _on_speech_started(client_id: str) -> None:
    """Tell the frontend the agent is now listening."""
    session = session_cache.get(client_id)
    if session and session.get("send_ws"):
        await _send(session["send_ws"], {"type": "agent_listening"})


async def _handle_transcript(client_id: str, transcription: str) -> None:
    """Handle a completed utterance — runs LangGraph + TTS pipeline.

    Called asynchronously from the Realtime API listener task when Whisper
    has finished transcribing the user's utterance.
    """
    session = session_cache.get(client_id)
    if session is None:
        logger.warning("[Agent] _handle_transcript: session %s gone", client_id)
        return

    send_ws = session.get("send_ws")
    if send_ws is None:
        logger.warning("[Agent] _handle_transcript: no send_ws for %s", client_id)
        return

    # ------------------------------------------------------------------
    # Reject unintelligible / noise results
    # ------------------------------------------------------------------
    if len(transcription.split()) < 2:
        logger.info(
            "[Agent] STT result too short — asking again | client_id=%s transcript=%r",
            client_id, transcription,
        )
        tts_bytes = await synthesise_speech(PROMPT_ASK_AGAIN)
        await _send(send_ws, {
            "type": "agent_audio",
            "data": base64.b64encode(tts_bytes).decode(),
        })
        return

    logger.info("[Agent] User said: %r | client_id=%s", transcription, client_id)

    # ------------------------------------------------------------------
    # Signal "thinking" to the frontend
    # ------------------------------------------------------------------
    logger.info("[Agent] → Invoking LangGraph pipeline | client_id=%s", client_id)
    await _send(send_ws, {"type": "agent_thinking"})

    # ------------------------------------------------------------------
    # Build initial graph state
    # ------------------------------------------------------------------
    initial_state = {
        "messages": [],
        "user_phone": session["phone_number"],
        "user_id": session["user_id"],
        "utterance": transcription,
        "generated_sql": "",
        "sql_result": "",
        "error_count": 0,
        "intent": "",          # set to "data_query" or "off_topic" by guardrail node
        "conversation_history": list(session["conversation_history"]),
    }

    # ------------------------------------------------------------------
    # Invoke LangGraph pipeline
    # ------------------------------------------------------------------
    spoken: str
    try:
        final_state = await get_graph().ainvoke(initial_state)
        spoken = _extract_last_ai_message(final_state.get("messages", []))
        logger.info(
            "[Agent] Pipeline complete | client_id=%s\n"
            "  generated_sql : %s\n"
            "  sql_result    : %.200s\n"
            "  spoken        : %r",
            client_id,
            final_state.get("generated_sql", ""),
            final_state.get("sql_result", ""),
            spoken,
        )
    except ValueError as exc:
        logger.warning(
            "[Agent] LangGraph pipeline error | client_id=%s error=%s", client_id, exc
        )
        spoken = "Sorry, I could not process that safely."

    # ------------------------------------------------------------------
    # Persist turn in conversation_history
    # ------------------------------------------------------------------
    updated_history = list(session["conversation_history"]) + [
        {"role": "user", "text": transcription},
        {"role": "assistant", "text": spoken},
    ]
    session_cache.update(client_id, conversation_history=updated_history)

    # ------------------------------------------------------------------
    # Synthesise TTS and send agent_audio back to client
    # ------------------------------------------------------------------
    logger.info("[Agent] ← Responding: %r | client_id=%s", spoken, client_id)
    tts_bytes = await synthesise_speech(spoken)
    await _send(send_ws, {
        "type": "agent_audio",
        "data": base64.b64encode(tts_bytes).decode(),
        "transcript": transcription,
        "text": spoken,
    })


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _extract_last_ai_message(messages: list) -> str:
    """Return the content of the last AIMessage, or a fallback string."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg.content
    return "I'm sorry, I didn't get a response."


async def _send(send_ws: Callable, payload: dict) -> None:
    """Call *send_ws* whether it is a coroutine function or a plain callable.

    Silently swallows closed-connection errors so a client disconnect does
    not crash the agent worker.
    """
    try:
        if asyncio.iscoroutinefunction(send_ws):
            await send_ws(payload)
        else:
            send_ws(payload)
    except ConnectionClosed:
        pass
    except RuntimeError as exc:
        if "not connected" in str(exc).lower() or "disconnect" in str(exc).lower():
            pass
        else:
            raise


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_orchestrator: VoiceAgentOrchestrator | None = None


def get_voice_agent() -> VoiceAgentOrchestrator:
    """Return the VoiceAgentOrchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = VoiceAgentOrchestrator()
    return _orchestrator
