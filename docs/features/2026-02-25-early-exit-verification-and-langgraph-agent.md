# Feature: Early-Exit Verification + LangGraph Agentic SQL Engine

**Date:** 2026-02-25  
**Branch:** manik/refactoring

---

## Feature Summary

Two independent features delivered together:

1. **Early-Exit Verification** — When any single chunk's similarity score clears the enrollment threshold, the verification session is marked `verified` immediately and no further audio is requested. This reduces latency for legitimate users while keeping the full multi-chunk flow as a fallback for borderline scores.

2. **LangGraph Agentic SQL Engine** — A voice-triggered, biometrically-gated natural-language-to-SQL agent built with LangGraph. After a session is verified, the user can speak a query over the financial database. The agent compiles the utterance to SQL, passes it through a deterministic security supervisor (enforces `phone_number` filter and read-only access), executes it via an MCP client, and speaks back a natural-language response. The LLM backend is switchable between OpenAI and Gemini via an env variable.

---

## Architecture

### Feature 1 — Early-Exit Verification

Affected layers: **service**, **config**

Current behaviour (see `verification_streaming.py` line ~256):
> "REFACTORED: Process ALL chunks before deciding final result — No early return"

New behaviour: after each chunk result is stored, if `result.is_match is True` **and** `session.early_exit_on_match is True`, the session is finalised immediately with `final_status = "verified"` and saved to the DB. Subsequent audio is ignored (existing guard at the top of `process_chunk` already short-circuits on `session.final_status is not None`).

### Feature 2 — LangGraph Agentic SQL Engine

Affected layers: **config**, **model**, **service (agent)**, **route**, **frontend (minimal — existing WebSocket `VERIFY_CONFIRMED` message triggers agent)**

```
WebSocket VERIFY_CONFIRMED
        │
        ▼
POST /api/agent/query
        │
        ▼
  LangGraph Graph
  ┌─────────────────────────────────────────────────────┐
  │  biometric_gate ──(no session)──► END               │
  │       │                                             │
  │  query_compiler (LLM + bind_tools)                  │
  │       │                                             │
  │  security_supervisor (deterministic Python)         │
  │       ├──(fail, retry < 3)──► query_compiler        │
  │       └──(pass)──► tool_executor (MCP)              │
  │                        │                            │
  │                   response_shaper (LLM)             │
  │                        │                            │
  │                       END                           │
  └─────────────────────────────────────────────────────┘
```

---

## New Files

| File | Purpose |
|---|---|
| `backend/app/agent/__init__.py` | Package marker |
| `backend/app/agent/state.py` | `AgentState` TypedDict |
| `backend/app/agent/llm.py` | `build_llm()` factory — returns OpenAI or Gemini model |
| `backend/app/agent/nodes/__init__.py` | Package marker |
| `backend/app/agent/nodes/biometric_gate.py` | Gate node — validates verified session |
| `backend/app/agent/nodes/query_compiler.py` | LLM node — NL → SQL plan |
| `backend/app/agent/nodes/security_supervisor.py` | Python node — SQL safety checks |
| `backend/app/agent/nodes/tool_executor.py` | MCP node — executes SQL |
| `backend/app/agent/nodes/response_shaper.py` | LLM node — SQL result → spoken sentence |
| `backend/app/agent/graph.py` | Assembles and compiles the full LangGraph |
| `backend/app/api/routes/agent.py` | `POST /api/agent/query` endpoint |

---

## Modified Files

| File | Why |
|---|---|
| `backend/app/core/config.py` | New env vars: `EARLY_EXIT_ON_MATCH`, `LLM_PROVIDER`, `OPENAI_API_KEY`, `GOOGLE_PROJECT_ID`, `DATABASE_URL` |
| `backend/app/services/verification_streaming.py` | Add `early_exit_on_match` field; add early-exit branch in `process_chunk` |
| `backend/requirements.txt` | Add `langgraph`, `langchain`, `langchain-openai`, `langchain-google-vertexai`, `mcp` |
| `backend/app/main.py` | Register `agent` router |

---

## API Contract

### POST /api/agent/query

