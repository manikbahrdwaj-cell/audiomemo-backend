from __future__ import annotations

from langchain_core.messages import SystemMessage
from langgraph.types import Command

from app.agent.state import AgentState

_MUTATING_KEYWORDS = {"DELETE", "UPDATE", "DROP", "INSERT", "TRUNCATE", "ALTER"}


async def security_supervisor(state: AgentState) -> Command:
    """Validate the generated SQL before it reaches the database.

    Two checks are applied:
    1. The verified user's phone number must appear verbatim in the SQL so
       results are always scoped to the authenticated user.
    2. The SQL must not contain any mutating / DDL keywords.

    On failure the node retries up to 3 times by routing back to
    ``query_compiler`` with a corrective ``SECURITY ERROR`` message.
    After 3 failures a ``ValueError("SECURITY_MAX_RETRIES")`` is raised so
    the orchestrator can return a safe apology to the user.

    On success the node routes to ``tool_executor``.
    """
    sql = state.get("generated_sql", "")
    phone = state["user_phone"]
    sql_upper = sql.upper()

    # --- Check 1: phone number filter present ----------------------------------
    if phone not in sql:
        reason = f"SQL must contain a filter on phone_number = '{phone}'"
        return _handle_failure(state, reason)

    # --- Check 2: no mutating keywords -----------------------------------------
    for keyword in _MUTATING_KEYWORDS:
        if keyword in sql_upper:
            reason = f"SQL contains forbidden keyword: {keyword}"
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
