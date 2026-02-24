"""
Backward-compatibility shim for app.ml.operations.
All symbols are now defined in their own modules.
This file re-exports them so existing imports continue to work.
"""

# Audio merging
from app.ml.audio_merger import (  # noqa: F401
    MergeMode,
    AudioMergeConfig,
    AudioMerger,
    merge_audio,
    merge_audio_files,
    get_audio_merger,
)

# Embedding metrics & statistics
from app.ml.embedding_metrics import (  # noqa: F401
    EmbeddingMetrics,
    EmbeddingComparison,
    EmbeddingStats,
)

# Embedding comparator
from app.ml.embedding_comparator import EmbeddingComparator  # noqa: F401

# Batch processor
from app.ml.embedding_batch import EmbeddingBatchProcessor  # noqa: F401

# Cache
from app.ml.embedding_cache import EmbeddingCache  # noqa: F401

# Service
from app.ml.embedding_service import (  # noqa: F401
    EmbeddingServiceConfig,
    EmbeddingService,
    get_embedding_service,
)