**Request**
```json
{
  "session_id": "uuid-of-verified-ws-session",
  "utterance": "Show me my last 5 transactions"
}
```

**Response — success**
```json
{
  "spoken_response": "Your last 5 transactions were ...",
  "generated_sql": "SELECT ... WHERE phone_number = '+1234567890' LIMIT 5",
  "sql_result": "[{...}, ...]"
}
```

**Response — gate failure (401)**
```json
{ "detail": "Session not verified or expired." }
```

**Response — security failure after max retries (422)**
```json
{ "detail": "Agent could not produce a safe SQL query after 3 attempts." }
```

---

## Dependencies

```
langgraph>=0.2
langchain>=0.2
langchain-openai>=0.1          # for ChatOpenAI
langchain-google-vertexai>=1.0 # for ChatVertexAI (Gemini)
mcp>=1.0                       # Model Context Protocol client
```

New `.env` keys:
```
EARLY_EXIT_ON_MATCH=true
LLM_PROVIDER=openai            # or "gemini"
OPENAI_API_KEY=sk-...
GOOGLE_PROJECT_ID=my-gcp-project   # only needed when LLM_PROVIDER=gemini
DATABASE_URL=postgresql://...      # used by MCP tool
```

---

## Test Plan

### Feature 1 — Early-Exit Verification
1. Enroll a phone number. Send one chunk with audio from the same speaker. Assert response contains `final_status: "verified"` and `verified_at_chunk: 1`.
2. Verify `session.final_status` is set; send a second chunk. Assert the response returns the already-complete status without re-processing.
3. Set `EARLY_EXIT_ON_MATCH=false`. Repeat scenario 1. Assert session does NOT close after chunk 1.

### Feature 2 — LangGraph Agent
1. Start server, verify phone number via WS, then call `POST /api/agent/query` with a valid utterance. Assert `spoken_response` is non-empty and `generated_sql` contains the phone number.
2. Call with an unverified `session_id`. Assert 401.
3. Manually mock the LLM to return SQL without the phone filter. Assert the security supervisor retries and eventually returns 422 after 3 attempts.
4. Mock the LLM to return `DELETE FROM ...`. Assert immediate 422 on security check.
5. Set `LLM_PROVIDER=gemini` and repeat scenario 1 with a mocked Gemini response. Assert the graph still completes successfully.

---

## Task List

```json
{
  "id": "T01",
    "title": "Add early-exit and agent config settings",
    "type": "feature",
    "priority": "high",
    "layer": "config",
    "file": "backend/app/core/config.py",
    "function_or_class": "Settings",
    "description": "Add five new fields to the Settings Pydantic model: (1) EARLY_EXIT_ON_MATCH: bool = True — controls whether verification stops on first matching chunk; (2) LLM_PROVIDER: str = 'openai' — toggles between 'openai' and 'gemini' in the agent; (3) OPENAI_API_KEY: str = '' — passed to ChatOpenAI; (4) GOOGLE_PROJECT_ID: str = '' — passed to ChatVertexAI when LLM_PROVIDER is 'gemini'; (5) DATABASE_URL: str = '' — connection string exposed to the MCP SQL tool. All fields must have sensible defaults so existing tests pass without a .env file.",
    "depends_on": [],
    "context_files": [
      "backend/app/core/config.py"
    ],
    "acceptance_criteria": [
      "Settings() instantiates without a .env file",
      "Each new field is readable via settings.<FIELD_NAME>",
      "No existing field is removed or renamed"
    ],
    "estimated_lines_changed": 8
}
```

```json
{
  "id": "T02",
    "title": "Add early_exit_on_match to StreamingVerificationSession",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/services/verification_streaming.py",
    "function_or_class": "StreamingVerificationSession",
    "description": "Add an `early_exit_on_match: bool = True` field to the StreamingVerificationSession dataclass. The default should be True so the feature is on by default. Also update RealtimeVerificationManager.create_session() to accept an optional `early_exit_on_match: bool` parameter (defaulting to `settings.EARLY_EXIT_ON_MATCH` from app.core.config) and assign it to the newly created session object. Import settings at the top of the file.",
    "depends_on": ["T01"],
    "context_files": [
      "backend/app/services/verification_streaming.py",
      "backend/app/core/config.py"
    ],
    "acceptance_criteria": [
      "StreamingVerificationSession has early_exit_on_match field",
      "create_session() passes the flag through to the session object",
      "Existing callers of create_session() require no changes (default covers them)"
    ],
    "estimated_lines_changed": 12
}
```

