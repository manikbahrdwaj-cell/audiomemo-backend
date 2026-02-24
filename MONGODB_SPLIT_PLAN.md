# MongoDB Split Plan

> **Goal:** Break `backend/app/db/mongodb.py` (~1 200 lines) into focused single-responsibility sub-modules.
> Each task below is a self-contained JSON prompt that can be fed directly to a coding model.
> LangChain functions (`get_langchain_sessions_collection`, `save_langchain_session`, …) are **excluded** (deferred).

---

## Target Directory Structure

```
backend/app/db/
├── __init__.py              ← update re-exports to point at new modules (MDB09)
├── mongodb.py               ← converted to a thin backward-compat shim (MDB08)
├── connection.py            ← NEW: client singleton + all collection getters
├── embeddings.py            ← NEW: voice embedding CRUD
├── enrollment_sessions.py   ← NEW: enrollment session CRUD
├── audio_chunks.py          ← NEW: audio chunk CRUD
├── enrollment_history.py    ← NEW: enrollment history CRUD
└── verified_sessions.py     ← NEW: verified session CRUD
```

---

## Function → Module Mapping

| Function | New module |
|---|---|
| `get_database` | `connection.py` |
| `get_enrollment_sessions_collection` | `connection.py` |
| `get_audio_chunks_collection` | `connection.py` |
| `get_enrollment_history_collection` | `connection.py` |
| `get_verified_sessions_collection` | `connection.py` |
| `get_langchain_sessions_collection` | **DEFERRED — stays in mongodb.py** |
| `store_voice_embedding` | `embeddings.py` |
| `get_voice_embedding` | `embeddings.py` |
| `check_enrollment` | `embeddings.py` |
| `find_nearest_embedding` | `embeddings.py` |
| `verify_phone_number_embedding` | `embeddings.py` |
| `delete_voice_embedding` | `embeddings.py` |
| `get_all_enrollments` | `embeddings.py` |
| `save_enrollment_session` | `enrollment_sessions.py` |
| `get_enrollment_session` | `enrollment_sessions.py` |
| `update_enrollment_session` | `enrollment_sessions.py` |
| `delete_enrollment_session` | `enrollment_sessions.py` |
| `get_enrollment_sessions_for_phone` | `enrollment_sessions.py` |
| `get_active_enrollment_sessions` | `enrollment_sessions.py` |
| `cleanup_expired_enrollment_sessions` | `enrollment_sessions.py` |
| `save_audio_chunk` | `audio_chunks.py` |
| `get_audio_chunks_for_session` | `audio_chunks.py` |
| `save_enrollment_history` | `enrollment_history.py` |
| `get_enrollment_history_for_phone` | `enrollment_history.py` |
| `get_recent_enrollments` | `enrollment_history.py` |
| `get_enrollment_stats` | `enrollment_history.py` |
| `save_verified_session` | `verified_sessions.py` |
| `get_verified_session` | `verified_sessions.py` |
| `update_verified_session` | `verified_sessions.py` |
| `delete_verified_session` | `verified_sessions.py` |
| `get_verified_sessions_for_phone` | `verified_sessions.py` |
| `get_active_verified_sessions` | `verified_sessions.py` |
| `get_recent_verifications` | `verified_sessions.py` |
| `save_langchain_session` | **DEFERRED — stays in mongodb.py** |
| `get_langchain_session` | **DEFERRED — stays in mongodb.py** |
| `update_langchain_session_status` | **DEFERRED — stays in mongodb.py** |
| `add_conversation_turn` | **DEFERRED — stays in mongodb.py** |
| `get_langchain_sessions_by_phone` | **DEFERRED — stays in mongodb.py** |
| `get_active_langchain_sessions` | **DEFERRED — stays in mongodb.py** |
| `get_langchain_session_summary` | **DEFERRED — stays in mongodb.py** |
| `delete_expired_langchain_sessions` | **DEFERRED — stays in mongodb.py** |

---

## Subtask Prompts

---

### MDB01 — Create app/db/connection.py

