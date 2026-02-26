"""
Centralised logging configuration for the Voice Biometric backend.

Log policy
----------
- One log file per day  :  logs/app.log  (rotated at midnight)
- Archives kept 6 days  :  logs/app.log.YYYY-MM-DD.gz  (gzip-compressed)
- Total retention       :  7 days  (today + 6 compressed archives)
- Console               :  INFO and above
- File                  :  DEBUG and above (maximum detail)
"""

import gzip
import logging
import logging.handlers
import os
import shutil
from pathlib import Path

# ── Log directory ──────────────────────────────────────────────────────────
# backend/app/core/logging_config.py  → go 3 levels up to reach backend/
_BACKEND_DIR = Path(__file__).parent.parent.parent
LOG_DIR = _BACKEND_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

# ── Formatters ────────────────────────────────────────────────────────────
_FILE_FORMAT = (
    "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
)
_CONSOLE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ── Gzip rotation helpers ─────────────────────────────────────────────────

def _gzip_namer(default_name: str) -> str:
    """Append .gz so rotated files are stored compressed."""
    return default_name + ".gz"


def _gzip_rotator(source: str, dest: str) -> None:
    """Compress the rotated log file and delete the original."""
    with open(source, "rb") as f_in, gzip.open(dest, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(source)


# ── Public setup function ─────────────────────────────────────────────────

def setup_logging() -> None:
    """
    Configure application-wide logging.

    Call this once at application startup, before any other code runs.
    Subsequent calls are idempotent (handlers are not duplicated).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()

    # Guard against double-initialisation (e.g. uvicorn --reload)
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)

    file_fmt = logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT)
    console_fmt = logging.Formatter(_CONSOLE_FORMAT, datefmt=_DATE_FORMAT)

    # ── Rotating file handler (daily, keep 6 archives = 7 days total) ──
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(LOG_FILE),
        when="midnight",
        interval=1,
        backupCount=6,   # 6 gzip archives + 1 active file = 7 days
        encoding="utf-8",
        utc=False,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)
    file_handler.namer = _gzip_namer
    file_handler.rotator = _gzip_rotator

    # ── Console handler ──────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # ── Third-party noise reduction ──────────────────────────────────────
    # These libs are very chatty at DEBUG; keep them at WARNING unless you
    # need low-level details.
    _quiet = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "speechbrain",
        "torch",
        "torchaudio",
        "pymongo",
        "motor",
        "huggingface_hub",
        "filelock",
        "urllib3",
        "httpx",
        "httpcore",
        "multipart",
    ]
    for name in _quiet:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Our own code: full detail
    logging.getLogger("app").setLevel(logging.DEBUG)

    logging.getLogger("app.core.logging_config").info(
        "Logging initialised — file=%s  rotation=midnight  retention=7 days",
        LOG_FILE,
    )