```json
{
  "id": "T03",
    "title": "Implement early-exit branch in process_chunk",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/services/verification_streaming.py",
    "function_or_class": "RealtimeVerificationManager.process_chunk",
    "description": "After the ChunkVerificationResult is appended to session.chunk_results (currently around line 255) and before the existing 'if session.chunks_processed >= session.max_chunks' block, insert a new early-exit block: if session.early_exit_on_match is True AND result.is_match is True, immediately set session.final_status = 'verified', session.verified_at_chunk = session.chunks_processed, session.status = StreamingVerificationStatus.VERIFIED, populate response['final_status'] = 'verified', log a success message, call self._save_session_to_database(session), and return response. Remove the comment '# REFACTORED: Process ALL chunks before deciding final result — No early return' as it will no longer be accurate. The existing max_chunks block must remain intact as the fallback path when EARLY_EXIT_ON_MATCH is False or no single chunk exceeds the threshold.",
    "depends_on": ["T02"],
    "context_files": [
      "backend/app/services/verification_streaming.py"
    ],
    "acceptance_criteria": [
      "When early_exit_on_match=True and chunk 1 is_match=True, response.final_status == 'verified' and session.verified_at_chunk == 1",
      "When early_exit_on_match=True but chunk 1 is_match=False, session continues to collect more chunks",
      "When early_exit_on_match=False, existing all-chunks-must-pass logic is unchanged",
      "_save_session_to_database is called exactly once on early exit"
    ],
    "estimated_lines_changed": 20
}
```

```json
{
  "id": "T04",
    "title": "Add langgraph and LLM packages to requirements.txt",
    "type": "feature",
    "priority": "high",
    "layer": "config",
    "file": "backend/requirements.txt",
    "function_or_class": null,
    "description": "Append the following packages to requirements.txt: langgraph>=0.2, langchain>=0.2, langchain-openai>=0.1, langchain-google-vertexai>=1.0, mcp>=1.0. These are required by the agent feature (T07–T15). Do not remove any existing dependency. Prefer unpinned lower-bound version specifiers (>=) so the project does not become rigidly pinned.",
    "depends_on": [],
    "context_files": [
      "backend/requirements.txt"
    ],
    "acceptance_criteria": [
      "pip install -r requirements.txt succeeds in a clean venv",
      "All five packages are importable after install"
    ],
    "estimated_lines_changed": 5
}
```

```json
{
  "id": "T05",
    "title": "Create AgentState TypedDict",
    "type": "feature",
    "priority": "high",
    "layer": "model",
    "file": "backend/app/agent/state.py",
    "function_or_class": "AgentState",
    "description": "Create backend/app/agent/__init__.py (empty) and backend/app/agent/state.py. In state.py define AgentState as a TypedDict using langgraph.graph.message.add_messages for the messages key. Fields: messages: Annotated[list[BaseMessage], add_messages] (conversation history, append-only reducer), user_phone: str (verified phone number, populated by biometric_gate), generated_sql: str (output of query_compiler, consumed by security_supervisor and tool_executor), sql_result: str (JSON string output of tool_executor, consumed by response_shaper), error_count: int (incremented by security_supervisor on each retry, used to enforce max-retry limit of 3). Import BaseMessage from langchain_core.messages and Annotated from typing.",
    "depends_on": ["T04"],
    "context_files": [
      "backend/app/agent/state.py"
    ],
    "acceptance_criteria": [
      "AgentState is importable from app.agent.state",
      "All five fields present with correct types",
      "messages field uses add_messages reducer so parallel node writes are merged, not overwritten"
    ],
    "estimated_lines_changed": 20
}
```

