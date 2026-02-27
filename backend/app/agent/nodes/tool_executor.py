from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal

from app.agent.state import AgentState
from app.db.connection import get_transactions_collection

logger = logging.getLogger(__name__)


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