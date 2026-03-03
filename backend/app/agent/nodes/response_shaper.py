from __future__ import annotations

import json
import logging
from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a voice assistant summarising a user's financial transactions. "
    "Convert the JSON result into one or two natural spoken sentences. "
    "Rules: no markdown, no bullet lists, no symbols like $-signs spelled out as 'dollars'. "
    "Format amounts as e.g. '52 dollars 30 cents' or '52.30 dollars'. "
    "If the user's question asks for a total or 'how much did I spend', "
    "compute the SUM of all 'amount' fields in the result and state it clearly, "
    "e.g. 'You spent 120 dollars 50 cents in total in December 2025.' "
    "Mention merchant names, categories, or totals as appropriate. "
    "If the result is an empty array, say there are no matching transactions. "
    "If given a JSON error object, apologise briefly without exposing internal details."
)

# Spoken response when query_compiler could not produce a valid filtered query.
_CLARIFY_RESPONSE = (
    "I'm sorry, I didn't quite understand that. Could you please rephrase your "
    "question? For example, you can ask: how much did I spend at Starbucks, or "
    "what are my transactions in December."
)

# Spoken refusal for off-topic questions
_OFF_TOPIC_RESPONSE = (
    "I can only help with questions about your own transactions and spending history. "
    "Please ask me about your purchases, merchants, or categories."
)


def build_response_shaper_node(llm) -> Callable[[AgentState], dict]:
    """Return an async LangGraph node that converts results to spoken text.

    Handles two cases:
    - off_topic sentinel (set by guardrail): returns a polite refusal without
      calling the LLM or DB.
    - normal sql_result JSON: shapes it into a natural spoken sentence via LLM.
    """

    async def node(state: AgentState) -> dict:
        sql_result = state.get("sql_result", "")

        # --- Short-circuit sentinels ------------------------------------------
        try:
            parsed = json.loads(sql_result) if sql_result else None
            if isinstance(parsed, dict):
                if parsed.get("off_topic"):
                    logger.info("[ResponseShaper] Off-topic query — returning refusal")
                    return {"messages": [AIMessage(content=_OFF_TOPIC_RESPONSE)]}
                if parsed.get("__clarify__"):
                    logger.info("[ResponseShaper] Parse-error sentinel — returning clarification")
                    return {"messages": [AIMessage(content=_CLARIFY_RESPONSE)]}
        except (json.JSONDecodeError, TypeError):
            pass

        # --- Normal path -------------------------------------------------------
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=sql_result),
        ]

        logger.info("[ResponseShaper] Shaping SQL result into speech")
        response = await llm.ainvoke(messages)
        spoken_text: str = response.content.strip()
        logger.info("[ResponseShaper] Spoken response: %r", spoken_text)

        return {"messages": [AIMessage(content=spoken_text)]}

    return node
