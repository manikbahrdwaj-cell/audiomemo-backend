# Backend Refactoring Plan

> **Scope:** ;;Restructure `backend/` into a proper `app/` package layout.
> LangChain / LLM files are **excluded** from this refactor (deferred).
> Each section below is a self-contained JSON prompt you can feed directly to a coding model.

---

## Target Directory Structure (after refactor)

```
audio-memo/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI factory only
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── enrollment.py      # All /enrollment/* HTTP routes
│   │   │       ├── verification.py    # All /verify, /verification/* HTTP routes
│   │   │       └── health.py          # GET /health, GET /check/{phone_number}
│   │   ├── websocket/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py             # was websocket_handler.py
│   │   │   ├── events.py              # was websocket_events.py
│   │   │   ├── router.py              # was websocket_router.py
│   │   │   ├── monitor.py             # was websocket_monitor.py
│   │   │   ├── config.py              # was websocket_config.py
│   │   │   ├── chunk_dispatcher.py    # was chunk_progress_dispatcher.py
│   │   │   ├── audio_chunk_handler.py # was websocket_audio_chunk_handler.py
│   │   │   └── audio_chunk_receiver.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # pydantic-settings, all env vars
│   │   │   └── exceptions.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── enrollment.py          # Pydantic schemas (extracted from main.py)
│   │   │   ├── verification.py        # Pydantic schemas (extracted from main.py)
│   │   │   └── common.py              # HealthResponse, CheckResponse
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── enrollment.py          # was enrollment_service.py
│   │   │   ├── enrollment_mongo.py    # was mongodb_enrollment_service.py
│   │   │   ├── verification.py        # was verification_service.py
│   │   │   └── verification_streaming.py  # was verification_streaming_service.py
│   │   ├── ml/
│   │   │   ├── __init__.py
│   │   │   ├── preprocessing.py       # torchaudio patches (extracted from main.py + voice_embedding.py)
│   │   │   ├── embedding.py           # was voice_embedding.py
│   │   │   ├── chunking.py            # was audio_chunking.py
│   │   │   ├── operations.py          # was embedding_operations.py
│   │   │   ├── similarity.py          # was embedding_similarity_operations.py
│   │   │   ├── matching.py            # was matching_logic.py
│   │   │   └── chunk_embedding_verifier.py
│   │   └── db/
│   │       ├── __init__.py
│   │       └── mongodb.py             # was database.py
│   ├── scripts/
│   │   ├── download_model.py          # was backend/download_model.py
│   │   ├── cleanup_model_cache.py     # was backend/cleanup_model_cache.py
│   │   ├── run_tests.py               # unchanged
│   │   ├── run_edge_case_tests.py     # unchanged
│   │   ├── run_all_tests.py           # was repo-root run_all_tests.py
│   │   ├── websocket_diagnostic.py    # was repo-root websocket_diagnostic.py
│   │   ├── generate_comprehensive_audio.py
│   │   ├── generate_test_audio.py
│   │   └── demo_pages/
│   │       ├── page1.html
│   │       ├── page2.html
│   │       └── page3.html
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── comprehensive_test_suite.py
│   │   ├── fixtures/
│   │   │   └── audio/                 # was repo-root test_audio_files/
│   │   ├── unit/
│   │   └── integration/
│   ├── pretrained_models/
│   ├── requirements.txt
│   ├── requirements-test.txt
│   ├── pytest.ini
│   └── run.py
└── frontend/
```


---

## Files Excluded from This Refactor (LangChain / LLM — deferred)

These files are **not moved, not deleted**. Leave them in place:

```
backend/langchain_session_service.py
backend/langchain_session_integration.py
backend/llm_chain_builder.py
backend/session_service.py
backend/config/gemini_config.py
backend/config/openai_config.py
backend/config/llm_config.py
backend/config/__init__.py
langchaindemo.py  (repo root — leave as-is)
```

---

## Subtask Prompts

---

### T01 — Delete example / demo / verify scripts

