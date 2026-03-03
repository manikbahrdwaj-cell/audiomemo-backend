from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal

from app.agent.state import AgentState
from app.db.connection import get_transactions_collection

logger = logging.getLogger(__name__)

# Matches ISO-8601 datetime strings produced by the query_compiler LLM,
# e.g. "2025-12-01T00:00:00" or "2025-12-01T00:00:00Z".
_ISO_DT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)


def _parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware UTC datetime."""
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _coerce_datetimes(obj: object) -> object:
    """Recursively convert ISO-8601 strings inside a filter dict to datetime objects.

    MongoDB stores timestamps as BSON Date.  Comparing a BSON Date against a
    plain string always returns nothing; we must pass Python datetime objects.
    """
    if isinstance(obj, dict):
        return {k: _coerce_datetimes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_datetimes(v) for v in obj]
    if isinstance(obj, str) and _ISO_DT_RE.match(obj):
        return _parse_iso(obj)
    return obj


def _json_default(obj: object) -> object:
    """Serialise types not natively handled by json.dumps."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _run_query(query_json: str) -> list[dict]:
    """Run MongoDB query synchronously — called inside asyncio.to_thread."""
    query = json.loads(query_json)
    col = get_transactions_collection()

    filter_ = query.get("filter", {})
    # Strip stray whitespace from string filter values (guards against \n-tainted IDs).
    filter_ = {k: v.strip() if isinstance(v, str) else v for k, v in filter_.items()}
    # Coerce ISO-8601 timestamp strings to datetime objects so that MongoDB
    # BSON Date comparisons ($gte / $lt / $lte / $gt) work correctly.
    filter_ = _coerce_datetimes(filter_)
    sort_spec = query.get("sort", {"timestamp": -1})
    limit = int(query.get("limit", 20))

    # pymongo sort() expects a list of (field, direction) pairs.
    sort_list = list(sort_spec.items())

    cursor = col.find(filter_, {"_id": 0}).sort(sort_list).limit(limit)
    return list(cursor)


async def tool_executor(state: AgentState) -> dict:
    """Execute the MongoDB query stored in *state['generated_sql']* and return
    the results as a JSON string in ``{"sql_result": ...}``.

    pymongo is synchronous, so the blocking call is offloaded to a thread via
    ``asyncio.to_thread`` to avoid blocking the event loop.
    """
    query_json = state["generated_sql"]
    logger.info("[ToolExecutor] Running MongoDB query: %s", query_json)

    try:
        rows = await asyncio.to_thread(_run_query, query_json)
    except Exception as exc:
        logger.exception("[ToolExecutor] MongoDB query failed — %s", exc)
        return {"sql_result": json.dumps({"error": str(exc)})}

    logger.info("[ToolExecutor] Query returned %d row(s)", len(rows))
    if rows:
        logger.debug("[ToolExecutor] First row sample: %s", json.dumps(rows[0], default=_json_default))
    return {"sql_result": json.dumps(rows, default=_json_default)}