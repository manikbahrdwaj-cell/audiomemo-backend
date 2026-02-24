# Enrollment.py Split Plan

## Overview

`backend/app/services/enrollment.py` is a large module handling:
- Enrollment session management (multi-chunk, audio/embedding merging)
- Session config, chunk record, and status enums
- Database integration
- Helper functions for session and chunk management
- Enrollment confirmation service (WebSocket)

### Target Module Structure

```
backend/app/services/
├── enrollment_status.py         # NEW – EnrollmentStatus enum
├── enrollment_chunk.py          # NEW – AudioChunkRecord dataclass
├── enrollment_config.py         # NEW – EnrollmentSessionConfig dataclass
├── enrollment_session.py        # NEW – EnrollmentSession dataclass (uses above)
├── enrollment_manager.py        # NEW – EnrollmentServiceManager class, get_enrollment_manager(), create/get/remove/list session helpers
├── enrollment_helpers.py        # NEW – add_audio_chunk, finalize_enrollment, merge_audio_chunks, generate_embedding_from_merged_audio, merge_and_generate_embedding
├── enrollment_confirmation.py   # NEW – EnrollmentConfirmationService, get_confirmation_service
└── enrollment.py                # UPDATED – backward-compat shim (re-exports everything from the new modules)
```

---

## Subtasks

### ENR01 – Create `enrollment_status.py`
```json
{
  "task_id": "ENR01",
  "description": "Extract EnrollmentStatus enum to its own module.",
  "file_to_create": "backend/app/services/enrollment_status.py",
  "source_file": "backend/app/services/enrollment.py",
  "instructions": [
    "Create the file backend/app/services/enrollment_status.py",
    "Add the module docstring: 'Enrollment session status enumeration.'",
    "Add imports: from enum import Enum",
    "Copy the EnrollmentStatus enum verbatim from enrollment.py"
  ]
}
```

---

### ENR02 – Create `enrollment_chunk.py`
```json
{
  "task_id": "ENR02",
  "description": "Extract AudioChunkRecord dataclass to its own module.",
  "file_to_create": "backend/app/services/enrollment_chunk.py",
  "source_file": "backend/app/services/enrollment.py",
  "instructions": [
    "Create the file backend/app/services/enrollment_chunk.py",
    "Add the module docstring: 'Audio chunk record for enrollment sessions.'",
    "Add imports: from dataclasses import dataclass, field; from typing import Optional, Dict, Any; from datetime import datetime; import numpy as np",
    "Copy the AudioChunkRecord dataclass verbatim from enrollment.py"
  ]
}
```

---

### ENR03 – Create `enrollment_config.py`
```json
{
  "task_id": "ENR03",
  "description": "Extract EnrollmentSessionConfig dataclass to its own module.",
  "file_to_create": "backend/app/services/enrollment_config.py",
  "source_file": "backend/app/services/enrollment.py",
  "instructions": [
    "Create the file backend/app/services/enrollment_config.py",
    "Add the module docstring: 'Configuration for enrollment sessions.'",
    "Add imports: from dataclasses import dataclass, field; from typing import Optional; from enum import Enum;",
    "Copy the EnrollmentSessionConfig dataclass verbatim from enrollment.py (ensure MergeMode import is correct)",
    "If MergeMode is not defined in this file, import it from app.ml.audio_merger or app.ml.operations as appropriate"
  ]
}
```

---

### ENR04 – Create `enrollment_session.py`
```json
{
  "task_id": "ENR04",
  "description": "Extract EnrollmentSession dataclass to its own module.",
  "file_to_create": "backend/app/services/enrollment_session.py",
  "source_file": "backend/app/services/enrollment.py",
  "instructions": [
    "Create the file backend/app/services/enrollment_session.py",
    "Add the module docstring: 'Enrollment session management for multi-chunk voice enrollment.'",
    "Add imports: from dataclasses import dataclass, field; from typing import Optional, List, Dict, Any; from datetime import datetime; import numpy as np",
    "Import EnrollmentSessionConfig from .enrollment_config, EnrollmentStatus from .enrollment_status, AudioChunkRecord from .enrollment_chunk",
    "Copy the EnrollmentSession dataclass verbatim from enrollment.py, updating references to config/status/chunk record as needed"
  ]
}
```

---

### ENR05 – Create `enrollment_manager.py`
```json
{
  "task_id": "ENR05",
  "description": "Extract EnrollmentServiceManager and related helpers to their own module.",
  "file_to_create": "backend/app/services/enrollment_manager.py",
  "source_file": "backend/app/services/enrollment.py",
  "instructions": [
    "Create the file backend/app/services/enrollment_manager.py",
    "Add the module docstring: 'Manager for multiple enrollment sessions.'",
    "Add imports: from typing import Optional, Dict, List, Any; from datetime import datetime;",
    "Import EnrollmentSession from .enrollment_session",
    "Copy the EnrollmentServiceManager class and get_enrollment_manager, create_enrollment_session, get_enrollment_session, remove_session, list_sessions, find_session_by_phone, cleanup_expired_sessions, get_active_sessions helpers from enrollment.py, updating references as needed"
  ]
}
```