```json
{
  "id": "T06",
    "title": "Create build_llm() factory function",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/agent/llm.py",
    "function_or_class": "build_llm",
    "description": "Create backend/app/agent/llm.py with a single public function build_llm() -> BaseChatModel. Read settings.LLM_PROVIDER (from app.core.config). If 'openai': return ChatOpenAI(model='gpt-4o-mini', api_key=settings.OPENAI_API_KEY). If 'gemini': return ChatVertexAI(model='gemini-1.5-flash', project=settings.GOOGLE_PROJECT_ID). Otherwise raise ValueError(f'Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}'). The function must NOT cache the model globally — graph.py will call it once at graph-compile time. Import ChatOpenAI from langchain_openai and ChatVertexAI from langchain_google_vertexai.",
    "depends_on": ["T01", "T04", "T05"],
    "context_files": [
      "backend/app/core/config.py",
      "backend/app/agent/llm.py"
    ],
    "acceptance_criteria": [
      "build_llm() returns a ChatOpenAI instance when LLM_PROVIDER='openai'",
      "build_llm() returns a ChatVertexAI instance when LLM_PROVIDER='gemini'",
      "build_llm() raises ValueError for unknown providers"
    ],
    "estimated_lines_changed": 25
}
```

```json
{
  "id": "T07",
    "title": "Create biometric_gate node",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/agent/nodes/biometric_gate.py",
    "function_or_class": "biometric_gate",
    "description": "Create backend/app/agent/nodes/__init__.py (empty) and backend/app/agent/nodes/biometric_gate.py. Define async function biometric_gate(state: AgentState) -> AgentState. The function receives the full graph state. It must look up `state['session_id']` (a key injected before graph invocation — see graph.py T14) in the DB via app.db.verified_sessions to check that the session's final_status is 'verified'. If the session is not found or not verified, raise a ValueError('GATE_FAILED: session not verified') — the route handler (T15) will catch this and return HTTP 401. If verified, extract the phone_number from the session document and return a state update: {'user_phone': phone_number}. Import get_verified_session from app.db.verified_sessions. Do NOT import any route or service layer.",
    "depends_on": ["T05"],
    "context_files": [
      "backend/app/agent/state.py",
      "backend/app/db/verified_sessions.py"
    ],
    "acceptance_criteria": [
      "Returns updated state with user_phone populated when session is verified",
      "Raises ValueError with 'GATE_FAILED' prefix when session missing or unverified",
      "No import from app.api or app.services"
    ],
    "estimated_lines_changed": 30
}
```

```json
{
  "id": "T08",
    "title": "Create query_compiler node",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/agent/nodes/query_compiler.py",
    "function_or_class": "build_query_compiler_node",
    "description": "Create backend/app/agent/nodes/query_compiler.py. Define build_query_compiler_node(llm: BaseChatModel) -> Callable[[AgentState], AgentState]. The returned async callable is the graph node. It should: (1) Build a system prompt that embeds the DB schema (hardcode a minimal schema string describing the transactions table with columns: id, phone_number, amount, merchant, timestamp) and instructs the LLM to produce a single SELECT SQL statement with a WHERE phone_number = '{user_phone}' filter — the user_phone must be injected from state['user_phone']. (2) Append any error messages from the previous security check (from state['messages'], look for the last SystemMessage with 'SECURITY ERROR') so the LLM can self-correct. (3) Invoke the bound LLM. (4) Parse the LLM text response to extract the SQL — look for text between ```sql...``` fences, or take the full response if no fences. (5) Return {'generated_sql': <extracted_sql>}.",
    "depends_on": ["T05", "T06"],
    "context_files": [
      "backend/app/agent/state.py",
      "backend/app/agent/llm.py"
    ],
    "acceptance_criteria": [
      "Returns state update with generated_sql key",
      "System prompt contains the phone number from state['user_phone']",
      "If the last message is a SECURITY ERROR, it is included in the prompt for self-correction",
      "SQL is extracted correctly from ```sql...``` fenced blocks"
    ],
    "estimated_lines_changed": 55
}
```

