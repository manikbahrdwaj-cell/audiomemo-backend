# Operations.py Split Plan

## Overview

`backend/app/ml/operations.py` is **1207 lines** and contains two fully independent concerns:
1. **Audio Merging** – `MergeMode`, `AudioMergeConfig`, `AudioMerger`, and 3 convenience functions
2. **Embedding Pipeline** – metrics, comparison, batch processing, caching, and a high-level service

### Target Module Structure

```
backend/app/ml/
├── audio_merger.py          # NEW  – MergeMode, AudioMergeConfig, AudioMerger, merge_audio(), merge_audio_files(), get_audio_merger()
├── embedding_metrics.py     # NEW  – EmbeddingMetrics, EmbeddingComparison, EmbeddingStats
├── embedding_comparator.py  # NEW  – EmbeddingComparator
├── embedding_batch.py       # NEW  – EmbeddingBatchProcessor
├── embedding_cache.py       # NEW  – EmbeddingCache
├── embedding_service.py     # NEW  – EmbeddingServiceConfig, EmbeddingService, get_embedding_service()
└── operations.py            # UPDATED – backward-compat shim (re-exports everything from the 6 new modules)
```

### Known External Usages (files that import from operations.py)
- `backend/app/services/enrollment.py` line 18: `from app.ml.operations import AudioMerger, AudioMergeConfig, MergeMode`

---

## Subtasks

### OPS01 – Create `audio_merger.py`

```json
{
  "task_id": "OPS01",
  "description": "Create backend/app/ml/audio_merger.py by extracting the audio-merging code from backend/app/ml/operations.py",
  "file_to_create": "backend/app/ml/audio_merger.py",
  "source_file": "backend/app/ml/operations.py",
  "instructions": [
    "Create the file backend/app/ml/audio_merger.py",
    "Add the module docstring: 'Audio merging and concatenation utilities.'",
    "Add the following imports at the top of the file:",
    "  import numpy as np",
    "  import torch",
    "  import logging",
    "  from typing import Dict, List, Optional, Tuple, Union",
    "  from dataclasses import dataclass",
    "  from enum import Enum",
    "  from app.ml.embedding import preprocess_audio",
    "  logger = logging.getLogger(__name__)",
    "Copy the following classes and functions verbatim from backend/app/ml/operations.py into the new file in this exact order:",
    "  1. class MergeMode(Enum) – the enum with CONCATENATE, OVERLAP, CROSSFADE, MIX values",
    "  2. @dataclass class AudioMergeConfig – the full dataclass including __post_init__ validation",
    "  3. class AudioMerger – the full class including all methods: __init__, _get_sample_rate_from_bytes, _resample_audio, _create_crossfade_envelope, merge_audio_segments, _concatenate, _merge_with_overlap, _merge_with_crossfade, _merge_with_mix, merge_from_files, save_merged_audio, get_merge_stats",
    "  4. function merge_audio() – the convenience function at the bottom of operations.py",
    "  5. function merge_audio_files() – the convenience function at the bottom of operations.py",
    "  6. function get_audio_merger() – the convenience function at the bottom of operations.py",
    "Do NOT copy any embedding-related classes (EmbeddingMetrics, EmbeddingComparison, EmbeddingStats, EmbeddingComparator, EmbeddingBatchProcessor, EmbeddingCache, EmbeddingServiceConfig, EmbeddingService) or the get_embedding_service() function",
    "Do NOT modify operations.py in this task"
  ]
}
```

---

### OPS02 – Create `embedding_metrics.py`

