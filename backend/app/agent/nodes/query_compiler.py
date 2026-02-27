from __future__ import annotations

import json
import re
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import AgentState

_SYSTEM_TEMPLATE = """\
You are a MongoDB query generator for a transactions collection.

Collection: transactions
Document schema:
  {{
    "phone_number": "<string>",
    "amount":       <number>,
    "merchant":     "<string>",
    "category":     "<string>"   // e.g. Grocery, Coffee, Fuel, Online Retail, Restaurant
    "timestamp":    <ISODate>
  }}

Rules:
- You MUST include "phone_number": "{phone_number}" inside the "filter" object.
- Only use read operators ($gt, $lt, $gte, $lte, $in, $regex, $and, $or).
- Do NOT use $where, $function, or $accumulator.
- Return ONLY valid JSON matching the schema below, optionally wrapped in ```json ... ``` fences:

  {{"filter": {{...}}, "sort": {{"timestamp": -1}}, "limit": <int>}}

- "sort" defaults to {{"timestamp": -1}} if not relevant to the question.
- "limit" defaults to 10.
- If the question cannot be answered with this schema use:
  {{"filter": {{"phone_number": "{phone_number}"}}, "sort": {{"timestamp": -1}}, "limit": 10}}
"""

_DEFAULT_QUERY_TEMPLATE = (
    '{{"filter": {{"phone_number": "{phone_number}"}}, '
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
        system_prompt = _SYSTEM_TEMPLATE.format(phone_number=phone)

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
        response = await llm.ainvoke(messages)
        query_json = _extract_json(response.content)

        # Validate it is parseable JSON; fall back to default on failure.
        try:
            json.loads(query_json)
        except (json.JSONDecodeError, ValueError):
            query_json = _DEFAULT_QUERY_TEMPLATE.format(phone_number=phone)

        return {"generated_sql": query_json}

    return node
