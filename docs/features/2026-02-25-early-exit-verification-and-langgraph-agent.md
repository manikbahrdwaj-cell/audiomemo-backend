# Feature: WebSocket-Native Voice Agent with Conversation History

**Date:** 2026-02-25
**Branch:** manik/refactoring

---

## Feature Summary

**WebSocket-Native Voice Agent** — After a session is verified, the same WebSocket connection transparently switches into "agent mode". The backend autonomously detects this switch via an in-memory session cache — the frontend has no role in triggering the agent. Subsequent audio chunks are fed to:

- **VAD** (energy-based Voice Activity Detection) to detect utterance completion (1.5 s of silence after speech)
- **Whisper STT** to transcribe the completed utterance
- A **meaningfulness classifier** to reject noise or filler speech and prompt the user to try again
- **LangGraph** to compile the utterance to a safe, phone-filtered SQL query and retrieve the result — receiving the full conversation history so it can maintain multi-turn context
- **OpenAI TTS** to synthesise the answer, which is sent back over the same WebSocket as audio bytes

If the user is not yet verified when audio arrives in agent mode, a TTS prompt ("Please speak a little more so I can verify you.") is returned instead.

Conversation history (text-only) is persisted in the in-memory session cache for the duration of the WebSocket session. Each completed user utterance and each agent response are appended so that subsequent LangGraph invocations receive full prior context.

---

## Architecture

### Phase 1 — Biometric Verification (existing, unchanged)

```
audio chunks → RealtimeVerificationManager.process_chunk()
                        │
              accumulate up to max_chunks
                        │
              all chunks evaluated → verified / unverified
                        │ verified
                        ▼
             write to AgentSessionCache
             send TTS greeting over WS
```

### Phase 2 — Voice Agent (same WebSocket, same `audio` message type)

```
                        ┌──────────────────────────────────────────────────────┐
  frontend sends        │  WebSocketEventHandler.handle_audio_chunk()          │
  {type:"audio", …}  ──►│                                                      │
  (unchanged message)   │  AgentSessionCache.get(client_id)                    │
                        │       │ verified=False                               │
                        │       ▼                                              │
                        │  TTS "Speak more to verify" → send_agent_audio()     │
                        │                                                      │
                        │       │ verified=True                                │
                        │       ▼                                              │
                        │  VoiceAgentOrchestrator.feed_chunk(client_id, audio) │
                        │       │                                              │
                        │  VAD: accumulate audio; silence > 1.5 s?            │
                        │       │ not yet → ACK only                           │
                        │       │ utterance_complete                           │
                        │       ▼                                              │
                        │  Whisper STT → transcription                         │
                        │       │                                              │
                        │  meaningfulness_check(transcription)                 │
                        │       │ not meaningful                               │
                        │       ▼                                              │
                        │  TTS "I didn't catch that. Ask again." → WS          │
                        │       │ meaningful                                   │
                        │       ▼                                              │
                        │  append utterance to session conversation_history    │
                        │       │                                              │
                        │  LangGraph(user_phone, utterance,                    │
                        │            conversation_history)                     │
                        │     query_compiler → security_supervisor             │
                        │       └─(fail/retry ≤3)──► query_compiler           │
                        │         └─(pass)──► tool_executor(MCP)              │
                        │                       └──► response_shaper(LLM)     │
                        │       │ spoken_text                                  │
                        │       ▼                                              │
                        │  append spoken_text to session conversation_history  │
                        │       │                                              │
                        │  OpenAI TTS → mp3 bytes → send_agent_audio() → WS   │
                        └──────────────────────────────────────────────────────┘
```

### Session Cache (in-memory, keyed by WebSocket `client_id`)

```python
{
  "<client_id>": {
    "verified": bool,
    "phone_number": str,           # populated on verification success
    "vad": UtteranceDetector,      # per-client VAD instance (owns buffer + flags)
    "conversation_history": list,  # text-only turn history for this session
    # Each entry: {"role": "user" | "assistant", "text": str}
  }
}
```