```json
{
  "task_id": "T01",
  "title": "Delete example, demo, and verify scripts from backend/",
  "description": "Permanently delete all files listed below. They are not production code and are not needed after the refactor. Use `git rm` so the deletions are staged.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo",
  "instructions": [
    "Run the following command to delete all listed files in one shot:",
    "  git rm backend/audio_chunking_examples.py backend/audio_chunks_integration_examples.py backend/enrollment_audio_merge_demo.py backend/enrollment_service_examples.py backend/langchain_integration_examples.py backend/langchain_runnableconfig_examples.py backend/matching_logic_examples.py backend/verification_service_examples.py backend/verify_audio_merge_implementation.py backend/verify_edge_case_implementation.py backend/verify_integration_tests.py backend/verify_scipy_similarity.py backend/verify_testing_setup.py backend/AUDIO_CHUNKING_INTEGRATION.py backend/IMPLEMENTATION_COMPLETE_MATCHING_LOGIC.txt",
    "If backend/package-lock.json exists, also run: git rm backend/package-lock.json",
    "Verify with `git status` that each file is shown as 'deleted'.",
    "Do NOT delete any other files."
  ],
  "files_to_delete": [
    "backend/audio_chunking_examples.py",
    "backend/audio_chunks_integration_examples.py",
    "backend/enrollment_audio_merge_demo.py",
    "backend/enrollment_service_examples.py",
    "backend/langchain_integration_examples.py",
    "backend/langchain_runnableconfig_examples.py",
    "backend/matching_logic_examples.py",
    "backend/verification_service_examples.py",
    "backend/verify_audio_merge_implementation.py",
    "backend/verify_edge_case_implementation.py",
    "backend/verify_integration_tests.py",
    "backend/verify_scipy_similarity.py",
    "backend/verify_testing_setup.py",
    "backend/AUDIO_CHUNKING_INTEGRATION.py",
    "backend/IMPLEMENTATION_COMPLETE_MATCHING_LOGIC.txt",
    "backend/package-lock.json (if it exists)"
  ],
  "depends_on": []
}
```

---

### T02 — Move repo-root loose files into backend/

```json
{
  "task_id": "T02",
  "title": "Move repo-root loose files into backend/scripts/ and backend/tests/",
  "description": "Several Python scripts and the test audio directory live at the repo root. Move them to their proper locations inside backend/. Use `git mv` for all moves so history is preserved.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo",
  "instructions": [
    "Create destination directories if they do not already exist:",
    "  mkdir -p backend/scripts/demo_pages  backend/tests/fixtures/audio",
    "Move Python scripts to backend/scripts/:",
    "  git mv run_all_tests.py backend/scripts/run_all_tests.py",
    "  git mv websocket_diagnostic.py backend/scripts/websocket_diagnostic.py",
    "  git mv generate_comprehensive_audio.py backend/scripts/generate_comprehensive_audio.py",
    "  git mv generate_test_audio.py backend/scripts/generate_test_audio.py",
    "Move the test suite to backend/tests/:",
    "  git mv comprehensive_test_suite.py backend/tests/comprehensive_test_suite.py",
    "Move HTML demo pages:",
    "  git mv page1.html backend/scripts/demo_pages/page1.html",
    "  git mv page2.html backend/scripts/demo_pages/page2.html",
    "  git mv page3.html backend/scripts/demo_pages/page3.html",
    "Move test audio files: if test_audio_files/ exists at the repo root, move its contents:",
    "  for f in test_audio_files/*; do git mv \"$f\" backend/tests/fixtures/audio/; done",
    "  Then remove the now-empty directory: rmdir test_audio_files",
    "Verify with `git status` that all moves are staged correctly.",
    "Do NOT move langchaindemo.py — leave it at the repo root (LLM refactor deferred).",
    "Do NOT move test_results.json, test_results_enrollment_verification.json, QUICK_FIX.bat, or start.ps1."
  ],
  "depends_on": []
}
```

---

### T03 — Create the new directory scaffold inside backend/app/

```json
{
  "task_id": "T03",
  "title": "Create all new package directories and empty __init__.py files",
  "description": "Create the full directory tree for backend/app/ and add an empty __init__.py to every package directory so Python treats them as importable packages.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Run the following command to create all directories at once:",
    "  mkdir -p app/api/routes app/websocket app/core app/models app/services app/ml app/db",
    "Create an empty __init__.py in each new directory:",
    "  touch app/__init__.py app/api/__init__.py app/api/routes/__init__.py app/websocket/__init__.py app/core/__init__.py app/models/__init__.py app/services/__init__.py app/ml/__init__.py app/db/__init__.py",
    "Verify: run `find app -name '__init__.py'` and confirm all 9 files are listed.",
    "Do NOT put any code in __init__.py files yet — that happens in T17.",
    "Do NOT touch any existing files outside the new app/ directory."
  ],
  "new_directories": [
    "backend/app/",
    "backend/app/api/",
    "backend/app/api/routes/",
    "backend/app/websocket/",
    "backend/app/core/",
    "backend/app/models/",
    "backend/app/services/",
    "backend/app/ml/",
    "backend/app/db/"
  ],
  "depends_on": []
}
```

---

### T04 — Move ML files into app/ml/

