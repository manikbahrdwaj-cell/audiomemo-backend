"""
HTTP request / response logging middleware.

What is logged
--------------
Request
  - Unique request-ID (8-char hex, also echoed in X-Request-ID response header)
  - HTTP method, path, query string
  - Client IP + port
  - Safe headers  (Authorization / Cookie / API-key values are redacted)
  - Content-Type and Content-Length
  - Body — for JSON payloads the first 2 000 chars are logged;
            for multipart/form-data (file uploads) only the size is logged

Response
  - Status code
  - Wall-clock latency (ms)
  - Response body size (bytes)
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.middleware.request_logging")

# ── Request-ID context variable ──────────────────────────────────────────
# Set at the start of every request so that log lines emitted deep inside
# service / ML code can include the ID by reading this var.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Headers whose *values* must never appear in logs
_REDACTED_HEADERS = frozenset(
    {"authorization", "cookie", "x-api-key", "x-auth-token", "x-secret"}
)
# Headers with no useful diagnostic value — skip them entirely
_SKIP_HEADERS = frozenset(
    {"host", "accept-encoding", "connection", "accept-language"}
)

# Maximum characters of a JSON body to log
_MAX_BODY_LOG_CHARS = 2_000


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Detailed structured logging for every HTTP request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request_id_var.set(request_id)

        start = time.perf_counter()

        content_type = request.headers.get("content-type", "")
        content_length = request.headers.get("content-length", "?")

        # ── Log the incoming request ──────────────────────────────────────
        # Only read body bytes for non-file-upload requests so we do not
        # disrupt streaming / large upload handling.
        body_log = await _describe_body(request, content_type)

        logger.info(
            "[%s] --> %s %s | client=%s | query=%s | content-type=%s | "
            "content-length=%s | headers=%s | body=%s",
            request_id,
            request.method,
            request.url.path,
            _client(request),
            dict(request.query_params) or "{}",
            content_type or "-",
            content_length,
            _safe_headers(dict(request.headers)),
            body_log,
        )

        # ── Execute the request ──────────────────────────────────────────
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1_000
            logger.error(
                "[%s] <-- %s %s | EXCEPTION after %.2fms | %s: %s",
                request_id,
                request.method,
                request.url.path,
                elapsed_ms,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1_000
        resp_size = response.headers.get("content-length", "?")

        # ── Log the outgoing response ─────────────────────────────────────
        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "[%s] <-- %s %s | status=%d | elapsed=%.2fms | response-size=%s bytes",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            resp_size,
        )

        response.headers["X-Request-ID"] = request_id
        return response


# ── Helpers ───────────────────────────────────────────────────────────────

def _client(request: Request) -> str:
    if request.client:
        return f"{request.client.host}:{request.client.port}"
    return "unknown"


def _safe_headers(headers: dict) -> dict:
    result = {}
    for key, value in headers.items():
        lk = key.lower()
        if lk in _SKIP_HEADERS:
            continue
        result[key] = "[REDACTED]" if lk in _REDACTED_HEADERS else value
    return result


async def _describe_body(request: Request, content_type: str) -> str:
    """Return a loggable summary of the request body."""
    # Don't read multipart bodies — file upload streams should not be buffered here.
    if "multipart/form-data" in content_type:
        cl = request.headers.get("content-length", "?")
        return f"<multipart/form-data {cl} bytes — not logged>"

    if "application/x-www-form-urlencoded" in content_type:
        cl = request.headers.get("content-length", "?")
        return f"<form-urlencoded {cl} bytes — not logged>"

    # For JSON and text payloads we read and cache the body.
    # BaseHTTPMiddleware in Starlette re-injects the cached bytes so the
    # endpoint can still read the body normally.
    try:
        body_bytes = await request.body()
    except Exception:
        return "<body-read-error>"

    if not body_bytes:
        return "<empty>"

    if "application/json" in content_type:
        try:
            parsed = json.loads(body_bytes)
            formatted = json.dumps(parsed, ensure_ascii=False)
            return formatted[:_MAX_BODY_LOG_CHARS] + (
                "…" if len(formatted) > _MAX_BODY_LOG_CHARS else ""
            )
        except Exception:
            pass

    if "text/" in content_type:
        try:
            text = body_bytes.decode("utf-8")
            return text[:_MAX_BODY_LOG_CHARS]
        except Exception:
            pass

    return f"<binary {len(body_bytes)} bytes>"