```json
{
  "task_id": "OPS02",
  "description": "Create backend/app/ml/embedding_metrics.py by extracting the EmbeddingMetrics, EmbeddingComparison, and EmbeddingStats classes from backend/app/ml/operations.py",
  "file_to_create": "backend/app/ml/embedding_metrics.py",
  "source_file": "backend/app/ml/operations.py",
  "instructions": [
    "Create the file backend/app/ml/embedding_metrics.py",
    "Add the module docstring: 'Embedding quality metrics and statistics.'",
    "Add the following imports at the top of the file:",
    "  import numpy as np",
    "  import logging",
    "  from typing import Optional",
    "  from dataclasses import dataclass",
    "  from datetime import datetime",
    "  logger = logging.getLogger(__name__)",
    "Add the following class definition (note: the @dataclass decorator and class header are MISSING in the source file operations.py due to a bug – add them here correctly):",
    "  @dataclass",
    "  class EmbeddingMetrics:",
    "      'Metrics and metadata for an embedding'",
    "      embedding_id: str",
    "      phone_number: str",
    "      dimensions: int",
    "      magnitude: float",
    "      mean_value: float",
    "      std_value: float",
    "      min_value: float",
    "      max_value: float",
    "      timestamp: datetime",
    "      generation_method: str  # 'standard', 'chunked', 'auto'",
    "      audio_duration_ms: Optional[float] = None",
    "      n_chunks: Optional[int] = None",
    "      quality_score: Optional[float] = None",
    "Copy the following classes verbatim from backend/app/ml/operations.py into the new file after EmbeddingMetrics:",
    "  1. @dataclass class EmbeddingComparison – the full dataclass with all fields (query_phone, enrolled_phone, cosine_similarity, euclidean_distance, manhattan_distance, chebyshev_distance, is_match, confidence, threshold)",
    "  2. class EmbeddingStats – the full class including calculate_metrics() static method and calculate_embedding_quality() static method",
    "Do NOT copy any audio-merging classes or any other embedding classes",
    "Do NOT modify operations.py in this task"
  ]
}
```

---

### OPS03 – Create `embedding_comparator.py`

```json
{
  "task_id": "OPS03",
  "description": "Create backend/app/ml/embedding_comparator.py by extracting the EmbeddingComparator class from backend/app/ml/operations.py",
  "file_to_create": "backend/app/ml/embedding_comparator.py",
  "source_file": "backend/app/ml/operations.py",
  "instructions": [
    "Create the file backend/app/ml/embedding_comparator.py",
    "Add the module docstring: 'Embedding comparison utilities using multiple distance metrics.'",
    "Add the following imports at the top of the file:",
    "  import numpy as np",
    "  import logging",
    "  from typing import Dict, List",
    "  from app.ml.embedding import calculate_cosine_similarity",
    "  from app.ml.embedding_metrics import EmbeddingComparison",
    "  logger = logging.getLogger(__name__)",
    "Copy the following class verbatim from backend/app/ml/operations.py:",
    "  class EmbeddingComparator – the full class including compare() static method and batch_compare() static method",
    "In the compare() method, the import of calculate_cosine_similarity comes from app.ml.embedding (already imported at the top)",
    "In batch_compare(), calls to EmbeddingComparator.compare() remain unchanged",
    "Do NOT copy any other classes",
    "Do NOT modify operations.py in this task"
  ]
}
```

---

### OPS04 – Create `embedding_batch.py`

```json
{
  "task_id": "OPS04",
  "description": "Create backend/app/ml/embedding_batch.py by extracting the EmbeddingBatchProcessor class from backend/app/ml/operations.py",
  "file_to_create": "backend/app/ml/embedding_batch.py",
  "source_file": "backend/app/ml/operations.py",
  "instructions": [
    "Create the file backend/app/ml/embedding_batch.py",
    "Add the module docstring: 'Batch processing of multiple audio files for embedding generation.'",
    "Add the following imports at the top of the file:",
    "  import logging",
    "  from typing import Callable, Dict, Optional, Tuple",
    "  import numpy as np",
    "  from app.ml.embedding import generate_embedding, generate_embedding_with_chunking, get_embedding_with_auto_chunking",
    "  from app.ml.embedding_metrics import EmbeddingMetrics, EmbeddingStats",
    "  logger = logging.getLogger(__name__)",
    "Copy the following class verbatim from backend/app/ml/operations.py:",
    "  class EmbeddingBatchProcessor – the full class including process_batch() static method",
    "The process_batch() method uses generate_embedding, generate_embedding_with_chunking, get_embedding_with_auto_chunking (already imported from app.ml.embedding) and EmbeddingStats (already imported from app.ml.embedding_metrics)",
    "Do NOT copy any other classes",
    "Do NOT modify operations.py in this task"
  ]
}
```