`conversation_history` starts as an empty list when the session is first created and grows with each completed turn. It is passed verbatim to every LangGraph invocation so the query_compiler node can reference prior questions and the response_shaper can give contextually coherent answers. History is never persisted to the database — it lives only for the duration of the WebSocket connection.

The cache is process-local (dict singleton). It is written by `verification_streaming.py` on verification success and read by `VoiceAgentOrchestrator` on every subsequent audio chunk. No DB round-trip per chunk.

### WebSocket Message Contract (additions — server → client only)

| Type | Payload | When sent |
|---|---|---|
| `agent_audio` | `{type, data: base64-mp3, transcript: str, text: str}` | After TTS is ready |
| `agent_listening` | `{type}` | VAD detects start of speech |
| `agent_thinking` | `{type}` | After STT, before graph completes |

The frontend continues sending the same `{type: "audio", data: "<base64-wav>"}` chunks. **No frontend change required.**

---

## New Files

| File | Purpose |
|---|---|
| `backend/app/agent/__init__.py` | Package marker |
| `backend/app/agent/session_cache.py` | In-memory session state singleton (includes conversation_history) |
| `backend/app/agent/vad.py` | Energy-based VAD and utterance completion detector |
| `backend/app/agent/stt.py` | Whisper STT via OpenAI API |
| `backend/app/agent/tts.py` | OpenAI TTS — text → mp3 bytes |
| `backend/app/agent/state.py` | `AgentState` TypedDict for LangGraph (includes conversation_history) |
| `backend/app/agent/llm.py` | `build_llm()` factory — OpenAI or Gemini |
| `backend/app/agent/nodes/__init__.py` | Package marker |
| `backend/app/agent/nodes/query_compiler.py` | LLM node — NL → SQL, uses conversation_history for context |
| `backend/app/agent/nodes/security_supervisor.py` | Python node — SQL safety |
| `backend/app/agent/nodes/tool_executor.py` | MCP node — SQL execution |
| `backend/app/agent/nodes/response_shaper.py` | LLM node — result → spoken sentence |
| `backend/app/agent/graph.py` | Compiles the LangGraph state machine |
| `backend/app/services/voice_agent.py` | Orchestrator: VAD → STT → graph → TTS, manages conversation_history |

---

## Modified Files

| File | Why |
|---|---|
| `backend/app/core/config.py` | `OPENAI_API_KEY`, `LLM_PROVIDER`, `GOOGLE_PROJECT_ID`, `DATABASE_URL`, `VAD_SILENCE_THRESHOLD_RMS`, `VAD_SILENCE_DURATION_MS` |
| `backend/app/services/verification_streaming.py` | Write to `AgentSessionCache` on verification success (T17) |
| `backend/app/websocket/events.py` | Route audio to `VoiceAgentOrchestrator` when session is in cache (T18) |
| `backend/requirements.txt` | `langgraph`, `langchain-openai`, `langchain-google-vertexai`, `mcp`, `openai>=1.30` |

---

## WebSocket Message Contract (additions)

No new REST endpoints. Everything flows over the existing WebSocket connection.

### Server → Client (new message types)

```json
{ "type": "agent_audio", "data": "<base64-mp3>", "transcript": "...", "text": "..." }
{ "type": "agent_listening" }
{ "type": "agent_thinking" }
```

### Client → Server (unchanged)

```json
{ "type": "audio", "data": "<base64-wav>" }
```

---

## Dependencies

```
langgraph>=0.2
langchain>=0.2
langchain-openai>=0.1
langchain-google-vertexai>=1.0
mcp>=1.0
openai>=1.30          # Whisper STT + TTS
```