```json
{
  "id": "T09",
    "title": "Create security_supervisor node",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/agent/nodes/security_supervisor.py",
    "function_or_class": "security_supervisor",
    "description": "Create backend/app/agent/nodes/security_supervisor.py. Define async function security_supervisor(state: AgentState) -> Command. Import Command from langgraph.types. The node must perform two deterministic checks on state['generated_sql']: (1) Phone filter check — verify that state['user_phone'] appears verbatim in the SQL string. (2) Mutation check — verify that none of the words DELETE, UPDATE, DROP, INSERT, TRUNCATE, ALTER appear in the uppercased SQL. If either check fails: increment state['error_count'] by 1; if error_count >= 3 raise ValueError('SECURITY_MAX_RETRIES: could not produce safe SQL'); otherwise return Command(update={'messages': [SystemMessage(content='SECURITY ERROR: <specific reason>. Retry.')], 'error_count': state['error_count']}, goto='query_compiler'). If both checks pass: return Command(goto='tool_executor'). Import SystemMessage from langchain_core.messages.",
    "depends_on": ["T05"],
    "context_files": [
      "backend/app/agent/state.py"
    ],
    "acceptance_criteria": [
      "Routes to query_compiler with an error message when phone filter is missing",
      "Routes to query_compiler with an error message when a mutating keyword is detected",
      "Routes to tool_executor when both checks pass",
      "Raises ValueError after 3 consecutive failures",
      "error_count is incremented on each failure"
    ],
    "estimated_lines_changed": 45
}
```

```json
{
  "id": "T10",
    "title": "Create tool_executor (MCP) node",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/agent/nodes/tool_executor.py",
    "function_or_class": "tool_executor",
    "description": "Create backend/app/agent/nodes/tool_executor.py. Define async function tool_executor(state: AgentState) -> AgentState. The node executes the vetted SQL from state['generated_sql'] via the MCP client. Use the mcp library to create a ClientSession pointed at settings.DATABASE_URL. Call the 'query' MCP tool with the SQL string. Serialize the result (a list of dicts) to a JSON string and return {'sql_result': json_string}. Handle exceptions: on any MCP error, set sql_result to a JSON string representing an error object: {'error': str(e)}. This ensures response_shaper always has something to work with. Import settings from app.core.config.",
    "depends_on": ["T04", "T05"],
    "context_files": [
      "backend/app/agent/state.py",
      "backend/app/core/config.py"
    ],
    "acceptance_criteria": [
      "Returns state update with sql_result as a JSON string",
      "On MCP error, sql_result contains a JSON error object instead of raising",
      "Does not modify generated_sql or user_phone"
    ],
    "estimated_lines_changed": 40
}
```

```json
{
  "id": "T11",
    "title": "Create response_shaper node",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/agent/nodes/response_shaper.py",
    "function_or_class": "build_response_shaper_node",
    "description": "Create backend/app/agent/nodes/response_shaper.py. Define build_response_shaper_node(llm: BaseChatModel) -> Callable[[AgentState], AgentState]. The returned async callable is the graph node. System prompt instructs the LLM: 'You are a voice assistant. Convert the following SQL query result into a single, natural, conversational spoken sentence. Do not use markdown or lists. If the result is an error JSON, apologise briefly.' Pass state['sql_result'] as the user message. Invoke the LLM, extract the text response, and return {'messages': [AIMessage(content=spoken_text)]}. The route handler reads the last AIMessage as the spoken_response.",
    "depends_on": ["T05", "T06"],
    "context_files": [
      "backend/app/agent/state.py",
      "backend/app/agent/llm.py"
    ],
    "acceptance_criteria": [
      "Returns a state update appending an AIMessage to messages",
      "The AIMessage content is a plain-language sentence with no markdown",
      "Handles error JSON in sql_result gracefully (apologises without crashing)"
    ],
    "estimated_lines_changed": 30
}
```