---

### OPS05 – Create `embedding_cache.py`

```json
{
  "task_id": "OPS05",
  "description": "Create backend/app/ml/embedding_cache.py by extracting the EmbeddingCache class from backend/app/ml/operations.py",
  "file_to_create": "backend/app/ml/embedding_cache.py",
  "source_file": "backend/app/ml/operations.py",
  "instructions": [
    "Create the file backend/app/ml/embedding_cache.py",
    "Add the module docstring: 'In-memory LRU-style cache for voice embeddings.'",
    "Add the following imports at the top of the file:",
    "  import logging",
    "  import numpy as np",
    "  from typing import Dict, Optional, Tuple",
    "  from datetime import datetime",
    "  logger = logging.getLogger(__name__)",
    "Copy the following class verbatim from backend/app/ml/operations.py:",
    "  class EmbeddingCache – the full class including __init__, get(), put(), clear(), get_stats() methods",
    "Do NOT copy any other classes",
    "Do NOT modify operations.py in this task"
  ]
}
```

---

### OPS06 – Create `embedding_service.py`

```json
{
  "task_id": "OPS06",
  "description": "Create backend/app/ml/embedding_service.py by extracting EmbeddingServiceConfig, EmbeddingService, and get_embedding_service() from backend/app/ml/operations.py",
  "file_to_create": "backend/app/ml/embedding_service.py",
  "source_file": "backend/app/ml/operations.py",
  "instructions": [
    "Create the file backend/app/ml/embedding_service.py",
    "Add the module docstring: 'High-level embedding service with caching, quality management, and batch support.'",
    "Add the following imports at the top of the file:",
    "  import logging",
    "  import numpy as np",
    "  from typing import Callable, Dict, Optional, Tuple",
    "  from app.ml.embedding import generate_embedding, generate_embedding_with_chunking, get_embedding_with_auto_chunking",
    "  from app.ml.embedding_metrics import EmbeddingMetrics, EmbeddingComparison, EmbeddingStats",
    "  from app.ml.embedding_comparator import EmbeddingComparator",
    "  from app.ml.embedding_batch import EmbeddingBatchProcessor",
    "  from app.ml.embedding_cache import EmbeddingCache",
    "  logger = logging.getLogger(__name__)",
    "Copy the following classes and function verbatim from backend/app/ml/operations.py in this order:",
    "  1. class EmbeddingServiceConfig – the full class including __init__",
    "  2. class EmbeddingService – the full class including __init__, generate(), compare(), batch_generate(), get_cache_stats(), clear_cache()",
    "  3. The module-level variable: _service: Optional[EmbeddingService] = None",
    "  4. function get_embedding_service() – the full function",
    "Do NOT copy any audio-merging classes or any other embedding classes that are now in their own modules",
    "Do NOT modify operations.py in this task"
  ]
}
```

---

### OPS07 – Convert `operations.py` to backward-compatibility shim

```json
{
  "task_id": "OPS07",
  "description": "Replace the content of backend/app/ml/operations.py with a backward-compatibility shim that re-exports all public symbols from the new modules",
  "depends_on": ["OPS01", "OPS02", "OPS03", "OPS04", "OPS05", "OPS06"],
  "file_to_modify": "backend/app/ml/operations.py",
  "instructions": [
    "Replace the ENTIRE content of backend/app/ml/operations.py with the following:",
    "---BEGIN FILE CONTENT---",
    "\"\"\"",
    "Backward-compatibility shim for app.ml.operations.",
    "All symbols are now defined in their own modules.",
    "This file re-exports them so existing imports continue to work.",
    "\"\"\"",
    "",
    "# Audio merging",
    "from app.ml.audio_merger import (  # noqa: F401",
    "    MergeMode,",
    "    AudioMergeConfig,",
    "    AudioMerger,",
    "    merge_audio,",
    "    merge_audio_files,",
    "    get_audio_merger,",
    ")",
    "",
    "# Embedding metrics & statistics",
    "from app.ml.embedding_metrics import (  # noqa: F401",
    "    EmbeddingMetrics,",
    "    EmbeddingComparison,",
    "    EmbeddingStats,",
    ")",
    "",
    "# Embedding comparator",
    "from app.ml.embedding_comparator import EmbeddingComparator  # noqa: F401",
    "",
    "# Batch processor",
    "from app.ml.embedding_batch import EmbeddingBatchProcessor  # noqa: F401",
    "",
    "# Cache",
    "from app.ml.embedding_cache import EmbeddingCache  # noqa: F401",
    "",
    "# Service",
    "from app.ml.embedding_service import (  # noqa: F401",
    "    EmbeddingServiceConfig,",
    "    EmbeddingService,",
    "    get_embedding_service,",
    ")",
    "---END FILE CONTENT---",
    "Do NOT leave any original class/function definitions in operations.py – they all now live in the new modules"
  ]
}
```

