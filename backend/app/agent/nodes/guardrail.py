"""Guardrail node — intent classifier that gates the LangGraph pipeline.

Only utterances that are clearly about the authenticated user's own financial
data (transactions, spending, merchants, categories) are forwarded to the
query_compiler → DB path.

Everything else (greetings, general knowledge questions, weather, jokes, etc.)
is short-circuited: ``intent`` is set to ``"off_topic"`` and ``sql_result``
pre-populated with a sentinel so ``response_shaper`` can emit a polite refusal
without ever touching the database.
"""
from __future__ import annotations

import logging
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a strict topic classifier for a voice banking assistant.

The assistant can ONLY answer questions about the authenticated user's own
financial transactions stored in a database with these fields:
  - amount        (how much was spent)
  - merchant      (store / vendor name)
  - category      (Grocery, Coffee, Fuel, Online Retail, Restaurant)
  - timestamp     (when the transaction happened)

Your job: decide whether the user's message is asking about their own
transaction or spending history, OR asking about something else entirely.

Reply with EXACTLY one word — no punctuation, no explanation:
  data_query   — the question is about the user's own transactions / spending
  off_topic    — anything else (greetings, general knowledge, weather, jokes,
                 personal questions not related to transactions, etc.)

A message is data_query whenever the user (I / me / my) asks about:
  • how much they spent / how many dollars they spent / total spending
  • spending in a specific month, year, or date range (e.g. "in December 2025",
    "in the month of December", "last month", "last week", "this year")
  • where they spent money, which merchant, which store
  • what categories they bought in
  • transaction history, purchases, bills, charges, payments
  • any specific amount from their own history

A message is off_topic when it:
  • asks about other people's spending ("we", "everyone", "all of us")
  • is a greeting, chitchat, joke, or general knowledge question
  • asks about future budgets or hypotheticals ("how much should I spend")
  • is about profits, investments, revenue — not personal transactions
  • makes a statement rather than asking about transaction data

Examples:
  "What did I spend last month?"              → data_query
  "Show me my coffee purchases"               → data_query
  "What is my biggest purchase?"              → data_query
  "How much money I spend?"                   → data_query
  "How much money did I spend?"               → data_query
  "How much dollars I spend?"                 → data_query
  "How much dollars did I spend?"             → data_query
  "How much dollars I total spend?"           → data_query
  "How much have I spent in total?"           → data_query
  "How much did I spend on coffee?"           → data_query
  "How much I spent this week?"               → data_query
  "How much did I spend last month?"          → data_query
  "How much did I spend in December?"         → data_query
  "How much did I spend in December 2025?"    → data_query
  "How much dollars I spent in December 2025?"                  → data_query
  "How much dollars I spent in the month of December 2025?"     → data_query
  "How much money did I spend in the month of January?"         → data_query
  "What is my total spending in November 2025?"                 → data_query
  "Show all my transactions from December 2025"                 → data_query
  "What did I buy in the last 3 months?"      → data_query
  "What transactions do I have?"              → data_query
  "Where did I spend my money?"               → data_query
  "Show me my recent purchases"               → data_query
  "How much did I spend at Peet's Coffee?"    → data_query
  "How much are you?"                         → off_topic
  "How are you?"                              → off_topic
  "Tell me a joke"                            → off_topic
  "What is the capital of France?"            → off_topic
  "Hi, I just found now, might be you find"   → off_topic
  "Do you know me?"                           → off_topic
  "How much profits I spend?"                 → off_topic
  "How much will we all spend?"               → off_topic
  "How much we all have spent?"               → off_topic
  "How much dollars is better?"               → off_topic
  "We have to spend 8.5 dollars"              → off_topic
"""


# ---------------------------------------------------------------------------
# Node factory
# ---------------------------------------------------------------------------

def build_guardrail_node(llm) -> Callable[[AgentState], dict]:
    """Return an async LangGraph node that classifies utterance intent.

    Returns a dict that updates:
      - ``intent``:     ``"data_query"`` | ``"off_topic"``
      - ``sql_result``: pre-filled refusal sentinel when off_topic so that
                        ``response_shaper`` can immediately produce a spoken
                        reply without executing any DB query.
    """

    async def node(state: AgentState) -> dict:
        utterance = state.get("utterance", "").strip()
        logger.info(
            "[Guardrail] Classifying utterance | utterance=%r", utterance
        )

        try:
            response = await llm.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=utterance),
            ])
            label = response.content.strip().lower().split()[0]
        except Exception as exc:
            logger.warning("[Guardrail] Classification failed (%s) — defaulting to data_query", exc)
            label = "data_query"

        # Normalise to exactly one of two values
        intent = "data_query" if label == "data_query" else "off_topic"

        logger.info("[Guardrail] Intent=%s | utterance=%r", intent, utterance)

        if intent == "off_topic":
            return {
                "intent": "off_topic",
                # Sentinel value: response_shaper checks for this key
                "sql_result": '{"off_topic": true}',
                # Skip query_compiler / security / tool_executor
                "generated_sql": "",
            }

        return {"intent": "data_query"}

    return node


# ---------------------------------------------------------------------------
# Routing helper used by graph.py
# ---------------------------------------------------------------------------

def route_after_guardrail(state: AgentState) -> str:
    """Return the next node name based on the intent set by the guardrail."""
    return "query_compiler" if state.get("intent") == "data_query" else "response_shaper"