---

### ENR06 – Create `enrollment_helpers.py`
```json
{
  "task_id": "ENR06",
  "description": "Extract helper functions for chunk and embedding management.",
  "file_to_create": "backend/app/services/enrollment_helpers.py",
  "source_file": "backend/app/services/enrollment.py",
  "instructions": [
    "Create the file backend/app/services/enrollment_helpers.py",
    "Add the module docstring: 'Helper functions for enrollment chunk and embedding management.'",
    "Add imports: from typing import Optional, Tuple, Any; import numpy as np",
    "Import EnrollmentSession from .enrollment_session",
    "Copy the following functions verbatim from enrollment.py: add_audio_chunk, finalize_enrollment, merge_audio_chunks, generate_embedding_from_merged_audio, merge_and_generate_embedding, updating references as needed"
  ]
}
```

---

### ENR07 – Create `enrollment_confirmation.py`
```json
{
  "task_id": "ENR07",
  "description": "Extract EnrollmentConfirmationService and get_confirmation_service to their own module.",
  "file_to_create": "backend/app/services/enrollment_confirmation.py",
  "source_file": "backend/app/services/enrollment.py",
  "instructions": [
    "Create the file backend/app/services/enrollment_confirmation.py",
    "Add the module docstring: 'WebSocket-based enrollment confirmation service.'",
    "Add imports: from typing import Optional, Dict, Any, List, Tuple; import logging",
    "Copy the EnrollmentConfirmationService class and get_confirmation_service function verbatim from enrollment.py"
  ]
}
```

---

### ENR08 – Convert `enrollment.py` to backward-compatibility shim
```json
{
  "task_id": "ENR08",
  "description": "Replace enrollment.py with a shim that re-exports all public symbols from the new modules.",
  "depends_on": ["ENR01", "ENR02", "ENR03", "ENR04", "ENR05", "ENR06", "ENR07"],
  "file_to_modify": "backend/app/services/enrollment.py",
  "instructions": [
    "Replace the entire content of enrollment.py with imports that re-export all public symbols from the new modules.",
    "For example: from .enrollment_status import EnrollmentStatus; from .enrollment_chunk import AudioChunkRecord; ... etc."
  ]
}
```

---

### ENR09 – Update `__init__.py` exports (if applicable)
```json
{
  "task_id": "ENR09",
  "description": "Update backend/app/services/__init__.py to re-export new public symbols if it previously re-exported from enrollment.py.",
  "depends_on": ["ENR08"],
  "file_to_modify": "backend/app/services/__init__.py",
  "instructions": [
    "If __init__.py currently imports or re-exports anything from enrollment.py, update those imports to use the new module paths instead. If not, no change is needed."
  ]
}
```

---

## Execution Order

```
ENR01 ──┐
ENR02 ──┤
ENR03 ──┤
ENR04 ──┤
ENR05 ──┤
ENR06 ──┤
ENR07 ──┘
   │
   ▼
ENR08
   │
   ▼
ENR09
```

ENR01–ENR07 can run in parallel. ENR08 must follow all seven, then ENR09.

---

## Symbol → New Module Mapping (Quick Reference)

| Symbol | New Module |
|---|---|
| `EnrollmentStatus` | `enrollment_status` |
| `AudioChunkRecord` | `enrollment_chunk` |
| `EnrollmentSessionConfig` | `enrollment_config` |
| `EnrollmentSession` | `enrollment_session` |
| `EnrollmentServiceManager`, `get_enrollment_manager`, `create_enrollment_session`, `get_enrollment_session`, `remove_session`, `list_sessions`, `find_session_by_phone`, `cleanup_expired_sessions`, `get_active_sessions` | `enrollment_manager` |
| `add_audio_chunk`, `finalize_enrollment`, `merge_audio_chunks`, `generate_embedding_from_merged_audio`, `merge_and_generate_embedding` | `enrollment_helpers` |
| `EnrollmentConfirmationService`, `get_confirmation_service` | `enrollment_confirmation` |

---

## Important Notes for Executing LLM

- All new modules must use **absolute imports** (e.g., `from app.services.enrollment_status import EnrollmentStatus`) for consistency.
- The backward-compatibility shim in `enrollment.py` must re-export all public symbols so existing imports continue to work.
- If any dataclass or enum uses types from other new modules, import them explicitly.
- Do not change any database or WebSocket logic; only move code for modularity.
