from app.ml.preprocessing import patch_torchaudio
patch_torchaudio()

# Initialise logging before anything else so that all subsequent imports
# (including speechbrain / torch) are captured in the log file.
from app.core.logging_config import setup_logging
setup_logging()

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import enrollment, verification, health
from app.core.config import settings
from app.middleware.request_logging import RequestLoggingMiddleware

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pre-load the ECAPA-TDNN model during startup.

    SpeechBrain's EncoderClassifier.from_hparams() writes files to the
    pretrained_models/ directory when the model is first loaded.  In
    development (uvicorn --reload), those file-system writes are picked up by
    the file watcher and trigger a server restart mid-WebSocket session.
    Loading the model here — once, at startup — ensures get_model() is a
    no-op (returns the cached global) for all subsequent requests.
    """
    try:
        _logger.info("Preloading ECAPA-TDNN model at startup…")
        from app.ml.embedding import get_model
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, get_model)
        _logger.info("✓ ECAPA-TDNN model preloaded successfully")
    except Exception as exc:
        _logger.error("Failed to preload ECAPA-TDNN model: %s", exc, exc_info=True)
        # Don't abort startup — the model will still be loaded lazily on the
        # first inference call; the reload issue will just reappear.
    yield
    # Nothing to clean up on shutdown.


app = FastAPI(
    title='Voice Biometric API',
    description='Voice enrollment and verification using ECAPA-TDNN embeddings',
    version='1.0.0',
    lifespan=lifespan,
)

# NOTE: middleware is applied in LIFO order in Starlette/FastAPI.
# RequestLoggingMiddleware is added last so it wraps everything and fires first.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(enrollment.router, tags=['enrollment'])
app.include_router(verification.router, tags=['verification'])
app.include_router(health.router, tags=['health'])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)