```json
{
  "task_id": "T04",
  "title": "Move ML source files into backend/app/ml/",
  "description": "Use git mv to move each ML-related file from backend/ to its new path inside backend/app/ml/. Do NOT edit file contents yet — imports will be updated in T09.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Run each git mv command (all paths are relative to backend/):",
    "  git mv voice_embedding.py app/ml/embedding.py",
    "  git mv audio_chunking.py app/ml/chunking.py",
    "  git mv embedding_operations.py app/ml/operations.py",
    "  git mv embedding_similarity_operations.py app/ml/similarity.py",
    "  git mv matching_logic.py app/ml/matching.py",
    "  git mv chunk_embedding_verifier.py app/ml/chunk_embedding_verifier.py",
    "Create a NEW empty file for preprocessing (content will be filled in T09):",
    "  touch app/ml/preprocessing.py",
    "Verify: run `ls app/ml/` and confirm all 8 files are present including __init__.py.",
    "Do NOT edit any file content at this step."
  ],
  "migration_map": {
    "voice_embedding.py":                 "app/ml/embedding.py",
    "audio_chunking.py":                  "app/ml/chunking.py",
    "embedding_operations.py":            "app/ml/operations.py",
    "embedding_similarity_operations.py": "app/ml/similarity.py",
    "matching_logic.py":                  "app/ml/matching.py",
    "chunk_embedding_verifier.py":        "app/ml/chunk_embedding_verifier.py"
  },
  "depends_on": ["T03"]
}
```

---

### T05 — Move the database file into app/db/

```json
{
  "task_id": "T05",
  "title": "Move database.py into backend/app/db/mongodb.py",
  "description": "Rename and move the single database module. Do NOT edit content yet.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Run: git mv database.py app/db/mongodb.py",
    "Verify: run `ls app/db/` and confirm: __init__.py  mongodb.py"
  ],
  "migration_map": {
    "database.py": "app/db/mongodb.py"
  },
  "depends_on": ["T03"]
}
```

---

### T06 — Move WebSocket files into app/websocket/

```json
{
  "task_id": "T06",
  "title": "Move all WebSocket source files into backend/app/websocket/",
  "description": "Use git mv for each file. Do NOT edit content yet — imports are updated in T11.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Run each git mv command:",
    "  git mv websocket_handler.py app/websocket/manager.py",
    "  git mv websocket_events.py app/websocket/events.py",
    "  git mv websocket_router.py app/websocket/router.py",
    "  git mv websocket_monitor.py app/websocket/monitor.py",
    "  git mv websocket_config.py app/websocket/config.py",
    "  git mv chunk_progress_dispatcher.py app/websocket/chunk_dispatcher.py",
    "  git mv websocket_audio_chunk_handler.py app/websocket/audio_chunk_handler.py",
    "  git mv audio_chunk_receiver.py app/websocket/audio_chunk_receiver.py",
    "Verify: run `ls app/websocket/` and confirm all 9 files are present (including __init__.py)."
  ],
  "migration_map": {
    "websocket_handler.py":            "app/websocket/manager.py",
    "websocket_events.py":             "app/websocket/events.py",
    "websocket_router.py":             "app/websocket/router.py",
    "websocket_monitor.py":            "app/websocket/monitor.py",
    "websocket_config.py":             "app/websocket/config.py",
    "chunk_progress_dispatcher.py":    "app/websocket/chunk_dispatcher.py",
    "websocket_audio_chunk_handler.py":"app/websocket/audio_chunk_handler.py",
    "audio_chunk_receiver.py":         "app/websocket/audio_chunk_receiver.py"
  },
  "depends_on": ["T03"]
}
```

---

### T07 — Move Service files into app/services/

```json
{
  "task_id": "T07",
  "title": "Move service files into backend/app/services/",
  "description": "Move the four service files that are in scope. LangChain-related services (langchain_session_service.py, langchain_session_integration.py, llm_chain_builder.py, session_service.py) are NOT moved — leave them in backend/ unchanged.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Run each git mv command:",
    "  git mv enrollment_service.py app/services/enrollment.py",
    "  git mv mongodb_enrollment_service.py app/services/enrollment_mongo.py",
    "  git mv verification_service.py app/services/verification.py",
    "  git mv verification_streaming_service.py app/services/verification_streaming.py",
    "Confirm the following files remain untouched in backend/ (do NOT move them):",
    "  langchain_session_service.py",
    "  langchain_session_integration.py",
    "  llm_chain_builder.py",
    "  session_service.py",
    "Verify: run `ls app/services/` and confirm: __init__.py enrollment.py enrollment_mongo.py verification.py verification_streaming.py"
  ],
  "migration_map": {
    "enrollment_service.py":             "app/services/enrollment.py",
    "mongodb_enrollment_service.py":     "app/services/enrollment_mongo.py",
    "verification_service.py":           "app/services/verification.py",
    "verification_streaming_service.py": "app/services/verification_streaming.py"
  },
  "files_NOT_to_move": [
    "langchain_session_service.py",
    "langchain_session_integration.py",
    "llm_chain_builder.py",
    "session_service.py"
  ],
  "depends_on": ["T03"]
}
```

---

### T08 — Move backend-level utility scripts into backend/scripts/