New `.env` keys:
```
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai              # or "gemini"
GOOGLE_PROJECT_ID=my-gcp-project # only when LLM_PROVIDER=gemini
DATABASE_URL=postgresql://...    # used by MCP tool
VAD_SILENCE_THRESHOLD_RMS=0.01   # RMS below this = silence
VAD_SILENCE_DURATION_MS=1500     # silence ms to trigger utterance_complete
```

---

## Test Plan

### Voice Agent
1. Connect via WebSocket, verify a phone number. Assert `AgentSessionCache.get(client_id)["verified"] == True` and `conversation_history == []`.
2. Send audio chunks of a complete spoken query, then 1.5 s silence. Assert an `agent_audio` WS frame is returned.
3. After step 2, assert `conversation_history` has two entries: `{"role": "user", "text": <transcription>}` and `{"role": "assistant", "text": <spoken>}`.
4. Send a follow-up query that references the previous answer. Assert the LangGraph query_compiler receives the full history and generates a contextually correct SQL.
5. Send noise-only audio. Assert `agent_audio` frame contains the PROMPT_ASK_AGAIN TTS. Assert `conversation_history` is NOT appended (non-meaningful input is not stored).
6. Connect unverified, send audio. Assert `agent_audio` contains PROMPT_NOT_VERIFIED TTS.
7. With verified session, mock LangGraph to fail the security check 3 times. Assert `agent_audio` contains an apology TTS.
8. Set `LLM_PROVIDER=gemini`, repeat scenario 2 with mocked Gemini response.

---

## Task List

```json
{
  "id": "T01",
  "title": "Add agent and VAD settings to config",
  "type": "feature",
  "priority": "high",
  "layer": "config",
  "file": "backend/app/core/config.py",
  "function_or_class": "Settings",
  "description": "Add six new fields to the Settings Pydantic model: (1) OPENAI_API_KEY: str = ''; (2) LLM_PROVIDER: str = 'openai' ('openai' or 'gemini'); (3) GOOGLE_PROJECT_ID: str = '' (only needed for Gemini); (4) DATABASE_URL: str = '' (PostgreSQL URL for MCP tool); (5) VAD_SILENCE_THRESHOLD_RMS: float = 0.01 (RMS amplitude below which audio is considered silence); (6) VAD_SILENCE_DURATION_MS: int = 1500 (consecutive silence milliseconds that trigger utterance completion). All fields must have safe defaults so existing tests pass with no .env file present.",
  "depends_on": [],
  "context_files": [
    "backend/app/core/config.py"
  ],
  "acceptance_criteria": [
    "Settings() instantiates without a .env file",
    "All 6 new fields are accessible via settings.<FIELD>",
    "No existing field is removed or renamed"
  ],
  "estimated_lines_changed": 8
}
```

```json
{
  "id": "T04",
  "title": "Add new packages to requirements.txt",
  "type": "feature",
  "priority": "high",
  "layer": "config",
  "file": "backend/requirements.txt",
  "function_or_class": null,
  "description": "Append the following lines to requirements.txt: langgraph>=0.2, langchain>=0.2, langchain-openai>=0.1, langchain-google-vertexai>=1.0, mcp>=1.0, openai>=1.30. The openai package covers Whisper STT (openai.audio.transcriptions.create) and TTS (openai.audio.speech.create). Do not remove any existing dependency. Use >= lower-bound specifiers.",
  "depends_on": [],
  "context_files": [
    "backend/requirements.txt"
  ],
  "acceptance_criteria": [
    "pip install -r requirements.txt completes without conflicts",
    "import openai, import langgraph, import langchain_openai all succeed after install"
  ],
  "estimated_lines_changed": 6
}
```

