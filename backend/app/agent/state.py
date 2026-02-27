from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state passed between every node in the voice-agent LangGraph."""

    # LangGraph append reducer — new messages are appended, not overwritten.
    messages: Annotated[list[BaseMessage], add_messages]

    # Verified phone number (display/logging only).
    user_phone: str

    # str(_id) of the voice_embeddings document — canonical user identifier
    # used to scope all transaction queries.
    user_id: str

    # Whisper transcription of the current user query.
    utterance: str

    # SQL produced by query_compiler and reviewed by security_supervisor.
    generated_sql: str

    # JSON string returned by tool_executor after running the SQL.
    sql_result: str

    # Number of security-check retries so far (max 3).
    error_count: int

    # Text-only turn history for the session, passed in at invocation time.
    # Each entry: {"role": "user" | "assistant", "text": str}
    # Graph nodes must NOT mutate this list.
    conversation_history: list[dict]
