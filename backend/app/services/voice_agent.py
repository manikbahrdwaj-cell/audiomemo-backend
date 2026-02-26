from __future__ import annotations

import base64
import logging
from typing import Callable

from langchain_core.messages import AIMessage

import app.agent.session_cache as session_cache
from app.agent.graph import get_graph
from app.agent.stt import transcribe_audio
from app.agent.tts import PROMPT_ASK_AGAIN, PROMPT_NOT_VERIFIED, synthesise_speech

logger = logging.getLogger(__name__)


class VoiceAgentOrchestrator:
    """Orchestrates the full voice-agent pipeline for a verified session.

    For each audio chunk received over the WebSocket it:
    1. Guards against unverified sessions — sends a TTS prompt to authenticate.
    2. Feeds the chunk to the per-session VAD; waits silently until an
       utterance is complete.
    3. Transcribes the captured utterance with Whisper.
    4. Rejects unintelligible / noise chunks with a TTS prompt.
    5. Invokes the LangGraph pipeline (SQL compile → security check →
       MCP execute → response shape).
    6. Updates ``conversation_history`` in the session cache.
    7. Synthesises the spoken response with OpenAI TTS and sends it over the
       WebSocket as an ``agent_audio`` message.
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
            audio_bytes: Raw audio bytes for this chunk.
            sample_rate: Sample rate of the audio, e.g. 16 000 Hz.
            send_ws:     Async-or-sync callable that sends a JSON-serialisable
                         dict to the client over the WebSocket.
        """
        # ------------------------------------------------------------------
        # 1. Guard: session must exist and be verified
        # ------------------------------------------------------------------
        session = session_cache.get(client_id)
        if session is None or not session.get("verified"):
            tts_bytes = await synthesise_speech(PROMPT_NOT_VERIFIED)
            await _send(send_ws, {
                "type": "agent_audio",
                "data": base64.b64encode(tts_bytes).decode(),
            })
            return

        # ------------------------------------------------------------------
        # 2. Feed chunk to VAD; wait until utterance is complete
        # ------------------------------------------------------------------
        utterance_complete, captured_audio = session["vad"].process_chunk(
            audio_bytes, sample_rate
        )
        if not utterance_complete:
            return

        # ------------------------------------------------------------------
        # 3. Signal "thinking" to the frontend
        # ------------------------------------------------------------------
        await _send(send_ws, {"type": "agent_thinking"})

        # ------------------------------------------------------------------
        # 4. Transcribe with Whisper; reject short / noise results
        # ------------------------------------------------------------------
        transcription = await transcribe_audio(captured_audio)
        if len(transcription.split()) < 3:
            tts_bytes = await synthesise_speech(PROMPT_ASK_AGAIN)
            await _send(send_ws, {
                "type": "agent_audio",
                "data": base64.b64encode(tts_bytes).decode(),
            })
            return  # conversation_history NOT updated

        # ------------------------------------------------------------------
        # 5. Build initial graph state (snapshot conversation_history)
        # ------------------------------------------------------------------
        initial_state = {
            "messages": [],
            "user_phone": session["phone_number"],
            "utterance": transcription,
            "generated_sql": "",
            "sql_result": "",
            "error_count": 0,
            "conversation_history": list(session["conversation_history"]),
        }

        # ------------------------------------------------------------------
        # 6. Invoke LangGraph pipeline
        # ------------------------------------------------------------------
        spoken: str
        try:
            final_state = await get_graph().ainvoke(initial_state)
            # Extract the last AIMessage from the messages list
            spoken = _extract_last_ai_message(final_state.get("messages", []))
        except ValueError as exc:
            logger.warning("LangGraph pipeline error for %s: %s", client_id, exc)
            spoken = "Sorry, I could not process that safely."

        # ------------------------------------------------------------------
        # 7. Persist turn in session conversation_history
        # ------------------------------------------------------------------
        updated_history = list(session["conversation_history"]) + [
            {"role": "user", "text": transcription},
            {"role": "assistant", "text": spoken},
        ]
        session_cache.update(client_id, conversation_history=updated_history)

        # ------------------------------------------------------------------
        # 8. Synthesise TTS and send agent_audio back to client
        # ------------------------------------------------------------------
        tts_bytes = await synthesise_speech(spoken)
        await _send(send_ws, {
            "type": "agent_audio",
            "data": base64.b64encode(tts_bytes).decode(),
            "transcript": transcription,
            "text": spoken,
        })


def _extract_last_ai_message(messages: list) -> str:
    """Return the content of the last AIMessage, or a fallback string."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg.content
    return "I'm sorry, I didn't get a response."


async def _send(send_ws: Callable, payload: dict) -> None:
    """Call *send_ws* whether it is a coroutine function or a plain callable."""
    import asyncio

    if asyncio.iscoroutinefunction(send_ws):
        await send_ws(payload)
    else:
        send_ws(payload)


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