```json
{
  "id": "T05",
  "title": "Create in-memory agent session cache",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/session_cache.py",
  "function_or_class": "AgentSessionCache",
  "description": "Create backend/app/agent/__init__.py (empty) and backend/app/agent/session_cache.py. Define a module-level _cache: dict[str, dict] = {}. Import UtteranceDetector from agent.vad and settings from core.config. Expose four public functions: (1) set_verified(client_id: str, phone_number: str) -> None — writes {'verified': True, 'phone_number': phone_number, 'vad': UtteranceDetector(settings.VAD_SILENCE_THRESHOLD_RMS, settings.VAD_SILENCE_DURATION_MS), 'conversation_history': []}; (2) get(client_id: str) -> dict | None; (3) delete(client_id: str) -> None; (4) update(client_id: str, **kwargs) -> None — merges kwargs into existing entry, no-op for unknown IDs. No threading.Lock needed. Do not import any service, route, or db layer. The conversation_history list stores dicts of the form {'role': 'user' | 'assistant', 'text': str} and is never persisted to the database.",
  "depends_on": ["T06"],
  "context_files": ["backend/app/agent/vad.py"],
  "acceptance_criteria": [
    "set_verified() creates all four required keys including a fresh UtteranceDetector instance",
    "set_verified() creates conversation_history: []",
    "get() returns None for unknown client_id",
    "update() is a no-op for unknown client_id"
  ],
  "estimated_lines_changed": 40
}
```

```json
{
  "id": "T06",
  "title": "Create energy-based VAD utterance detector",
  "type": "feature",
  "priority": "high",
  "layer": "ml",
  "file": "backend/app/agent/vad.py",
  "function_or_class": "UtteranceDetector",
  "description": "Create backend/app/agent/vad.py. Define class UtteranceDetector with constructor __init__(self, silence_threshold_rms: float, silence_duration_ms: int). Internal instance state: _buffer: bytes = b'', _speech_detected: bool = False, _last_speech_ts: float = 0.0. Public method process_chunk(audio_bytes: bytes, sample_rate: int) -> tuple[bool, bytes]. Behaviour: (1) Read audio_bytes with soundfile into float32 samples. (2) Compute RMS = sqrt(mean(samples**2)). (3) If RMS >= threshold: set self._speech_detected=True, self._last_speech_ts=time.monotonic(), append audio_bytes to self._buffer. (4) If self._speech_detected is True AND RMS < threshold AND (time.monotonic() - self._last_speech_ts) * 1000 >= silence_duration_ms: capture = self._buffer, reset self._buffer=b'', self._speech_detected=False, self._last_speech_ts=0.0, return (True, capture). (5) Otherwise return (False, b''). Do NOT export a singleton — each call to session_cache.set_verified() creates a fresh instance.",
  "depends_on": ["T01"],
  "context_files": [
    "backend/app/core/config.py"
  ],
  "acceptance_criteria": [
    "Returns (False, b'') while buffer is still accumulating",
    "Returns (True, <audio>) after speech followed by VAD_SILENCE_DURATION_MS of silence",
    "Resets all internal state after returning True so next call starts a fresh utterance",
    "process_chunk() takes only audio_bytes and sample_rate — no external state dict"
  ],
  "estimated_lines_changed": 55
}
```

```json
{
  "id": "T07",
  "title": "Create Whisper STT service",
  "type": "feature",
  "priority": "high",
  "layer": "ml",
  "file": "backend/app/agent/stt.py",
  "function_or_class": "transcribe_audio",
  "description": "Create backend/app/agent/stt.py. Define async function transcribe_audio(audio_bytes: bytes, language: str = 'en') -> str. Instantiate AsyncOpenAI(api_key=settings.OPENAI_API_KEY). Call client.audio.transcriptions.create(model='whisper-1', file=('audio.wav', io.BytesIO(audio_bytes), 'audio/wav'), language=language). Return response.text. On any exception, log the error at WARNING level and return '' so callers handle empty transcription gracefully without crashing.",
  "depends_on": ["T01", "T04"],
  "context_files": [
    "backend/app/core/config.py"
  ],
  "acceptance_criteria": [
    "Returns a non-empty string for valid speech audio",
    "Returns '' (not raises) on API error",
    "Uses AsyncOpenAI — fully non-blocking"
  ],
  "estimated_lines_changed": 30
}
```