---

### OPS08 – Verify `enrollment.py` still works

```json
{
  "task_id": "OPS08",
  "description": "Verify that backend/app/services/enrollment.py imports from app.ml.operations still resolve correctly after the split",
  "depends_on": ["OPS07"],
  "file_to_check": "backend/app/services/enrollment.py",
  "instructions": [
    "Open backend/app/services/enrollment.py",
    "Find line 18: from app.ml.operations import AudioMerger, AudioMergeConfig, MergeMode",
    "Confirm this import still works because operations.py is now a shim that re-exports AudioMerger, AudioMergeConfig, and MergeMode from app.ml.audio_merger",
    "Do NOT change the import in enrollment.py – the shim handles it",
    "If the import line is NOT 'from app.ml.operations import AudioMerger, AudioMergeConfig, MergeMode', update this task's check to match the actual import statement",
    "Run a quick syntax check by reading the top ~30 lines of enrollment.py and confirming no NameError would occur for AudioMerger, AudioMergeConfig, or MergeMode"
  ]
}
```

---

### OPS09 – Update `__init__.py` exports (if applicable)

```json
{
  "task_id": "OPS09",
  "description": "Update backend/app/ml/__init__.py to export the new public symbols from the new modules",
  "depends_on": ["OPS07"],
  "file_to_modify": "backend/app/ml/__init__.py",
  "instructions": [
    "Open backend/app/ml/__init__.py",
    "Read its current content",
    "If the file currently imports or re-exports anything that was in operations.py (e.g. EmbeddingService, AudioMerger, etc.), update those import paths to point to the new specific modules instead of app.ml.operations",
    "If the file currently has 'from app.ml.operations import ...' update it to use the new module paths:",
    "  AudioMerger, AudioMergeConfig, MergeMode, merge_audio, merge_audio_files, get_audio_merger  → from app.ml.audio_merger",
    "  EmbeddingMetrics, EmbeddingComparison, EmbeddingStats                                        → from app.ml.embedding_metrics",
    "  EmbeddingComparator                                                                           → from app.ml.embedding_comparator",
    "  EmbeddingBatchProcessor                                                                       → from app.ml.embedding_batch",
    "  EmbeddingCache                                                                                → from app.ml.embedding_cache",
    "  EmbeddingServiceConfig, EmbeddingService, get_embedding_service                              → from app.ml.embedding_service",
    "If the file does not import anything from operations.py, no change is needed"
  ]
}
```

---

## Execution Order

```
OPS01 ──┐
OPS02 ──┤
OPS03 ──┤──► OPS07 ──► OPS08
OPS04 ──┤         └──► OPS09
OPS05 ──┤
OPS06 ──┘
```

OPS01–OPS06 are all independent and can be executed in parallel or any order.  
OPS07 must run after all six creation tasks complete.  
OPS08 and OPS09 must run after OPS07.

---

## Symbol → New Module Mapping (Quick Reference)

