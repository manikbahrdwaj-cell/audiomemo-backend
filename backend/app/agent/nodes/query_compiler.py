from __future__ import annotations

import re
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import AgentState

_SYSTEM_TEMPLATE = """\
You are a SQL query generator for a transactions database.

Schema:
  transactions (
    id           SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    amount       NUMERIC(10,2) NOT NULL,
    merchant     VARCHAR(100) NOT NULL,
    category     VARCHAR(50) NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL
  )

Rules:
- Generate a single SELECT query only.
- You MUST include the filter: WHERE phone_number = '{phone_number}'
- Do NOT generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or any DDL.
- Return ONLY the SQL statement, optionally wrapped in ```sql ... ``` fences.
- If the user question cannot be answered with this schema, return:
  SELECT * FROM transactions WHERE phone_number = '{phone_number}' LIMIT 10;
"""


def _extract_sql(raw: str) -> str:
    """Return SQL from a ```sql ... ``` fenced block, or the full output."""
    match = re.search(r"```sql\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw.strip()


def build_query_compiler_node(llm) -> Callable[[AgentState], dict]:
    """Return an async LangGraph node that compiles a user utterance to SQL.

    The node:
    1. Builds a system prompt scoped to the verified user's phone number.
    2. Prepends prior conversation turns when ``conversation_history`` is
       non-empty so the LLM has multi-turn context.
    3. Forwards any ``SECURITY ERROR`` ``SystemMessage`` from ``state["messages"]``
       so the LLM can self-correct the previous attempt.
    4. Invokes the LLM with the current utterance as the user message.
    5. Extracts SQL from ```sql``` fences or falls back to the raw output.
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
        sql = _extract_sql(response.content)

        return {"generated_sql": sql}

    return node