```json
{
  "id": "T08",
  "title": "Create OpenAI TTS service",
  "type": "feature",
  "priority": "high",
  "layer": "ml",
  "file": "backend/app/agent/tts.py",
  "function_or_class": "synthesise_speech",
  "description": "Create backend/app/agent/tts.py. Define async function synthesise_speech(text: str, voice: str = 'alloy') -> bytes. Instantiate AsyncOpenAI(api_key=settings.OPENAI_API_KEY). Call client.audio.speech.create(model='tts-1', voice=voice, input=text, response_format='mp3'). Read with await response.aread(). Return raw mp3 bytes. On exception, log and return b''. Also define two module-level constants: PROMPT_NOT_VERIFIED = 'Please speak a little more so I can verify your identity.' and PROMPT_ASK_AGAIN = \"I didn't catch a clear question. Could you please ask again?\"",
  "depends_on": ["T01", "T04"],
  "context_files": [
    "backend/app/core/config.py"
  ],
  "acceptance_criteria": [
    "Returns non-empty bytes for valid input text",
    "Returns b'' (not raises) on API error",
    "PROMPT_NOT_VERIFIED and PROMPT_ASK_AGAIN are importable constants",
    "Uses AsyncOpenAI"
  ],
  "estimated_lines_changed": 35
}
```

```json
{
  "id": "T09",
  "title": "Create AgentState TypedDict",
  "type": "feature",
  "priority": "high",
  "layer": "model",
  "file": "backend/app/agent/state.py",
  "function_or_class": "AgentState",
  "description": "Create backend/app/agent/state.py. Define AgentState as a TypedDict with seven fields: messages: Annotated[list[BaseMessage], add_messages] (LangGraph append reducer); user_phone: str (verified phone number from session cache); utterance: str (Whisper transcription of current query); generated_sql: str (output of query_compiler); sql_result: str (JSON string output of tool_executor); error_count: int (incremented by security_supervisor on each retry, max 3); conversation_history: list[dict] (text-only prior turns from the session cache — each entry is {'role': 'user' | 'assistant', 'text': str}, passed in at invocation time, not modified by graph nodes). Import BaseMessage from langchain_core.messages, add_messages from langgraph.graph.message, Annotated from typing.",
  "depends_on": ["T04"],
  "context_files": [],
  "acceptance_criteria": [
    "AgentState importable from app.agent.state",
    "All seven fields present with correct types",
    "messages uses add_messages reducer",
    "conversation_history field is list[dict]"
  ],
  "estimated_lines_changed": 22
}
```

```json
{
  "id": "T10",
  "title": "Create build_llm() factory",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/llm.py",
  "function_or_class": "build_llm",
  "description": "Create backend/app/agent/llm.py. Define build_llm() -> BaseChatModel. Read settings.LLM_PROVIDER. If 'openai': return ChatOpenAI(model='gpt-4o-mini', api_key=settings.OPENAI_API_KEY). If 'gemini': return ChatVertexAI(model='gemini-1.5-flash', project=settings.GOOGLE_PROJECT_ID). Otherwise raise ValueError(f'Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}'). Do not cache at module level — graph.py will call this once at compile time.",
  "depends_on": ["T01", "T04", "T09"],
  "context_files": [
    "backend/app/core/config.py"
  ],
  "acceptance_criteria": [
    "Returns ChatOpenAI when LLM_PROVIDER='openai'",
    "Returns ChatVertexAI when LLM_PROVIDER='gemini'",
    "Raises ValueError for unknown provider"
  ],
  "estimated_lines_changed": 25
}
```

