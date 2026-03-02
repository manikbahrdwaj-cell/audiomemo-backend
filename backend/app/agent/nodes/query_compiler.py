from __future__ import annotations

import json
import re
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage

import logging

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_TEMPLATE = """\
You are a MongoDB query generator. Translate the user's natural-language question
into a valid JSON query against the "transactions" collection.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLLECTION: transactions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Field        Type      Notes
-----------  --------  -----------------------------------------
user_id      string    Authenticated user ID — ALWAYS filter by this
amount       number    Transaction amount in USD (e.g. 52.3)
merchant     string    Store / vendor name (e.g. "Whole Foods Market")
category     string    Exactly one of: "Grocery", "Coffee", "Fuel",
                       "Online Retail", "Restaurant"
timestamp    ISODate   UTC datetime stored as Python datetime object;
                       compare with ISO 8601 strings using $gte / $lte
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HARD RULES:
1. The "filter" object MUST always contain exactly: "user_id": "{user_id}"
2. Use only these read operators: $gt $lt $gte $lte $in $regex $and $or $not
3. NEVER use: $where  $function  $accumulator  $expr  or any write operators
4. Return ONLY a JSON object (optionally inside ```json … ``` fences):
     {{"filter": {{...}}, "sort": {{...}}, "limit": <int>}}
5. "sort" defaults to {{"timestamp": -1}} (newest first).
6. "limit" defaults to 10. Use a smaller number when the user asks for "last N".
   Use 100 when the user asks for totals / sums over a time period (e.g. "how much did I spend in December").

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUERY EXAMPLES (user_id omitted for brevity):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Show my last 3 transactions"
  → {{"filter": {{"user_id": "{user_id}"}}, "sort": {{"timestamp": -1}}, "limit": 3}}

"What did I spend on coffee?"
  → {{"filter": {{"user_id": "{user_id}", "category": "Coffee"}}, "sort": {{"timestamp": -1}}, "limit": 10}}

"Transactions above $100"
  → {{"filter": {{"user_id": "{user_id}", "amount": {{"$gt": 100}}}}, "sort": {{"timestamp": -1}}, "limit": 10}}

"Grocery and restaurant spending"
  → {{"filter": {{"user_id": "{user_id}", "category": {{"$in": ["Grocery", "Restaurant"]}}}}, "sort": {{"timestamp": -1}}, "limit": 10}}

"Spending at Amazon"
  → {{"filter": {{"user_id": "{user_id}", "merchant": {{"$regex": "Amazon", "$options": "i"}}}}, "sort": {{"timestamp": -1}}, "limit": 10}}

"Transactions this month (February 2026)"
  → {{"filter": {{"user_id": "{user_id}", "timestamp": {{"$gte": "2026-02-01T00:00:00", "$lt": "2026-03-01T00:00:00"}}}}, "sort": {{"timestamp": -1}}, "limit": 10}}

"How much did I spend in December 2025?" / "Total spending in December 2025" / "How much dollars I spent in December 2025?"
  → {{"filter": {{"user_id": "{user_id}", "timestamp": {{"$gte": "2025-12-01T00:00:00", "$lt": "2026-01-01T00:00:00"}}}}, "sort": {{"timestamp": -1}}, "limit": 100}}

"How much did I spend in November 2025?" / "Total in November"
  → {{"filter": {{"user_id": "{user_id}", "timestamp": {{"$gte": "2025-11-01T00:00:00", "$lt": "2025-12-01T00:00:00"}}}}, "sort": {{"timestamp": -1}}, "limit": 100}}

"Largest purchase"
  → {{"filter": {{"user_id": "{user_id}"}}, "sort": {{"amount": -1}}, "limit": 1}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If the question cannot be answered from this schema,
fall back to the default query (all recent transactions):
  {{"filter": {{"user_id": "{user_id}"}}, "sort": {{"timestamp": -1}}, "limit": 10}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

_DEFAULT_QUERY_TEMPLATE = (
    '{{"filter": {{"user_id": "{user_id}"}}, '
    '"sort": {{"timestamp": -1}}, "limit": 10}}'
)


def _extract_json(raw: str) -> str:
    """Return JSON from a ```json ... ``` fenced block or the first {...} found."""
    match = re.search(r"```json\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # fallback: extract first {...} block
    match = re.search(r"(\{.*\})", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()


def build_query_compiler_node(llm) -> Callable[[AgentState], dict]:
    """Return an async LangGraph node that compiles a user utterance to a MongoDB query.

    The node:
    1. Builds a system prompt scoped to the verified user's phone number.
    2. Prepends prior conversation turns when ``conversation_history`` is
       non-empty so the LLM has multi-turn context.
    3. Forwards any ``SECURITY ERROR`` ``SystemMessage`` from ``state["messages"]``
       so the LLM can self-correct the previous attempt.
    4. Invokes the LLM with the current utterance as the user message.
    5. Extracts JSON from ```json``` fences or falls back to the first {...} block.
    """

    async def node(state: AgentState) -> dict:
        phone = state["user_phone"]
        user_id = state["user_id"]
        system_prompt = _SYSTEM_TEMPLATE.format(user_id=user_id)

        # --- Build user message -------------------------------------------------
        user_parts: list[str] = []

        # Inject prior conversation turns for multi-turn context
        history = state.get("conversation_history", [])
        if history:
            lines = ["Previous conversation:"]
            for turn in history:
                role = turn.get("role", "user").capitalize()
                lines.append(f"{role}: {turn.get('text', '')}")
            user_parts.append("\n".join(lines))

        user_parts.append(f"Current question: {state['utterance']}")
        user_message_text = "\n\n".join(user_parts)

        # --- Collect messages for LLM invocation --------------------------------
        messages: list = [
            SystemMessage(content=system_prompt),
        ]

        # Forward any SECURITY ERROR messages from previous attempts
        for msg in state.get("messages", []):
            if isinstance(msg, SystemMessage) and "SECURITY ERROR" in msg.content:
                messages.append(msg)

        messages.append(HumanMessage(content=user_message_text))

        # --- Invoke LLM ---------------------------------------------------------
        logger.info("[QueryCompiler] Compiling query | phone=%s user_id=%s utterance=%r", phone, user_id, state["utterance"])
        response = await llm.ainvoke(messages)
        logger.debug("[QueryCompiler] Raw LLM output: %s", response.content)
        query_json = _extract_json(response.content)

        # Validate it is parseable JSON; fall back to default on failure.
        try:
            json.loads(query_json)
            logger.info("[QueryCompiler] Generated query: %s", query_json)
        except (json.JSONDecodeError, ValueError):
            logger.warning("[QueryCompiler] JSON parse failed — using default query")
            query_json = _DEFAULT_QUERY_TEMPLATE.format(user_id=user_id)

        return {"generated_sql": query_json}

    return node