```json
{
  "task_id": "T08",
  "title": "Move download_model.py and cleanup_model_cache.py into backend/scripts/",
  "description": "Move these two utility scripts. The scripts/ directory already has run_tests.py and run_edge_case_tests.py; leave those unchanged.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Run: git mv download_model.py scripts/download_model.py",
    "Run: git mv cleanup_model_cache.py scripts/cleanup_model_cache.py",
    "Verify: run `ls scripts/` and confirm download_model.py and cleanup_model_cache.py are present alongside run_tests.py and run_edge_case_tests.py."
  ],
  "depends_on": []
}
```

---

### T09a — Verify zero-internal-import files in app/ml/

```json
{
  "task_id": "T09a",
  "title": "Verify that app/ml/chunking.py and app/ml/matching.py have no internal imports",
  "description": "After the git mv in T04 these two files should already be self-contained. Confirm this is true; no edits are needed.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open app/ml/chunking.py. Read the import block (every line starting with 'import' or 'from').",
    "Confirm there are NO lines of the form `from audio_chunking import`, `from voice_embedding import`, or any other bare-module internal import.",
    "Allowed imports: numpy, torch, torchaudio, scipy, standard library only.",
    "Open app/ml/matching.py. Perform the same check.",
    "If both files pass — do nothing. If any internal import is found, report the exact line; do not change the file (flag for manual review)."
  ],
  "depends_on": ["T04"]
}
```

---

### T09b — Populate app/ml/preprocessing.py

```json
{
  "task_id": "T09b",
  "title": "Create app/ml/preprocessing.py by extracting patching code from main.py and embedding.py",
  "description": "app/ml/preprocessing.py was created as an empty file in T04. Populate it with two functions extracted from existing files. This must be done before T09c because T09c removes the patching block from embedding.py.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "--- Step 1: Extract patch_torchaudio() from backend/main.py ---",
    "Open backend/main.py. Locate the torchaudio patching block near the top of the file.",
    "It will be a try/except or a direct call such as `torchaudio.set_audio_backend(...)` or a monkey-patch of `torchaudio.load`.",
    "Wrap that code in a function named `patch_torchaudio()` with no parameters and no return value.",
    "Delete the original block from main.py (the bare code that is now inside the function).",
    "Add a call `patch_torchaudio()` at the top of main.py where the block used to be, so behaviour is preserved.",
    "--- Step 2: Extract patch_os_symlink() from app/ml/embedding.py ---",
    "Open app/ml/embedding.py. Look for a block guarded by `if platform.system() == 'Windows':` that patches os.symlink.",
    "If found: wrap it in a function named `patch_os_symlink()` with no parameters and no return value.",
    "Delete the original block from embedding.py.",
    "If no such block exists, define an empty stub: `def patch_os_symlink(): pass`.",
    "--- Step 3: Write app/ml/preprocessing.py ---",
    "The file must have the following structure and ONLY these imports at the top:",
    "  import os",
    "  import sys",
    "  import platform",
    "  import torchaudio",
    "Then define patch_torchaudio() (from Step 1) and patch_os_symlink() (from Step 2).",
    "No app.* imports are allowed in this file.",
    "--- Verification ---",
    "Run: python -c \"from app.ml.preprocessing import patch_torchaudio, patch_os_symlink; print('OK')\" from backend/.",
    "Expected output: OK"
  ],
  "new_file": "backend/app/ml/preprocessing.py",
  "depends_on": ["T04"]
}
```

---

### T09c — Update imports in app/ml/embedding.py