```json
{
  "id": "T12",
    "title": "Assemble LangGraph state machine",
    "type": "feature",
    "priority": "high",
    "layer": "service",
    "file": "backend/app/agent/graph.py",
    "function_or_class": "build_graph",
    "description": "Create backend/app/agent/graph.py. Define build_graph() -> CompiledGraph. Call build_llm() once to get the shared LLM instance. Instantiate a StateGraph(AgentState). Add nodes: 'biometric_gate' → biometric_gate, 'query_compiler' → build_query_compiler_node(llm), 'security_supervisor' → security_supervisor, 'tool_executor' → tool_executor, 'response_shaper' → build_response_shaper_node(llm). Set entry point to 'biometric_gate'. Add edges: biometric_gate → query_compiler, query_compiler → security_supervisor (security_supervisor uses Command internally to route to either query_compiler or tool_executor), tool_executor → response_shaper, response_shaper → END. Compile and return the graph. Cache the compiled graph as a module-level singleton _graph so build_graph() is called once at import time. Export a top-level get_graph() function that returns _graph.",
    "depends_on": ["T05", "T06", "T07", "T08", "T09", "T10", "T11"],
    "context_files": [
      "backend/app/agent/state.py",
      "backend/app/agent/llm.py",
      "backend/app/agent/nodes/biometric_gate.py",
      "backend/app/agent/nodes/query_compiler.py",
      "backend/app/agent/nodes/security_supervisor.py",
      "backend/app/agent/nodes/tool_executor.py",
      "backend/app/agent/nodes/response_shaper.py"
    ],
    "acceptance_criteria": [
      "build_graph() returns a CompiledGraph without error",
      "get_graph() returns the same singleton on repeated calls",
      "Graph node names match: biometric_gate, query_compiler, security_supervisor, tool_executor, response_shaper"
    ],
    "estimated_lines_changed": 50
}
```

```json
{
  "id": "T13",
    "title": "Create POST /api/agent/query route",
    "type": "feature",
    "priority": "high",
    "layer": "route",
    "file": "backend/app/api/routes/agent.py",
    "function_or_class": "query_agent",
    "description": "Create backend/app/api/routes/agent.py. Define an APIRouter with prefix '/api/agent'. Add a POST '/query' endpoint. Request body: Pydantic model AgentQueryRequest with fields session_id: str and utterance: str. Handler logic: (1) Build the initial state dict: {'messages': [HumanMessage(content=utterance)], 'user_phone': '', 'generated_sql': '', 'sql_result': '', 'error_count': 0, 'session_id': session_id}. (2) Invoke get_graph().ainvoke(initial_state). (3) Catch ValueError: if message starts with 'GATE_FAILED' raise HTTPException(401); if 'SECURITY_MAX_RETRIES' raise HTTPException(422). (4) On success, extract the last AIMessage content from final_state['messages'] as spoken_response. Return JSON: {spoken_response, generated_sql: final_state['generated_sql'], sql_result: final_state['sql_result']}. Do NOT import services or db directly — all logic goes through the graph.",
    "depends_on": ["T12"],
    "context_files": [
      "backend/app/agent/graph.py",
      "backend/app/agent/state.py",
      "backend/app/models/common.py"
    ],
    "acceptance_criteria": [
      "Returns 200 with spoken_response on successful graph run",
      "Returns 401 when biometric_gate raises GATE_FAILED",
      "Returns 422 when security_supervisor raises SECURITY_MAX_RETRIES",
      "No business logic inside the route handler"
    ],
    "estimated_lines_changed": 45
}
```

```json
{
  "id": "T14",
    "title": "Register agent router in main.py",
    "type": "feature",
    "priority": "medium",
    "layer": "route",
    "file": "backend/app/main.py",
    "function_or_class": "app",
    "description": "In backend/app/main.py, import the agent router: `from app.api.routes import agent`. Add `app.include_router(agent.router)` alongside the existing enrollment, verification, and health router inclusions. No other changes to main.py are needed.",
    "depends_on": ["T13"],
    "context_files": [
      "backend/app/main.py",
      "backend/app/api/routes/agent.py"
    ],
    "acceptance_criteria": [
      "GET /openapi.json includes the /api/agent/query path after startup",
      "No existing routes are affected"
    ],
    "estimated_lines_changed": 3
}
```