```json
{
  "id": "T11",
  "title": "Create query_compiler node",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/nodes/query_compiler.py",
  "function_or_class": "build_query_compiler_node",
  "description": "Create backend/app/agent/nodes/__init__.py (empty) and backend/app/agent/nodes/query_compiler.py. Define build_query_compiler_node(llm) -> Callable[[AgentState], dict]. The returned async node: (1) builds a system prompt with a hardcoded transactions schema (id, phone_number, amount, merchant, timestamp) and instructs the LLM to produce a SELECT SQL with WHERE phone_number = '{state[user_phone]}'; (2) if state['conversation_history'] is non-empty, serialise it as a formatted prior-turns block (e.g. 'Previous conversation:\\nUser: ...\\nAssistant: ...') and prepend it to the user message so the LLM has full context; (3) appends any SECURITY ERROR SystemMessage from state['messages'] for self-correction; (4) invokes the LLM with state['utterance'] as the current user message; (5) extracts SQL from ```sql...``` fences or takes the full output; (6) returns {'generated_sql': sql}.",
  "depends_on": ["T09", "T10"],
  "context_files": [
    "backend/app/agent/state.py",
    "backend/app/agent/llm.py"
  ],
  "acceptance_criteria": [
    "Returns dict with generated_sql",
    "System prompt includes state['user_phone']",
    "Prior conversation turns injected into prompt when conversation_history is non-empty",
    "SECURITY ERROR messages forwarded for self-correction",
    "SQL extracted correctly from fenced blocks"
  ],
  "estimated_lines_changed": 65
}
```

```json
{
  "id": "T12",
  "title": "Create security_supervisor node",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/nodes/security_supervisor.py",
  "function_or_class": "security_supervisor",
  "description": "Create backend/app/agent/nodes/security_supervisor.py. Define async function security_supervisor(state: AgentState) -> Command (import Command from langgraph.types). Two checks on state['generated_sql']: (1) state['user_phone'] must appear verbatim; (2) none of DELETE/UPDATE/DROP/INSERT/TRUNCATE/ALTER in uppercased SQL. On failure: error_count = state['error_count'] + 1; if error_count >= 3 raise ValueError('SECURITY_MAX_RETRIES'); else return Command(update={'messages': [SystemMessage('SECURITY ERROR: <reason>. Retry.')], 'error_count': error_count}, goto='query_compiler'). On pass: return Command(goto='tool_executor').",
  "depends_on": ["T09"],
  "context_files": [
    "backend/app/agent/state.py"
  ],
  "acceptance_criteria": [
    "Routes to query_compiler with error message on missing phone filter",
    "Routes to query_compiler on mutating keyword",
    "Routes to tool_executor when both checks pass",
    "Raises ValueError('SECURITY_MAX_RETRIES') after 3 failures",
    "error_count increments correctly"
  ],
  "estimated_lines_changed": 45
}
```

```json
{
  "id": "T13",
  "title": "Create tool_executor (MCP) node",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/nodes/tool_executor.py",
  "function_or_class": "tool_executor",
  "description": "Create backend/app/agent/nodes/tool_executor.py. Define async function tool_executor(state: AgentState) -> dict. Open an MCP ClientSession against settings.DATABASE_URL, call the 'query' tool with state['generated_sql'], serialize the result list to JSON, return {'sql_result': json_string}. On any exception: catch, log, return {'sql_result': json.dumps({'error': str(e)})} — never raise so response_shaper can gracefully apologise.",
  "depends_on": ["T04", "T09"],
  "context_files": [
    "backend/app/agent/state.py",
    "backend/app/core/config.py"
  ],
  "acceptance_criteria": [
    "Returns dict with sql_result as JSON string on success",
    "Returns dict with JSON error object on MCP failure (no raise)",
    "Does not modify generated_sql or user_phone"
  ],
  "estimated_lines_changed": 40
}
```