```json
{
  "task_id": "T09c",
  "title": "Fix internal import in app/ml/embedding.py",
  "description": "Replace the bare-module import of audio_chunking with the correct app.ml.chunking path. Also remove any remaining patching code that was already moved to preprocessing.py in T09b.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open app/ml/embedding.py.",
    "Find the line: `from audio_chunking import ChunkProcessor, ChunkConfig`",
    "Replace it with: `from app.ml.chunking import ChunkProcessor, ChunkConfig`",
    "Scan the file for any remaining patching block (os.symlink or torchaudio) that should have been removed in T09b. If still present, delete it now.",
    "Do NOT change any other imports or function bodies.",
    "Verification: run `python -c \"from app.ml.embedding import generate_embedding; print('OK')\"` from backend/. Expected output: OK (or a model-load log followed by OK)."
  ],
  "import_replacements": [
    {"file": "app/ml/embedding.py", "old": "from audio_chunking import", "new": "from app.ml.chunking import"}
  ],
  "depends_on": ["T09b"]
}
```

---

### T09d — Update imports in operations.py, similarity.py, and chunk_embedding_verifier.py

```json
{
  "task_id": "T09d",
  "title": "Fix internal imports in app/ml/operations.py, similarity.py, and chunk_embedding_verifier.py",
  "description": "These three files still import from bare module names (voice_embedding, audio_chunking). Update every such import to the correct app.ml.* path. Apply changes in the listed order.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "--- app/ml/operations.py ---",
    "Open the file. Read the full import block.",
    "Find every line of the form `from voice_embedding import ...`.",
    "Replace `voice_embedding` with `app.ml.embedding` — keep all imported symbols unchanged.",
    "If there is a line importing `preprocess_audio` and that function was moved to preprocessing.py in T09b, change that specific import to: `from app.ml.preprocessing import preprocess_audio`.",
    "Do NOT change any other lines.",
    "--- app/ml/similarity.py ---",
    "Find: `from voice_embedding import calculate_cosine_similarity`",
    "Replace with: `from app.ml.embedding import calculate_cosine_similarity`",
    "If there are any other `from voice_embedding import` lines, apply the same module substitution.",
    "--- app/ml/chunk_embedding_verifier.py ---",
    "Open the file. Read the import block.",
    "Apply these two substitutions to every matching import line:",
    "  `from voice_embedding import ...` → `from app.ml.embedding import ...`",
    "  `from audio_chunking import ...`  → `from app.ml.chunking import ...`",
    "--- Verification ---",
    "Run each of the following and confirm there is no ImportError:",
    "  python -c \"from app.ml.operations import AudioMerger; print('OK')\"",
    "  python -c \"from app.ml.similarity import EmbeddingSimilarityCalculator; print('OK')\"",
    "  python -c \"from app.ml.chunk_embedding_verifier import ChunkEmbeddingVerifier; print('OK')\""
  ],
  "import_replacements": [
    {"file": "app/ml/operations.py",             "old": "from voice_embedding import", "new": "from app.ml.embedding import"},
    {"file": "app/ml/similarity.py",             "old": "from voice_embedding import", "new": "from app.ml.embedding import"},
    {"file": "app/ml/chunk_embedding_verifier.py","old": "from voice_embedding import", "new": "from app.ml.embedding import"},
    {"file": "app/ml/chunk_embedding_verifier.py","old": "from audio_chunking import",  "new": "from app.ml.chunking import"}
  ],
  "depends_on": ["T09c"]
}
```

---

### T10 — Verify imports in app/db/mongodb.py

```json
{
  "task_id": "T10",
  "title": "Verify imports in backend/app/db/mongodb.py",
  "description": "The database module has no internal imports. Inspect and confirm — no edits should be needed.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Open app/db/mongodb.py.",
    "Read the import block at the top of the file.",
    "Verify there are no imports of the form `from database import ...`, `from voice_embedding import ...`, or any other bare-module internal import.",
    "If all imports are third-party (pymongo, motor, etc.) or standard library — no changes needed.",
    "If any unexpected internal import exists, replace it with the appropriate `app.*` path following the pattern from T09."
  ],
  "depends_on": ["T05"]
}
```

---

### T11 — Update imports in app/websocket/ files

```json
{
  "task_id": "T11",
  "title": "Update all internal imports inside backend/app/websocket/ files",
  "description": "Update bare-module imports to app.* paths. IMPORTANT: app/websocket/events.py previously imported from session_service and langchain_session_integration — both of those import lines must be DELETED (LangChain is deferred). Also remove any code in the file body that calls those removed symbols.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "--- app/websocket/manager.py, config.py, monitor.py, router.py, chunk_dispatcher.py ---",
    "None of these have internal imports. Verify each and leave unchanged.",

    "--- app/websocket/audio_chunk_handler.py ---",
    "Inspect imports and apply:",
    "  `from audio_chunking import`    → `from app.ml.chunking import`",
    "  `from voice_embedding import`   → `from app.ml.embedding import`",
    "  `from websocket_handler import` → `from app.websocket.manager import`",
    "Apply the same rules to app/websocket/audio_chunk_receiver.py.",

    "--- app/websocket/events.py (MOST COMPLEX) ---",
    "Step 1: Apply these import replacements (keep all symbol names unchanged):",
    "  `from websocket_handler import`               → `from app.websocket.manager import`",
    "  `from voice_embedding import`                 → `from app.ml.embedding import`",
    "  `from database import`                        → `from app.db.mongodb import`",
    "  `from chunk_progress_dispatcher import`       → `from app.websocket.chunk_dispatcher import`",
    "  `from embedding_similarity_operations import` → `from app.ml.similarity import`",
    "Step 2: DELETE these import lines entirely (do not replace):",
    "  Any line containing `from session_service import`",
    "  Any line containing `from langchain_session_integration import`",
    "Step 3: Search the file body for every call to `get_verified_session_manager` and `get_langchain_session_integration`. Comment out each call site and add: `# TODO: restore after LangChain refactor`.",
    "Step 4: Confirm no remaining references to `session_service`, `langchain`, or `llm` exist in the file."
  ],
  "import_replacements": [
    {"file": "app/websocket/events.py", "old": "from websocket_handler import",               "new": "from app.websocket.manager import"},
    {"file": "app/websocket/events.py", "old": "from voice_embedding import",                 "new": "from app.ml.embedding import"},
    {"file": "app/websocket/events.py", "old": "from database import",                        "new": "from app.db.mongodb import"},
    {"file": "app/websocket/events.py", "old": "from chunk_progress_dispatcher import",       "new": "from app.websocket.chunk_dispatcher import"},
    {"file": "app/websocket/events.py", "old": "from embedding_similarity_operations import", "new": "from app.ml.similarity import"},
    {"file": "app/websocket/events.py", "old": "from session_service import",                 "new": "DELETE THIS LINE"},
    {"file": "app/websocket/events.py", "old": "from langchain_session_integration import",   "new": "DELETE THIS LINE"}
  ],
  "depends_on": ["T06", "T09", "T10"]
}
```

---

### T12 — Update imports in app/services/ files

```json
{
  "task_id": "T12",
  "title": "Update all internal imports inside backend/app/services/ files",
  "description": "Update bare-module imports to app.* paths in the four migrated service files.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "--- app/services/enrollment.py ---",
    "Apply these replacements:",
    "  `from voice_embedding import ...`    → `from app.ml.embedding import ...`",
    "  `from database import ...`           → `from app.db.mongodb import ...`",
    "  `from embedding_operations import ...` → `from app.ml.operations import ...`",
    "  `from audio_chunking import ...`     → `from app.ml.chunking import ...`",

    "--- app/services/enrollment_mongo.py ---",
    "Apply these replacements:",
    "  `from enrollment_service import ...` → `from app.services.enrollment import ...`",
    "  `from database import ...`           → `from app.db.mongodb import ...`",
    "NOTE: Read the actual import lines and replace only the module prefix, keeping all symbol names unchanged.",

    "--- app/services/verification.py ---",
    "Apply:",
    "  `from voice_embedding import ...`    → `from app.ml.embedding import ...`",
    "  If any `from database import` lines exist: replace `database` with `app.db.mongodb`.",

    "--- app/services/verification_streaming.py ---",
    "Apply:",
    "  `from voice_embedding import ...`    → `from app.ml.embedding import ...`",
    "  `from database import ...`           → `from app.db.mongodb import ...`"
  ],
  "depends_on": ["T07", "T09", "T10"]
}
```

---

### T13 — Create app/core/config.py

```json
{
  "task_id": "T13",
  "title": "Create backend/app/core/config.py with centralised settings",
  "description": "Create a new pydantic-settings file that loads all config from environment variables / .env. This replaces hardcoded values scattered across main.py, websocket_config.py, and database.py. After creating the file, update the three places where values were previously hardcoded.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Create app/core/config.py with the following content:",
    "```python",
    "from pydantic_settings import BaseSettings",
    "from typing import List",
    "",
    "class Settings(BaseSettings):",
    "    HOST: str = '0.0.0.0'",
    "    PORT: int = 8000",
    "    RELOAD: bool = True",
    "    ALLOWED_ORIGINS: List[str] = ['http://localhost:3000', 'http://127.0.0.1:3000']",
    "    MONGODB_URL: str = 'mongodb://localhost:27017'",
    "    DATABASE_NAME: str = 'voice_biometric'",
    "    SIMILARITY_THRESHOLD: float = 0.75",
    "    WS_HEARTBEAT_INTERVAL: int = 30",
    "    WS_HEARTBEAT_TIMEOUT: int = 60",
    "    WS_MAX_MESSAGE_SIZE: int = 1048576",
    "    WS_MAX_BUFFER_SIZE: int = 10000000",
    "",
    "    class Config:",
    "        env_file = '.env'",
    "",
    "settings = Settings()",
    "```",
    "After creating the file, update hardcoded values in three locations:",
    "  1. app/db/mongodb.py: replace the hardcoded MongoDB URL with `from app.core.config import settings` + `settings.MONGODB_URL` / `settings.DATABASE_NAME`.",
    "  2. app/websocket/events.py: replace `SIMILARITY_THRESHOLD = 0.75` with `from app.core.config import settings` + `settings.SIMILARITY_THRESHOLD`.",
    "  3. app/websocket/config.py: replace hardcoded WebSocket limit integers with `settings.WS_*` values.",
    "Create backend/.env.example with:",
    "  HOST=0.0.0.0",
    "  PORT=8000",
    "  MONGODB_URL=mongodb://localhost:27017",
    "  DATABASE_NAME=voice_biometric",
    "  SIMILARITY_THRESHOLD=0.75"
  ],
  "new_files": ["backend/app/core/config.py", "backend/.env.example"],
  "depends_on": ["T03"]
}
```

---

### T14 — Extract Pydantic models from main.py into app/models/

```json
{
  "task_id": "T14",
  "title": "Extract Pydantic schemas from backend/main.py into app/models/",
  "description": "The old main.py contains all Pydantic BaseModel subclasses inline alongside route handlers. Extract them into three dedicated files. Do not delete them from main.py yet — that happens in T15.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Step 1: Open backend/main.py and read it fully to identify all classes that extend pydantic.BaseModel.",
    "Step 2: Classify each class:",
    "  Names containing 'Enrollment'           → app/models/enrollment.py",
    "  Names containing 'Verify' / 'Verification' → app/models/verification.py",
    "  HealthResponse, CheckResponse, ErrorResponse → app/models/common.py",
    "Step 3: For each file, create it with only the relevant model classes (copied verbatim) and the necessary imports at the top (`from pydantic import BaseModel`, `from typing import Optional, List`).",
    "Step 4: Verify each file is syntactically valid Python.",
    "Step 5: Do NOT remove schemas from main.py yet — that is done in T15."
  ],
  "new_files": [
    "backend/app/models/enrollment.py",
    "backend/app/models/verification.py",
    "backend/app/models/common.py"
  ],
  "depends_on": ["T03"]
}
```

---

### T15 — Split main.py into route files and a new app/main.py factory

```json
{
  "task_id": "T15",
  "title": "Split backend/main.py into route modules and a lean app/main.py factory",
  "description": "The existing main.py (~1736 lines) contains all routes, middleware, startup code, and schemas. Extract HTTP routes into three APIRouter files, then create a new lean app/main.py, then delete the old main.py.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "--- Step 1: Create app/api/routes/health.py ---",
    "Extract the GET /health and GET /check/{phone_number} handlers from main.py.",
    "Header imports:",
    "  from fastapi import APIRouter",
    "  from app.models.common import HealthResponse, CheckResponse",
    "  from app.db.mongodb import check_enrollment",
    "  router = APIRouter()",

    "--- Step 2: Create app/api/routes/enrollment.py ---",
    "Extract ALL handlers whose paths start with /enrollment/ from main.py.",
    "Header imports:",
    "  from fastapi import APIRouter, File, UploadFile, Form, HTTPException",
    "  from app.models.enrollment import <all enrollment response schemas needed>",
    "  from app.services.enrollment import <all service functions needed>",
    "  from app.db.mongodb import store_voice_embedding, get_voice_embedding, check_enrollment",
    "  from app.ml.embedding import generate_embedding",
    "  router = APIRouter()",

    "--- Step 3: Create app/api/routes/verification.py ---",
    "Extract ALL handlers whose paths start with /verify or /verification/ from main.py. Also extract any WebSocket endpoint defined in main.py.",
    "Header imports:",
    "  from fastapi import APIRouter, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect",
    "  from app.models.verification import <all verification schemas needed>",
    "  from app.services.verification import <required service functions>",
    "  from app.services.verification_streaming import <required streaming functions>",
    "  from app.db.mongodb import get_voice_embedding, check_enrollment",
    "  from app.ml.embedding import generate_embedding, calculate_cosine_similarity",
    "  from app.websocket.manager import ConnectionManager",
    "  from app.websocket.events import event_handler",
    "  from app.websocket.monitor import monitor",
    "  from app.websocket.router import WebSocketMessageRouter, RouteConfig, MessageType",
    "  router = APIRouter()",
    "IMPORTANT: Do NOT include any import from session_service or langchain in this file.",

    "--- Step 4: Create app/main.py (the entire file content) ---",
    "  from app.ml.preprocessing import patch_torchaudio",
    "  patch_torchaudio()",
    "  from fastapi import FastAPI",
    "  from fastapi.middleware.cors import CORSMiddleware",
    "  from app.api.routes import enrollment, verification, health",
    "  from app.core.config import settings",
    "  app = FastAPI(title='Voice Biometric API', description='Voice enrollment and verification using ECAPA-TDNN embeddings', version='1.0.0')",
    "  app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])",
    "  app.include_router(enrollment.router, prefix='/enrollment', tags=['enrollment'])",
    "  app.include_router(verification.router, prefix='/verification', tags=['verification'])",
    "  app.include_router(health.router, tags=['health'])",

    "--- Step 5: Delete the old backend/main.py ---",
    "Run: git rm main.py",

    "--- Step 6: Smoke test ---",
    "From backend/, run: python -c 'from app.main import app; print(len(app.routes), \"routes loaded\")'",
    "It must print a non-zero route count with no ImportError."
  ],
  "new_files": [
    "backend/app/api/routes/health.py",
    "backend/app/api/routes/enrollment.py",
    "backend/app/api/routes/verification.py",
    "backend/app/main.py"
  ],
  "files_to_delete": ["backend/main.py"],
  "depends_on": ["T09", "T10", "T11", "T12", "T13", "T14"]
}
```

---

### T16 — Update backend/run.py

```json
{
  "task_id": "T16",
  "title": "Update backend/run.py to use the new app.main:app entry point",
  "description": "The existing run.py starts the old main:app. Replace its entire content.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Replace the entire content of backend/run.py with:",
    "  import uvicorn",
    "  from app.core.config import settings",
    "  if __name__ == '__main__':",
    "      uvicorn.run('app.main:app', host=settings.HOST, port=settings.PORT, reload=settings.RELOAD)",
    "Test: from backend/ run `python run.py` and verify the server starts without ImportError."
  ],
  "depends_on": ["T13", "T15"]
}
```

---

### T17 — Populate __init__.py files with public APIs

```json
{
  "task_id": "T17",
  "title": "Populate each package __init__.py with its public API re-exports",
  "description": "Add re-export statements to each __init__.py. If a listed symbol does not exist in its module, skip it and leave a `# TODO: add when implemented` comment.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "app/ml/__init__.py:",
    "  from app.ml.embedding import generate_embedding, calculate_cosine_similarity",
    "  from app.ml.chunking import ChunkConfig, AudioChunker",
    "  from app.ml.preprocessing import patch_torchaudio",

    "app/db/__init__.py:",
    "  from app.db.mongodb import (get_database, store_voice_embedding, get_voice_embedding, check_enrollment, find_nearest_embedding, save_verified_session)",

    "app/services/__init__.py:",
    "  from app.services.enrollment import create_enrollment_session, finalize_enrollment",
    "  from app.services.verification import create_verification_session, process_verification_session",

    "app/websocket/__init__.py:",
    "  from app.websocket.manager import ConnectionManager",
    "  from app.websocket.events import event_handler",
    "  from app.websocket.router import WebSocketMessageRouter",

    "app/models/__init__.py  — leave empty.",
    "app/core/__init__.py    — leave empty.",
    "app/__init__.py         — leave empty."
  ],
  "depends_on": ["T09", "T10", "T11", "T12", "T15"]
}
```

---

### T18 — Update test imports

```json
{
  "task_id": "T18",
  "title": "Update import paths in all test files under backend/tests/",
  "description": "All test files reference old bare-module import names. Update them to use app.* paths. Also patch conftest.py to ensure sys.path is set correctly.",
  "working_directory": "/Users/vibhorgoyal/PersonalWorkspace/audio-memo/backend",
  "instructions": [
    "Step 1: Update backend/conftest.py — add these two lines at the very top:",
    "  import sys, os",
    "  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))",

    "Step 2: Run this grep to find all outdated imports in test files:",
    "  grep -rn 'from voice_embedding\\|from database\\|from enrollment_service\\|from audio_chunking\\|from websocket_handler\\|from verification_service\\|from embedding_operations\\|from embedding_similarity\\|from matching_logic\\|from chunk_progress_dispatcher\\|from mongodb_enrollment_service\\|from verification_streaming_service' tests/",

    "Step 3: For each match, apply the replacement from the table below. Replace only the module name — keep all imported symbol names unchanged.",

    "Step 4: Grep for any test-file imports of session_service or langchain. Comment out those lines and any test code that depends solely on those symbols. Add: `# TODO: restore after LangChain refactor`.",

    "Step 5: Verify test collection works: python -m pytest tests/ --collect-only"
  ],
  "import_replacement_table": {
    "voice_embedding":                  "app.ml.embedding",
    "audio_chunking":                   "app.ml.chunking",
    "embedding_operations":             "app.ml.operations",
    "embedding_similarity_operations":  "app.ml.similarity",
    "matching_logic":                   "app.ml.matching",
    "database":                         "app.db.mongodb",
    "enrollment_service":               "app.services.enrollment",
    "mongodb_enrollment_service":       "app.services.enrollment_mongo",
    "verification_service":             "app.services.verification",
    "verification_streaming_service":   "app.services.verification_streaming",
    "websocket_handler":                "app.websocket.manager",
    "chunk_progress_dispatcher":        "app.websocket.chunk_dispatcher"
  },
  "depends_on": ["T09", "T10", "T11", "T12", "T17"]
}
```

---

## Execution Order

```
T01  Delete scripts            (no deps)
T02  Move root files           (no deps)
T03  Create scaffold           (no deps)
T08  Move backend scripts      (no deps)

T04  Move ML files             (T03)
T05  Move DB file              (T03)
T06  Move WS files             (T03)
T07  Move service files        (T03)
T13  Create core/config.py     (T03)
T14  Extract models/           (T03)

T09a Verify zero-import files   (T04)
T09b Populate preprocessing.py  (T04)
T09c Fix embedding.py imports   (T09b)
T09d Fix ops/sim/verifier imports (T09c)
T10  Verify DB imports          (T05)

T11  Update WS imports          (T06, T09d, T10)
T12  Update service imports     (T07, T09d, T10)

T15  Split main.py → routes     (T09d–T14)

T16  Update run.py              (T13, T15)
T17  Populate __init__.py       (T09d–T12, T15)
T18  Update test imports        (T09d–T12, T17)
```
