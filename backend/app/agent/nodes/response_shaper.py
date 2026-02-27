from __future__ import annotations

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
    "Mention merchant names, categories, or totals as appropriate. "
    "If the result is an empty array, say there are no matching transactions. "
    "If given a JSON error object, apologise briefly without exposing internal details."
)


def build_response_shaper_node(llm) -> Callable[[AgentState], dict]:
    """Return an async LangGraph node that converts SQL results to spoken text.

    The node passes the raw ``sql_result`` JSON string to the LLM and asks it
    to produce a single, plain spoken sentence suitable for TTS synthesis.
    JSON error objects from ``tool_executor`` are handled gracefully — the LLM
    is instructed to apologise without exposing internal details.
    """

    async def node(state: AgentState) -> dict:
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=state["sql_result"]),
        ]

        logger.info("[ResponseShaper] Shaping SQL result into speech")
        response = await llm.ainvoke(messages)
        spoken_text: str = response.content.strip()
        logger.info("[ResponseShaper] Spoken response: %r", spoken_text)

        return {"messages": [AIMessage(content=spoken_text)]}

    return node