```json
{
  "id": "T14",
  "title": "Create response_shaper node",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/nodes/response_shaper.py",
  "function_or_class": "build_response_shaper_node",
  "description": "Create backend/app/agent/nodes/response_shaper.py. Define build_response_shaper_node(llm) -> Callable[[AgentState], dict]. Returned async node: system prompt 'You are a voice assistant. Convert the SQL result into one natural spoken sentence. No markdown, no lists. If given a JSON error, apologise briefly.' Pass state['sql_result'] as user message, invoke LLM, return {'messages': [AIMessage(content=spoken_text)]}.",
  "depends_on": ["T09", "T10"],
  "context_files": [
    "backend/app/agent/state.py",
    "backend/app/agent/llm.py"
  ],
  "acceptance_criteria": [
    "Returns dict appending AIMessage to messages",
    "AIMessage content is a plain sentence with no markdown",
    "Handles JSON error objects gracefully"
  ],
  "estimated_lines_changed": 30
}
```

```json
{
  "id": "T15",
  "title": "Assemble LangGraph state machine",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/agent/graph.py",
  "function_or_class": "build_graph",
  "description": "Create backend/app/agent/graph.py. Define build_graph() -> CompiledGraph. Call build_llm() once. Create StateGraph(AgentState). Add nodes: 'query_compiler', 'security_supervisor', 'tool_executor', 'response_shaper'. Entry point: 'query_compiler'. Edges: query_compiler → security_supervisor; security_supervisor uses Command internally to route to query_compiler or tool_executor; tool_executor → response_shaper; response_shaper → END. Do NOT add a biometric_gate node — auth is enforced upstream in VoiceAgentOrchestrator. Cache compiled graph as module-level singleton. Export get_graph() returning the singleton.",
  "depends_on": ["T09", "T10", "T11", "T12", "T13", "T14"],
  "context_files": [
    "backend/app/agent/state.py",
    "backend/app/agent/llm.py",
    "backend/app/agent/nodes/query_compiler.py",
    "backend/app/agent/nodes/security_supervisor.py",
    "backend/app/agent/nodes/tool_executor.py",
    "backend/app/agent/nodes/response_shaper.py"
  ],
  "acceptance_criteria": [
    "build_graph() compiles without error",
    "get_graph() returns same singleton on repeated calls",
    "No biometric_gate node in the graph"
  ],
  "estimated_lines_changed": 45
}
```

```json
{
  "id": "T16",
  "title": "Create VoiceAgentOrchestrator service",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/services/voice_agent.py",
  "function_or_class": "VoiceAgentOrchestrator",
  "description": "Create backend/app/services/voice_agent.py. Define class VoiceAgentOrchestrator and module-level singleton get_voice_agent(). Public async method process_audio_chunk(client_id, audio_bytes, sample_rate, send_ws). Logic: (1) session = AgentSessionCache.get(client_id). If None or not session['verified']: tts = await synthesise_speech(PROMPT_NOT_VERIFIED); send_ws({'type':'agent_audio','data':b64(tts).decode()}); return. (2) utterance_complete, audio = session['vad'].process_chunk(audio_bytes, sample_rate). If not utterance_complete: return. (3) send_ws({'type':'agent_thinking'}). (4) transcription = await transcribe_audio(audio). If len(transcription.split()) < 3: send agent_audio PROMPT_ASK_AGAIN; return (do NOT append to conversation_history). (5) Build initial_state with user_phone from session, utterance=transcription, conversation_history=list(session['conversation_history']). (6) Try final_state = await get_graph().ainvoke(initial_state). Extract last AIMessage content as spoken. Except ValueError: spoken = 'Sorry, I could not process that safely.' (7) Append {'role':'user','text':transcription} and {'role':'assistant','text':spoken} to session['conversation_history'] via AgentSessionCache.update(). (8) tts = await synthesise_speech(spoken); send_ws({'type':'agent_audio','data':b64(tts),'transcript':transcription,'text':spoken}).",
  "depends_on": ["T05", "T06", "T07", "T08", "T09", "T15"],
  "context_files": [
    "backend/app/agent/session_cache.py",
    "backend/app/agent/vad.py",
    "backend/app/agent/stt.py",
    "backend/app/agent/tts.py",
    "backend/app/agent/graph.py",
    "backend/app/agent/state.py"
  ],
  "acceptance_criteria": [
    "Sends PROMPT_NOT_VERIFIED TTS when session is unverified or absent",
    "Returns immediately (no send) while utterance is still accumulating",
    "Sends PROMPT_ASK_AGAIN TTS when transcription is fewer than 3 words; history NOT updated",
    "Appends user utterance and assistant response to session conversation_history on successful turn",
    "Sends agent_audio with spoken LangGraph response on success",
    "send_ws called with correct shapes in all paths",
    "No direct DB calls inside this function"
  ],
  "estimated_lines_changed": 90
}
```