```json
{
  "task_id": "MDB01",
  "title": "Create backend/app/db/connection.py — MongoDB connection singleton and collection getters",
  "description": "Extract the global connection state and all collection-getter functions from mongodb.py into a new dedicated file. This file is the single place that owns the MongoClient instance. All other new db sub-modules will import their collection getter from here.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Create the file app/db/connection.py.",
    "At the top add these imports and ONLY these imports:",
    "  import logging",
    "  from pymongo import MongoClient",
    "  from pymongo.errors import ConnectionFailure",
    "  from app.core.config import settings",
    "",
    "Copy the following block from mongodb.py verbatim into connection.py:",
    "  - The MONGODB_URL and DATABASE_NAME constants (they must read from settings, not be hardcoded).",
    "  - The six global variables: _client, _db, _collection, _enrollment_sessions_collection,",
    "    _audio_chunks_collection, _enrollment_history_collection.",
    "    (Do NOT copy _langchain_sessions_collection — that stays in mongodb.py.)",
    "  - The full body of get_database()",
    "  - The full body of get_enrollment_sessions_collection()",
    "  - The full body of get_audio_chunks_collection()",
    "  - The full body of get_enrollment_history_collection()",
    "    NOTE: get_enrollment_history_collection references _client and DATABASE_NAME —",
    "    make sure both are defined in this file.",
    "",
    "Do NOT copy get_verified_sessions_collection() here — it will be in verified_sessions.py.",
    "Do NOT copy get_langchain_sessions_collection() here — it stays in mongodb.py.",
    "Do NOT remove anything from mongodb.py yet — that happens in MDB08.",
    "",
    "Verification: run `python -c \"from app.db.connection import get_database; print('OK')\"` from backend/.",
    "Expected output: OK (a MongoDB connection log may appear — that is fine)."
  ],
  "new_file": "backend/app/db/connection.py",
  "functions_to_copy": [
    "get_database",
    "get_enrollment_sessions_collection",
    "get_audio_chunks_collection",
    "get_enrollment_history_collection"
  ],
  "depends_on": []
}
```

---

### MDB02 — Create app/db/embeddings.py

```json
{
  "task_id": "MDB02",
  "title": "Create backend/app/db/embeddings.py — voice embedding CRUD",
  "description": "Extract the seven voice-embedding functions from mongodb.py into a new file. This file handles storing and retrieving ECAPA-TDNN voice embeddings.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Create the file app/db/embeddings.py.",
    "At the top add these imports and ONLY these imports:",
    "  import logging",
    "  import numpy as np",
    "  from typing import Optional, Dict, Any, List",
    "  from datetime import datetime",
    "  from app.db.connection import get_database",
    "",
    "Copy the following functions verbatim from mongodb.py into this file:",
    "  - store_voice_embedding(phone_number, embedding)",
    "  - get_voice_embedding(phone_number)",
    "  - check_enrollment(phone_number)",
    "  - find_nearest_embedding(query_embedding, phone_number, limit)",
    "  - verify_phone_number_embedding(query_embedding, phone_number)",
    "  - delete_voice_embedding(phone_number)",
    "  - get_all_enrollments()",
    "",
    "Do NOT remove anything from mongodb.py yet — that happens in MDB08.",
    "",
    "Verification:",
    "  python -c \"from app.db.embeddings import store_voice_embedding, check_enrollment; print('OK')\"",
    "Expected output: OK"
  ],
  "new_file": "backend/app/db/embeddings.py",
  "functions_to_copy": [
    "store_voice_embedding",
    "get_voice_embedding",
    "check_enrollment",
    "find_nearest_embedding",
    "verify_phone_number_embedding",
    "delete_voice_embedding",
    "get_all_enrollments"
  ],
  "depends_on": ["MDB01"]
}
```

---

### MDB03 — Create app/db/enrollment_sessions.py

```json
{
  "task_id": "MDB03",
  "title": "Create backend/app/db/enrollment_sessions.py — enrollment session CRUD",
  "description": "Extract the seven enrollment-session functions from the '# ENROLLMENT SESSION OPERATIONS' section of mongodb.py into a new file.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Create the file app/db/enrollment_sessions.py.",
    "At the top add these imports and ONLY these imports:",
    "  import logging",
    "  from typing import Optional, Dict, Any, List",
    "  from datetime import datetime",
    "  from app.db.connection import get_enrollment_sessions_collection",
    "",
    "Copy the following functions verbatim from mongodb.py into this file:",
    "  - save_enrollment_session(session_data)",
    "  - get_enrollment_session(session_id)",
    "  - update_enrollment_session(session_id, updates)",
    "  - delete_enrollment_session(session_id)",
    "  - get_enrollment_sessions_for_phone(phone_number, limit)",
    "  - get_active_enrollment_sessions(phone_number)",
    "  - cleanup_expired_enrollment_sessions(max_age_seconds)",
    "",
    "Do NOT remove anything from mongodb.py yet — that happens in MDB08.",
    "",
    "Verification:",
    "  python -c \"from app.db.enrollment_sessions import save_enrollment_session; print('OK')\"",
    "Expected output: OK"
  ],
  "new_file": "backend/app/db/enrollment_sessions.py",
  "functions_to_copy": [
    "save_enrollment_session",
    "get_enrollment_session",
    "update_enrollment_session",
    "delete_enrollment_session",
    "get_enrollment_sessions_for_phone",
    "get_active_enrollment_sessions",
    "cleanup_expired_enrollment_sessions"
  ],
  "depends_on": ["MDB01"]
}
```

---

### MDB04 — Create app/db/audio_chunks.py

```json
{
  "task_id": "MDB04",
  "title": "Create backend/app/db/audio_chunks.py — audio chunk CRUD",
  "description": "Extract the two audio-chunk functions from the '# AUDIO CHUNKS OPERATIONS' section of mongodb.py into a new file.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Create the file app/db/audio_chunks.py.",
    "At the top add these imports and ONLY these imports:",
    "  import logging",
    "  from typing import Dict, Any, List",
    "  from datetime import datetime",
    "  from app.db.connection import get_audio_chunks_collection",
    "",
    "Copy the following functions verbatim from mongodb.py into this file:",
    "  - save_audio_chunk(chunk_data)",
    "  - get_audio_chunks_for_session(session_id)",
    "",
    "Do NOT remove anything from mongodb.py yet — that happens in MDB08.",
    "",
    "Verification:",
    "  python -c \"from app.db.audio_chunks import save_audio_chunk, get_audio_chunks_for_session; print('OK')\"",
    "Expected output: OK"
  ],
  "new_file": "backend/app/db/audio_chunks.py",
  "functions_to_copy": [
    "save_audio_chunk",
    "get_audio_chunks_for_session"
  ],
  "depends_on": ["MDB01"]
}
```

---

### MDB05 — Create app/db/enrollment_history.py

```json
{
  "task_id": "MDB05",
  "title": "Create backend/app/db/enrollment_history.py — enrollment history CRUD",
  "description": "Extract the four enrollment-history functions from the '# ENROLLMENT HISTORY OPERATIONS' section of mongodb.py into a new file.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Create the file app/db/enrollment_history.py.",
    "At the top add these imports and ONLY these imports:",
    "  import logging",
    "  from typing import Optional, Dict, Any, List",
    "  from datetime import datetime",
    "  from app.db.connection import get_enrollment_history_collection, get_enrollment_sessions_collection",
    "",
    "Copy the following functions verbatim from mongodb.py into this file:",
    "  - save_enrollment_history(history_data)",
    "  - get_enrollment_history_for_phone(phone_number, limit)",
    "  - get_recent_enrollments(limit)",
    "  - get_enrollment_stats(phone_number)",
    "",
    "NOTE: get_enrollment_stats() uses both get_enrollment_sessions_collection() and",
    "get_enrollment_history_collection() — both are imported from connection.py above.",
    "",
    "Do NOT remove anything from mongodb.py yet — that happens in MDB08.",
    "",
    "Verification:",
    "  python -c \"from app.db.enrollment_history import get_enrollment_stats; print('OK')\"",
    "Expected output: OK"
  ],
  "new_file": "backend/app/db/enrollment_history.py",
  "functions_to_copy": [
    "save_enrollment_history",
    "get_enrollment_history_for_phone",
    "get_recent_enrollments",
    "get_enrollment_stats"
  ],
  "depends_on": ["MDB01"]
}
```

---

### MDB06 — Create app/db/verified_sessions.py

```json
{
  "task_id": "MDB06",
  "title": "Create backend/app/db/verified_sessions.py — verified session CRUD",
  "description": "Extract get_verified_sessions_collection and the seven verified-session functions from the '# VERIFIED SESSIONS OPERATIONS' section of mongodb.py into a new file. This file owns the collection getter because it is not needed by any other sub-module.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Create the file app/db/verified_sessions.py.",
    "At the top add these imports and ONLY these imports:",
    "  import logging",
    "  from typing import Optional, Dict, Any, List",
    "  from datetime import datetime",
    "  from app.db.connection import get_database  # used to access _db for collection init",
    "",
    "Copy the following functions verbatim from mongodb.py into this file:",
    "  - get_verified_sessions_collection()   ← this stays here, NOT in connection.py",
    "  - save_verified_session(session_data)",
    "  - get_verified_session(session_id)",
    "  - update_verified_session(session_id, updates)",
    "  - delete_verified_session(session_id)",
    "  - get_verified_sessions_for_phone(phone_number, limit)",
    "  - get_active_verified_sessions(phone_number)",
    "  - get_recent_verifications(limit)",
    "",
    "IMPORTANT: get_verified_sessions_collection() references the global `_db` variable.",
    "  Since _db is now defined in connection.py, you must either:",
    "  Option A (preferred): call get_database() inside the function to ensure _db is initialised,",
    "    then access the collection directly: `get_database(); from app.db.connection import _db`",
    "  Option B: import the `_client` and `_db` module-level variables from connection.py",
    "    and reference them by name. Use Option A unless Option B is cleaner for the actual code.",
    "",
    "Do NOT remove anything from mongodb.py yet — that happens in MDB08.",
    "",
    "Verification:",
    "  python -c \"from app.db.verified_sessions import save_verified_session; print('OK')\"",
    "Expected output: OK"
  ],
  "new_file": "backend/app/db/verified_sessions.py",
  "functions_to_copy": [
    "get_verified_sessions_collection",
    "save_verified_session",
    "get_verified_session",
    "update_verified_session",
    "delete_verified_session",
    "get_verified_sessions_for_phone",
    "get_active_verified_sessions",
    "get_recent_verifications"
  ],
  "depends_on": ["MDB01"]
}
```

---

### MDB07 — Convert mongodb.py to backward-compat shim

```json
{
  "task_id": "MDB07",
  "title": "Convert backend/app/db/mongodb.py into a thin backward-compatibility shim",
  "description": "Replace the body of mongodb.py with import re-exports from the new sub-modules. Any code that still imports from app.db.mongodb will continue to work without changes. The LangChain functions remain implemented here (not moved).",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open app/db/mongodb.py.",
    "DELETE everything in the file EXCEPT the LangChain section:",
    "  - Keep the module docstring at the top.",
    "  - Keep the LangChain global variable: _langchain_sessions_collection",
    "  - Keep the full body of get_langchain_sessions_collection()",
    "  - Keep save_langchain_session(), get_langchain_session(), update_langchain_session_status(),",
    "    add_conversation_turn(), get_langchain_sessions_by_phone(), get_active_langchain_sessions(),",
    "    get_langchain_session_summary(), delete_expired_langchain_sessions()",
    "",
    "REPLACE the deleted code with these import re-exports at the top of the file",
    "(after the docstring, before the LangChain section):",
    "",
    "  # Backward-compat re-exports — real implementations now live in sub-modules",
    "  from app.db.connection import (",
    "      get_database,",
    "      get_enrollment_sessions_collection,",
    "      get_audio_chunks_collection,",
    "      get_enrollment_history_collection,",
    "  )",
    "  from app.db.embeddings import (",
    "      store_voice_embedding,",
    "      get_voice_embedding,",
    "      check_enrollment,",
    "      find_nearest_embedding,",
    "      verify_phone_number_embedding,",
    "      delete_voice_embedding,",
    "      get_all_enrollments,",
    "  )",
    "  from app.db.enrollment_sessions import (",
    "      save_enrollment_session,",
    "      get_enrollment_session,",
    "      update_enrollment_session,",
    "      delete_enrollment_session,",
    "      get_enrollment_sessions_for_phone,",
    "      get_active_enrollment_sessions,",
    "      cleanup_expired_enrollment_sessions,",
    "  )",
    "  from app.db.audio_chunks import (",
    "      save_audio_chunk,",
    "      get_audio_chunks_for_session,",
    "  )",
    "  from app.db.enrollment_history import (",
    "      save_enrollment_history,",
    "      get_enrollment_history_for_phone,",
    "      get_recent_enrollments,",
    "      get_enrollment_stats,",
    "  )",
    "  from app.db.verified_sessions import (",
    "      save_verified_session,",
    "      get_verified_session,",
    "      update_verified_session,",
    "      delete_verified_session,",
    "      get_verified_sessions_for_phone,",
    "      get_active_verified_sessions,",
    "      get_recent_verifications,",
    "  )",
    "",
    "Keep ALL imports the LangChain functions need (pymongo, logging, typing, datetime, app.core.config).",
    "",
    "Verification: run `python -c \"from app.db.mongodb import check_enrollment, save_verified_session, save_langchain_session; print('OK')\"` from backend/.",
    "Expected: OK"
  ],
  "depends_on": ["MDB01", "MDB02", "MDB03", "MDB04", "MDB05", "MDB06"]
}
```

---

### MDB08 — Update app/db/__init__.py

```json
{
  "task_id": "MDB08",
  "title": "Update backend/app/db/__init__.py to re-export from the new sub-modules",
  "description": "The current __init__.py re-exports a small fixed set of symbols from mongodb.py. Expand it to re-export the complete public API from all new sub-modules so callers can optionally use `from app.db import store_voice_embedding` instead of the full path.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open app/db/__init__.py.",
    "Replace its entire contents with the following:",
    "",
    "  # Connection",
    "  from app.db.connection import get_database",
    "",
    "  # Embeddings",
    "  from app.db.embeddings import (",
    "      store_voice_embedding,",
    "      get_voice_embedding,",
    "      check_enrollment,",
    "      find_nearest_embedding,",
    "      verify_phone_number_embedding,",
    "      delete_voice_embedding,",
    "      get_all_enrollments,",
    "  )",
    "",
    "  # Enrollment sessions",
    "  from app.db.enrollment_sessions import (",
    "      save_enrollment_session,",
    "      get_enrollment_session,",
    "      update_enrollment_session,",
    "      delete_enrollment_session,",
    "      get_enrollment_sessions_for_phone,",
    "      get_active_enrollment_sessions,",
    "      cleanup_expired_enrollment_sessions,",
    "  )",
    "",
    "  # Audio chunks",
    "  from app.db.audio_chunks import (",
    "      save_audio_chunk,",
    "      get_audio_chunks_for_session,",
    "  )",
    "",
    "  # Enrollment history",
    "  from app.db.enrollment_history import (",
    "      save_enrollment_history,",
    "      get_enrollment_history_for_phone,",
    "      get_recent_enrollments,",
    "      get_enrollment_stats,",
    "  )",
    "",
    "  # Verified sessions",
    "  from app.db.verified_sessions import (",
    "      save_verified_session,",
    "      get_verified_session,",
    "      update_verified_session,",
    "      delete_verified_session,",
    "      get_verified_sessions_for_phone,",
    "      get_active_verified_sessions,",
    "      get_recent_verifications,",
    "  )",
    "",
    "Verification:",
    "  python -c \"from app.db import store_voice_embedding, save_verified_session, check_enrollment; print('OK')\"",
    "Expected: OK"
  ],
  "depends_on": ["MDB07"]
}
```

---

### MDB09 — Update app/services/enrollment_mongo.py

```json
{
  "task_id": "MDB09",
  "title": "Update imports in backend/app/services/enrollment_mongo.py",
  "description": "This file imports 15 symbols from app.db.mongodb in one block. After the split, each symbol has a more precise home. Update the import block to import directly from the correct sub-module. The backward-compat shim in mongodb.py means this is optional for correctness, but it is required for clarity.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open app/services/enrollment_mongo.py.",
    "Find the existing import block (around line 21):",
    "  from app.db.mongodb import (",
    "      save_enrollment_session,",
    "      get_enrollment_session as db_get_enrollment_session,",
    "      update_enrollment_session,",
    "      delete_enrollment_session,",
    "      get_enrollment_sessions_for_phone,",
    "      get_active_enrollment_sessions,",
    "      cleanup_expired_enrollment_sessions,",
    "      save_audio_chunk,",
    "      get_audio_chunks_for_session,",
    "      save_enrollment_history,",
    "      get_enrollment_history_for_phone,",
    "      get_recent_enrollments,",
    "      get_enrollment_stats,",
    "      get_voice_embedding",
    "  )",
    "",
    "Replace it with these three precise imports:",
    "  from app.db.enrollment_sessions import (",
    "      save_enrollment_session,",
    "      get_enrollment_session as db_get_enrollment_session,",
    "      update_enrollment_session,",
    "      delete_enrollment_session,",
    "      get_enrollment_sessions_for_phone,",
    "      get_active_enrollment_sessions,",
    "      cleanup_expired_enrollment_sessions,",
    "  )",
    "  from app.db.audio_chunks import (",
    "      save_audio_chunk,",
    "      get_audio_chunks_for_session,",
    "  )",
    "  from app.db.enrollment_history import (",
    "      save_enrollment_history,",
    "      get_enrollment_history_for_phone,",
    "      get_recent_enrollments,",
    "      get_enrollment_stats,",
    "  )",
    "  from app.db.embeddings import get_voice_embedding",
    "",
    "Do NOT change anything else in the file.",
    "",
    "Verification:",
    "  python -c \"from app.services.enrollment_mongo import MongoDBEnrollmentService; print('OK')\"",
    "Expected: OK"
  ],
  "depends_on": ["MDB07"]
}
```

---

### MDB10 — Update app/websocket/events.py

```json
{
  "task_id": "MDB10",
  "title": "Update imports in backend/app/websocket/events.py",
  "description": "events.py imports 6 symbols from app.db.mongodb. Update to import from the correct sub-modules.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open app/websocket/events.py.",
    "Find the existing import block:",
    "  from app.db.mongodb import (",
    "      store_voice_embedding,",
    "      find_nearest_embedding,",
    "      verify_phone_number_embedding,",
    "      check_enrollment,",
    "      get_voice_embedding,",
    "      save_verified_session",
    "  )",
    "",
    "Replace it with these two precise imports:",
    "  from app.db.embeddings import (",
    "      store_voice_embedding,",
    "      find_nearest_embedding,",
    "      verify_phone_number_embedding,",
    "      check_enrollment,",
    "      get_voice_embedding,",
    "  )",
    "  from app.db.verified_sessions import save_verified_session",
    "",
    "Do NOT change anything else in the file.",
    "",
    "Verification:",
    "  python -c \"from app.websocket.events import event_handler; print('OK')\"",
    "Expected: OK (or an import chain completing without ImportError)"
  ],
  "depends_on": ["MDB07"]
}
```

---

### MDB11 — Update app/services/verification_streaming.py and app/services/enrollment.py

```json
{
  "task_id": "MDB11",
  "title": "Update imports in app/services/verification_streaming.py and app/services/enrollment.py",
  "description": "Two service files each import a small set of symbols from app.db.mongodb. Update them to use the correct sub-module paths.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "--- app/services/verification_streaming.py ---",
    "Find: `from app.db.mongodb import get_voice_embedding, save_verified_session`",
    "Replace with:",
    "  from app.db.embeddings import get_voice_embedding",
    "  from app.db.verified_sessions import save_verified_session",
    "",
    "--- app/services/enrollment.py ---",
    "Find: `from app.db.mongodb import store_voice_embedding, get_voice_embedding`",
    "Replace with:",
    "  from app.db.embeddings import store_voice_embedding, get_voice_embedding",
    "",
    "If there is an additional lazy import inside a function body like:",
    "  `from app.db.mongodb import check_enrollment`",
    "Replace it with:",
    "  `from app.db.embeddings import check_enrollment`",
    "",
    "Verification:",
    "  python -c \"from app.services.verification_streaming import get_verification_streaming_manager; print('OK')\"",
    "  python -c \"from app.services.enrollment import get_enrollment_manager; print('OK')\"",
    "Expected: OK for both"
  ],
  "depends_on": ["MDB07"]
}
```

---

### MDB12 — Update app/api/routes/

```json
{
  "task_id": "MDB12",
  "title": "Update imports in app/api/routes/enrollment.py, verification.py, and health.py",
  "description": "Three route files import from app.db.mongodb. Update each to use the correct sub-module. Also update any lazy (inside-function) imports.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "--- app/api/routes/health.py ---",
    "Find every occurrence of: `from app.db.mongodb import check_enrollment`",
    "Replace each with:         `from app.db.embeddings import check_enrollment`",
    "",
    "--- app/api/routes/enrollment.py ---",
    "Find: `from app.db.mongodb import store_voice_embedding, get_voice_embedding, check_enrollment`",
    "Replace with:",
    "  from app.db.embeddings import store_voice_embedding, get_voice_embedding, check_enrollment",
    "Also find any lazy import inside a function body:",
    "  `from app.db.mongodb import check_enrollment`",
    "Replace each with:",
    "  `from app.db.embeddings import check_enrollment`",
    "",
    "--- app/api/routes/verification.py ---",
    "Find: `from app.db.mongodb import get_voice_embedding, check_enrollment`",
    "Replace with:",
    "  from app.db.embeddings import get_voice_embedding, check_enrollment",
    "Also find any lazy import inside a function body:",
    "  `from app.db.mongodb import check_enrollment`",
    "Replace each with:",
    "  `from app.db.embeddings import check_enrollment`",
    "",
    "Verification:",
    "  python -c \"from app.api.routes import enrollment, verification, health; print('OK')\"",
    "Expected: OK"
  ],
  "depends_on": ["MDB07"]
}
```

---

### MDB13 — Update conftest.py mock patch paths

```json
{
  "task_id": "MDB13",
  "title": "Update mock patch paths in backend/conftest.py",
  "description": "conftest.py patches 'app.db.mongodb.MongoClient'. After the split, MongoClient lives in app.db.connection, so the patch path must be updated so tests continue to mock the correct object.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open backend/conftest.py.",
    "Search for every string: `app.db.mongodb.MongoClient`",
    "Replace each occurrence with: `app.db.connection.MongoClient`",
    "Search for any other patch paths that reference `app.db.mongodb.<symbol>`",
    "  where <symbol> is now in a sub-module, and update accordingly:",
    "  - `app.db.mongodb.store_voice_embedding`   → `app.db.embeddings.store_voice_embedding`",
    "  - `app.db.mongodb.get_voice_embedding`      → `app.db.embeddings.get_voice_embedding`",
    "  - `app.db.mongodb.check_enrollment`         → `app.db.embeddings.check_enrollment`",
    "  - `app.db.mongodb.save_enrollment_session`  → `app.db.enrollment_sessions.save_enrollment_session`",
    "  - `app.db.mongodb.save_verified_session`    → `app.db.verified_sessions.save_verified_session`",
    "  (Apply the same pattern for any other patched symbols.)",
    "",
    "Verification:",
    "  python -m pytest tests/ --collect-only 2>&1 | tail -5",
    "Expected: collection completes with 0 errors"
  ],
  "depends_on": ["MDB07", "MDB08"]
}
```

---

## Execution Order

```
MDB01  Create connection.py          (no deps)

MDB02  Create embeddings.py          (MDB01)
MDB03  Create enrollment_sessions.py (MDB01)
MDB04  Create audio_chunks.py        (MDB01)
MDB05  Create enrollment_history.py  (MDB01)
MDB06  Create verified_sessions.py   (MDB01)

MDB07  Convert mongodb.py → shim     (MDB01–MDB06)
MDB08  Update __init__.py            (MDB07)

MDB09  Update enrollment_mongo.py    (MDB07)
MDB10  Update events.py              (MDB07)
MDB11  Update service files          (MDB07)
MDB12  Update route files            (MDB07)
MDB13  Update conftest.py mocks      (MDB07, MDB08)
```
