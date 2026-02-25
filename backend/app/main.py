from app.ml.preprocessing import patch_torchaudio
patch_torchaudio()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import enrollment, verification, health
from app.core.config import settings

app = FastAPI(
    title='Voice Biometric API',
    description='Voice enrollment and verification using ECAPA-TDNN embeddings',
    version='1.0.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(enrollment.router, tags=['enrollment'])
app.include_router(verification.router, tags=['verification'])
app.include_router(health.router, tags=['health'])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)