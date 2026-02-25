# GitHub Copilot Instructions — audio-memo

## Project Overview

**audio-memo** is a voice biometric authentication system.
- **Backend**: FastAPI (Python 3.11), MongoDB, SpeechBrain ECAPA-TDNN embeddings, WebSocket support.
- **Frontend**: React.js SPA.
- **Key domains**: Enrollment, Verification, ML embeddings, WebSocket streaming, LangChain LLM integration.

---

## Repository Structure

```
audio-memo/
├── backend/
│   └── app/
│       ├── api/routes/       # FastAPI route handlers (thin controllers only)
│       ├── core/             # App config, settings
│       ├── db/               # MongoDB access layer (one file per collection/concept)
│       ├── ml/               # Embedding generation, similarity, chunking, preprocessing
│       ├── models/           # Pydantic request/response models
│       ├── services/         # Business logic (orchestrates db + ml)
│       └── websocket/        # WebSocket manager, events, routing
├── frontend/
│   └── src/
│       ├── components/
│       ├── services/
│       ├── hooks/
│       └── utils/
└── docs/                     # RCA documents, feature specs, task lists
```

---

## Core Coding Principles

### 1. Modularization First
- **Routes** (`api/routes/`) must only handle HTTP/WebSocket concerns: parse input, call a service, return a response. No business logic.
- **Services** (`services/`) own all business logic. Each service file maps to a single domain concept (e.g., `enrollment_session.py`, `verification.py`).
- **DB layer** (`db/`) encapsulates all MongoDB queries. Services must never call `pymongo` directly.
- **ML layer** (`ml/`) contains all model inference, embedding math, preprocessing. Services call ML functions; routes never do.
- **Models** (`models/`) are pure Pydantic schemas. No logic allowed inside model files.

### 2. Reuse Before Writing
- Before writing a new function, search the existing codebase for a similar utility:
  - Embedding generation → `ml/embedding.py:generate_embedding()`
  - Cosine similarity → `ml/embedding.py:calculate_cosine_similarity()`
  - Enrollment check → `db/embeddings.py:check_enrollment()`
  - Session management → `services/enrollment_manager.py` / `services/verification.py`
- If a function does 90% of what you need, extend or wrap it — do not duplicate it.
- Shared utilities belong in the most specific layer that makes sense (`ml/`, `db/`, `services/`), never in route files.

### 3. Dependency Direction
```
routes → services → db / ml
              ↘ models (for typing)
```
Never import routes from services. Never import services from db or ml.

---

## Documentation Requirements

### For Every Bug Fix
1. **Before writing any code**, create `docs/rca/<YYYY-MM-DD>-<short-title>.md` with:
   - **Summary**: One-sentence description of the bug.
   - **Root Cause Analysis (RCA)**: Why it happened. File + line references.
   - **Impact**: What broke, which endpoints/users affected.
   - **Fix Required**: Exact code change needed (file, function, what to change).
   - **Verification Steps**: How to confirm the fix works.
   - **Task List** (JSON — see format below).

### For Every New Feature
1. **Before writing any code**, create `docs/features/<YYYY-MM-DD>-<feature-name>.md` with:
   - **Feature Summary**: What it does and why it is needed.
   - **Architecture**: Which layers are affected (route / service / db / ml / frontend).
   - **New Files**: List of files to be created.
   - **Modified Files**: List of existing files to be changed and why.
   - **API Contract**: New endpoints or WebSocket messages (request/response schema).
   - **Dependencies**: New packages or external services required.
   - **Test Plan**: Scenarios to validate the feature.
   - **Task List** (JSON — see format below).

---

## Task List JSON Format

Every doc file must include a `## Task List` section containing **one separate `json` code block per task**. Do NOT wrap all tasks in a single JSON array — each task is its own fenced block. This format allows an implementing model to extract and execute one task at a time without parsing a large array.

This list is optimised for execution by a **~30B parameter model with ~3B active params and a 40k token context window** — tasks must be small, self-contained, and explicitly reference file paths.

```json
{
  "id": "T01",
  "title": "Short imperative description (≤10 words)",
  "type": "bug_fix | feature | refactor | test | docs",
  "priority": "high | medium | low",
  "layer": "route | service | db | ml | model | frontend | config | test",
  "file": "backend/app/services/verification.py",
  "function_or_class": "process_verification_session",
  "description": "Detailed paragraph explaining exactly what needs to change in this specific file and function. Include: current behavior, desired behavior, and any edge cases to handle. Reference other task IDs this depends on.",
  "depends_on": ["T00"],
  "context_files": [
    "backend/app/services/verification.py",
    "backend/app/db/embeddings.py"
  ],
  "acceptance_criteria": [
    "Function returns X when Y",
    "No import of Z inside route layer"
  ],
  "estimated_lines_changed": 20
}
```

```json
{
  "id": "T02",
  "title": "Next task ...",
  ...
}
```

### Task List Rules
- **One `json` block per task. Never wrap tasks in a shared array.**
- Each task must touch **at most one file**. If a change requires two files, split into two tasks.
- `context_files` must list every file needed to understand the task (imported modules, related tests).
- `description` must be long enough that the implementing model needs no other context.
- Order tasks so dependencies always come first (`depends_on` must reference earlier IDs).
- Estimated lines changed should stay under 80; split larger tasks.

---

## Code Style

### Python (Backend)
- Python 3.11+, type hints on all function signatures.
- Pydantic v2 for all request/response models.
- `async def` for all route handlers and any I/O-bound service functions.
- Use `HTTPException` with explicit `status_code` and `detail` strings — no bare `raise`.
- Log with the module-level logger (`logging.getLogger(__name__)`), not `print`.
- Group imports: stdlib → third-party → internal (`app.*`).

### JavaScript (Frontend)
- Functional components with hooks only — no class components.
- All API calls go through `src/services/api.js` — no `fetch`/`axios` calls in components.
- Custom hooks live in `src/hooks/`.
- Component files export one default component matching the filename.

---

## Naming Conventions

| Concept | Convention | Example |
|---|---|---|
| Route file | `<domain>.py` | `verification.py` |
| Service file | `<domain>_<noun>.py` | `enrollment_session.py` |
| DB file | `<collection>.py` | `embeddings.py` |
| Pydantic model | `PascalCase` | `VerificationSessionResponse` |
| Service function | `snake_case` verb + noun | `create_verification_session()` |
| Route handler | `snake_case` verb + noun | `finalize_verification_session()` |
| JS component | `PascalCase.js` | `VerificationPage.js` |
| JS hook | `useCamelCase.js` | `useVerification.js` |

---

## What NOT to Do
- Do not put business logic in route handlers.
- Do not call `pymongo` or model inference directly from routes.
- Do not create a new utility function if an equivalent exists in `ml/` or `db/`.
- Do not hardcode thresholds or config values in route or service files — use `core/config.py`.
- Do not commit code without a corresponding doc file for the change (bug or feature).
- Do not leave `TODO` comments — convert them to a task in the docs JSON or open an issue.