| Symbol | New Module |
|---|---|
| `MergeMode` | `app.ml.audio_merger` |
| `AudioMergeConfig` | `app.ml.audio_merger` |
| `AudioMerger` | `app.ml.audio_merger` |
| `merge_audio()` | `app.ml.audio_merger` |
| `merge_audio_files()` | `app.ml.audio_merger` |
| `get_audio_merger()` | `app.ml.audio_merger` |
| `EmbeddingMetrics` | `app.ml.embedding_metrics` |
| `EmbeddingComparison` | `app.ml.embedding_metrics` |
| `EmbeddingStats` | `app.ml.embedding_metrics` |
| `EmbeddingComparator` | `app.ml.embedding_comparator` |
| `EmbeddingBatchProcessor` | `app.ml.embedding_batch` |
| `EmbeddingCache` | `app.ml.embedding_cache` |
| `EmbeddingServiceConfig` | `app.ml.embedding_service` |
| `EmbeddingService` | `app.ml.embedding_service` |
| `get_embedding_service()` | `app.ml.embedding_service` |

---

## Important Notes for Executing LLM

1. **Bug fix required in OPS02**: In `operations.py`, the `EmbeddingMetrics` class is missing its `@dataclass` decorator and `class EmbeddingMetrics:` header line. The fields appear as bare module-level code between `get_merge_stats()` and `EmbeddingComparison`. When creating `embedding_metrics.py`, add the missing decorator and class header.

2. **Do not change** `backend/app/services/enrollment.py` – the existing import `from app.ml.operations import AudioMerger, AudioMergeConfig, MergeMode` will continue working through the shim created in OPS07.

3. **Imports in new files must use the `app.ml.*` absolute path**, not relative imports, to be consistent with the rest of the codebase.

4. **The `_service` global variable** in `embedding_service.py` must be at module level (not inside the class) exactly as in the original `operations.py`.


---

## Validation Results (2026-02-24)

### Task-by-Task Status

| Task | Status | Notes |
|------|--------|-------|
| OPS01 – `audio_merger.py` | ✅ PASSED | 672 lines; all symbols present (`MergeMode`, `AudioMergeConfig`, `AudioMerger`, `merge_audio`, `merge_audio_files`, `get_audio_merger`). `torch`/`torchaudio` unresolved-import warnings are pre-existing environment issues, not new errors from the refactoring. |
| OPS02 – `embedding_metrics.py` | ✅ PASSED | 120 lines; missing `@dataclass`/`class EmbeddingMetrics:` bug was correctly fixed. `EmbeddingComparison`, `EmbeddingStats` all present. No errors. |
| OPS03 – `embedding_comparator.py` | ✅ PASSED | 102 lines; `EmbeddingComparator` present with `compare()` and `batch_compare()`. No errors. |
| OPS04 – `embedding_batch.py` | ✅ PASSED | 75 lines; `EmbeddingBatchProcessor` present. No errors. |
| OPS05 – `embedding_cache.py` | ✅ PASSED | 80 lines; `EmbeddingCache` with `get`, `put`, `clear`, `get_stats`. No errors. |
| OPS06 – `embedding_service.py` | ✅ PASSED | 196 lines; `EmbeddingServiceConfig`, `EmbeddingService`, `_service` global, `get_embedding_service()`. No errors. |
| OPS07 – `operations.py` shim | ❌ FAILED → fixed by OPS10 | Shim was NOT applied. The original 1206-line file was left intact with the shim text incorrectly embedded as a string literal inside `AudioMerger.__init__`, causing real compile errors: unexpected indentation, `return` outside function, undefined variables. Fixed by OPS10. |
| OPS08 – verify `enrollment.py` | ✅ PASSED | Line 18 import `from app.ml.operations import AudioMerger, AudioMergeConfig, MergeMode` confirmed present and correct. No NameErrors. No changes needed. |
| OPS09 – update `__init__.py` | ✅ PASSED (no-op) | No imports from `app.ml.operations` present; no change needed. |

---

### OPS10 – Fix `operations.py` shim (remediation for failed OPS07) ✅ COMPLETED 2026-02-24

**Root cause:** OPS07 inserted the shim content as a string literal inside `AudioMerger.__init__` instead of replacing the entire file content. This left all original class/function definitions in place and caused compile errors.

**Fix applied:** Replaced the entire content of `backend/app/ml/operations.py` with the clean 37-line shim defined in OPS07. Verified with static analysis: no errors remain.
