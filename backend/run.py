import os
import uvicorn
from app.core.config import settings

if __name__ == '__main__':
    # When running with reload=True, only watch the app/ source directory.
    # pretrained_models/ is excluded because SpeechBrain writes .py and .ckpt
    # files there during model loading, which would otherwise trigger a reload
    # and kill any active WebSocket connections.
    _extra: dict = {}
    if settings.RELOAD:
        _base = os.path.dirname(os.path.abspath(__file__))
        _app_dir = os.path.join(_base, 'app')
        # Exclude ALL pretrained_models directories — SpeechBrain imports and
        # touches custom.py from these directories during model loading.
        # Even with reload_dirs restricted to app/, uvicorn/watchfiles also
        # tracks every imported Python source file, so custom.py ends up in
        # the watch list and triggers an infinite reload loop unless excluded.
        _extra['reload_dirs'] = [_app_dir]
        _extra['reload_excludes'] = [
            os.path.join(_base, 'pretrained_models'),       # backend/pretrained_models/
            os.path.join(_app_dir, 'ml', 'pretrained_models'),  # app/ml/pretrained_models/
        ]

    uvicorn.run(
        'app.main:app',
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        **_extra,
    )