```json
{
  "id": "T17",
  "title": "Write verification success to AgentSessionCache",
  "type": "feature",
  "priority": "high",
  "layer": "service",
  "file": "backend/app/services/verification_streaming.py",
  "function_or_class": "RealtimeVerificationManager._save_session_to_database",
  "description": "In RealtimeVerificationManager, after every code path that sets session.final_status = 'verified' — the existing all-chunks path — call AgentSessionCache.set_verified(client_id=session.session_id, phone_number=session.phone_number). Import set_verified from app.agent.session_cache. First, confirm that session.session_id is the WebSocket client_id by tracing create_session() callers in events.py. If it is not the client_id, add a client_id: str = '' field to StreamingVerificationSession and populate it from events.py at session creation. The cache write must happen before _save_session_to_database returns so the very next audio chunk is correctly routed. The newly created cache entry will have conversation_history initialized to [] by set_verified().",
  "depends_on": ["T05"],
  "context_files": [
    "backend/app/services/verification_streaming.py",
    "backend/app/agent/session_cache.py",
    "backend/app/websocket/events.py"
  ],
  "acceptance_criteria": [
    "AgentSessionCache.get(session_id)['verified'] == True immediately after verification success",
    "AgentSessionCache.get(session_id)['conversation_history'] == [] on creation",
    "phone_number correctly populated in cache",
    "Cache write occurs in the full multi-chunk verified path"
  ],
  "estimated_lines_changed": 15
}
```

```json
{
  "id": "T18",
  "title": "Route verified audio to VoiceAgentOrchestrator in events.py",
  "type": "feature",
  "priority": "high",
  "layer": "route",
  "file": "backend/app/websocket/events.py",
  "function_or_class": "WebSocketEventHandler.handle_audio_chunk",
  "description": "In handle_audio_chunk(), before the existing buffer-append logic, add: session = get_agent_session(connection.client_id). If session is not None (entry exists): decode audio_bytes from the base64 message field, call await get_voice_agent().process_audio_chunk(client_id=connection.client_id, audio_bytes=audio_bytes, sample_rate=16000, send_ws=connection.send_json), then return {'type': 'audio_ack', 'status': 'ok'}. If session is None, fall through to the existing biometric buffer path unchanged. Import get as get_agent_session from app.agent.session_cache and get_voice_agent from app.services.voice_agent. Note: process_audio_chunk calls send_ws directly for async TTS responses; handle_audio_chunk only returns the synchronous ACK.",
  "depends_on": ["T05", "T16", "T17"],
  "context_files": [
    "backend/app/websocket/events.py",
    "backend/app/websocket/manager.py",
    "backend/app/agent/session_cache.py",
    "backend/app/services/voice_agent.py"
  ],
  "acceptance_criteria": [
    "Audio from a client with a cache entry is routed to VoiceAgentOrchestrator",
    "Audio from a client with no cache entry goes through the existing biometric path unchanged",
    "ACK returned immediately; agent TTS arrives as a separate send_json call",
    "No REST endpoint created or modified"
  ],
  "estimated_lines_changed": 20
}
```
