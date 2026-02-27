from __future__ import annotations

import json

from langchain_core.messages import SystemMessage
from langgraph.types import Command

from app.agent.state import AgentState

# MongoDB operators that allow arbitrary code execution.
_FORBIDDEN_OPERATORS = {"$where", "$function", "$accumulator"}


async def security_supervisor(state: AgentState) -> Command:
    """Validate the generated MongoDB query JSON before it reaches the database.

    Three checks are applied:
    1. The value must be valid JSON.
    2. The ``filter.phone_number`` field must equal the verified user's phone so
       results are always scoped to the authenticated user.
    3. The JSON must not reference any code-execution operators.

    On failure the node retries up to 3 times by routing back to
    ``query_compiler`` with a corrective ``SECURITY ERROR`` message.
    After 3 failures a ``ValueError("SECURITY_MAX_RETRIES")`` is raised so
    the orchestrator can return a safe apology to the user.

    On success the node routes to ``tool_executor``.
    """
    raw = state.get("generated_sql", "")
    phone = state["user_phone"]

    # --- Check 1: valid JSON ---------------------------------------------------
    try:
        query = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return _handle_failure(state, "Generated query is not valid JSON.")

    # --- Check 2: phone_number filter present and correctly scoped -------------
    filt = query.get("filter", {})
    if filt.get("phone_number") != phone:
        reason = (
            f'filter.phone_number must equal "{phone}". '
            "Always scope queries to the authenticated user."
        )
        return _handle_failure(state, reason)

    # --- Check 3: no forbidden operators ---------------------------------------
    raw_lower = raw.lower()
    for op in _FORBIDDEN_OPERATORS:
        if op in raw_lower:
            reason = f"Query contains forbidden operator: {op}"
            return _handle_failure(state, reason)

    # --- All checks passed -----------------------------------------------------
    return Command(goto="tool_executor")


def _handle_failure(state: AgentState, reason: str) -> Command:
    error_count = state.get("error_count", 0) + 1

    if error_count >= 3:
        raise ValueError("SECURITY_MAX_RETRIES")

    return Command(
        update={
            "messages": [SystemMessage(content=f"SECURITY ERROR: {reason}. Retry.")],
            "error_count": error_count,
        },
        goto="query_compiler",
    )
