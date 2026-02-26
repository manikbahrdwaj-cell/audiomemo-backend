from __future__ import annotations

from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.state import AgentState

_SYSTEM_PROMPT = (
    "You are a voice assistant. Convert the SQL result into one natural spoken sentence. "
    "No markdown, no lists. If given a JSON error, apologise briefly."
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

        response = await llm.ainvoke(messages)
        spoken_text: str = response.content.strip()

        return {"messages": [AIMessage(content=spoken_text)]}

    return node
