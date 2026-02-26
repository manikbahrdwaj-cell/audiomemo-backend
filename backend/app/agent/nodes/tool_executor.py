from __future__ import annotations

import json
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)


async def tool_executor(state: AgentState) -> dict:
    """Execute *state['generated_sql']* via the MCP PostgreSQL tool.

    Opens a fresh MCP ``ClientSession`` for each invocation (stateless),
    calls the ``"query"`` tool with the generated SQL, serialises the
    result to a JSON string, and returns ``{"sql_result": json_string}``.

    On any exception the error is logged at WARNING level and a JSON error
    object is returned so ``response_shaper`` can apologise gracefully
    without crashing the graph.
    """
    sql = state["generated_sql"]

    try:
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres", settings.DATABASE_URL],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("query", {"sql": sql})

        # result.content is a list of TextContent / other content blocks.
        # Normalise to a plain list of dicts / strings for the shaper.
        rows: list = []
        for block in result.content:
            if hasattr(block, "text"):
                try:
                    rows.append(json.loads(block.text))
                except json.JSONDecodeError:
                    rows.append(block.text)
            else:
                rows.append(str(block))

        return {"sql_result": json.dumps(rows)}

    except Exception as exc:
        logger.warning("MCP tool_executor failed: %s", exc)
        return {"sql_result": json.dumps({"error": str(exc)})}
