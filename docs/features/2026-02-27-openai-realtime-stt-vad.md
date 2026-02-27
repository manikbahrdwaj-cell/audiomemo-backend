# Replace Custom VAD with OpenAI Realtime API Server VAD

**Date:** 2026-02-27

## Feature Summary

Replace the custom energy-based `UtteranceDetector` (VAD) + manual Whisper call pipeline with
OpenAI's Realtime API server-side VAD. The Realtime API streams raw PCM audio, uses an
ML-based VAD to detect utterance boundaries, and fires a `conversation.item.input_audio_transcription.completed`
event with the Whisper transcript — eliminating the need for our own RMS threshold logic.

## Architecture

| Layer | Change |
|---|---|
| `ml/` | `vad.py` kept but no longer called in agent mode |
| `agent/` | New `realtime_stt.py` — `RealtimeSTTSession` class |
| `services/` | `voice_agent.py` — swap VAD path for RealtimeSTT path |
| `agent/` | `session_cache.py` — replace `vad` with `realtime_stt` + `send_ws` |
| frontend | No change — WAV chunks still sent at 100ms; backend decodes+resamples |

## New Files
- `backend/app/agent/realtime_stt.py` — `RealtimeSTTSession`, `_wav_bytes_to_pcm16()`

## Modified Files
- `backend/app/services/voice_agent.py` — lazy creation + audio forwarding; `_handle_transcript` callback
- `backend/app/agent/session_cache.py` — `set_verified` removes `vad`, adds `realtime_stt`/`send_ws`

## API Contract
Internal only — no new HTTP endpoints. WebSocket messages unchanged:
- `agent_listening` — sent when Realtime API fires `speech_started`
- `agent_thinking` — sent after transcript received, before LangGraph
- `agent_audio` — sent with TTS bytes and text after LangGraph completes

## Dependencies
No new packages — uses existing `websockets==12.0`, `openai>=1.30`, `numpy`, `soundfile`.

## Test Plan
1. Verify session: biometric pass → agent mode kicks in
2. Speak a complete sentence → exactly one `agent_audio` reply (no fragments)
3. Speak mid-sentence, pause 2s, finish → should wait for full utterance
4. Disconnect mid-session → no crash

## Task List

```json
{
  "id": "T01",
  "title": "Create RealtimeSTTSession class",
  "type": "feature",
  "priority": "high",
  "layer": "ml",
  "file": "backend/app/agent/realtime_stt.py",
  "function_or_class": "RealtimeSTTSession",
  "description": "Create a new file that manages a single OpenAI Realtime API WebSocket per verified session. On start(), connect to wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17 with headers Authorization + OpenAI-Beta. Send session.update to configure server_vad (threshold=0.5, silence_duration_ms=1200, create_response=false) with whisper-1 transcription. A background _listen() task fires on_speech_started() on speech_started events and on_transcript(text) on transcription.completed. send_audio(wav_bytes) decodes WAV→float32, resamples 16kHz→24kHz with numpy, converts to int16, sends as input_audio_buffer.append. close() cleanly cancels the listener and closes the socket.",
  "depends_on": [],
  "context_files": ["backend/app/agent/vad.py", "backend/app/agent/stt.py", "backend/app/core/config.py"],
  "acceptance_criteria": [
    "Connects and keeps WebSocket open until close() is called",
    "on_transcript fires with full sentence when user stops speaking",
    "on_speech_started fires when speech begins",
    "send_audio handles WAV bytes from existing audioChunkingService"
  ],
  "estimated_lines_changed": 110
}
```

```json
{
  "id": "T02",
  "title": "Update session_cache for RealtimeSTT",
  "type": "refactor",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/session_cache.py",
  "function_or_class": "set_verified",
  "description": "Replace the `vad: UtteranceDetector(...)` entry with `realtime_stt: None` (populated lazily in voice_agent) and `send_ws: None` (populated on first audio chunk). The delete() function must schedule stt.close() if realtime_stt is set before popping from cache.",
  "depends_on": ["T01"],
  "context_files": ["backend/app/agent/realtime_stt.py"],
  "acceptance_criteria": [
    "set_verified no longer instantiates UtteranceDetector",
    "delete() closes the RealtimeSTTSession via asyncio task"
  ],
  "estimated_lines_changed": 20
}
```

```json
{
  "id": "T03",
  "title": "Rewrite VoiceAgentOrchestrator for RealtimeSTT",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/services/voice_agent.py",
  "function_or_class": "VoiceAgentOrchestrator.process_audio_chunk",
  "description": "process_audio_chunk now: (1) verifies session, (2) stores send_ws in cache, (3) lazily creates RealtimeSTTSession with on_transcript→_handle_transcript and on_speech_started→_on_speech_started callbacks, (4) calls session.realtime_stt.send_audio(audio_bytes). Extract LangGraph+TTS pipeline into free function _handle_transcript(client_id, transcription) which is called asynchronously from the Realtime API listener task.",
  "depends_on": ["T01", "T02"],
  "context_files": ["backend/app/agent/realtime_stt.py", "backend/app/agent/session_cache.py", "backend/app/agent/graph.py"],
  "acceptance_criteria": [
    "process_audio_chunk returns immediately after forwarding audio",
    "_handle_transcript runs full LangGraph + TTS pipeline",
    "No direct VAD or Whisper calls remain in this file"
  ],
  "estimated_lines_changed": 60
}
```
