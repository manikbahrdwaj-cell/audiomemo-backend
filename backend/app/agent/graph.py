from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph

from app.agent.llm import build_llm
from app.agent.nodes.query_compiler import build_query_compiler_node
from app.agent.nodes.response_shaper import build_response_shaper_node
from app.agent.nodes.security_supervisor import security_supervisor
from app.agent.nodes.tool_executor import tool_executor
from app.agent.state import AgentState

# Module-level singleton — compiled once on first call to get_graph().
_graph: CompiledGraph | None = None


def build_graph() -> CompiledGraph:
    """Compile and return the voice-agent LangGraph state machine.

    Node wiring:
        query_compiler → security_supervisor
        security_supervisor → query_compiler  (on security failure, via Command)
        security_supervisor → tool_executor   (on pass, via Command)
        tool_executor → response_shaper
        response_shaper → END

    Authentication is enforced upstream in VoiceAgentOrchestrator — no
    biometric_gate node is present in this graph.
    """
    llm = build_llm()

    graph = StateGraph(AgentState)

    # --- Register nodes --------------------------------------------------------
    graph.add_node("query_compiler", build_query_compiler_node(llm))
    graph.add_node("security_supervisor", security_supervisor)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("response_shaper", build_response_shaper_node(llm))

    # --- Entry point -----------------------------------------------------------
    graph.set_entry_point("query_compiler")

    # --- Edges -----------------------------------------------------------------
    # query_compiler always proceeds to security_supervisor for validation.
    graph.add_edge("query_compiler", "security_supervisor")

    # security_supervisor uses langgraph.types.Command to route internally:
    #   - failure → back to query_compiler  (with SECURITY ERROR message)
    #   - pass    → tool_executor
    # No explicit add_edge needed for Command-driven routing.

    graph.add_edge("tool_executor", "response_shaper")
    graph.add_edge("response_shaper", END)

    return graph.compile()


def get_graph() -> CompiledGraph:
    """Return the compiled graph singleton, building it on first call."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
