"""LangGraph StateGraph wiring the purchasing agent.

Flow:
    ingest -> agent_reason -> guardrail
    agent_reason = the LLM investigates via tool calls and proposes a decision
    guardrail    = deterministic recompute + validate/override the proposal

    guardrail --> finalize            (reject / investigate)
    guardrail --> escalate            (infeasible)
    guardrail --> approval_gate --> act   (accept / modify / source_alternate / confirm_existing)
    act -> validate
    validate --> finalize             (outcome acceptable)
    validate --> replan -> agent_reason   (discrepancy, retries remain)  <-- feedback loop
    validate --> escalate             (discrepancy, no retries)
    escalate -> finalize

`interrupt_before=['act']` lets the runner pause for human-in-the-loop approval.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState
from app.config import get_settings

settings = get_settings()


def _route_after_guardrail(state: AgentState) -> str:
    dtype = state["decision"]["type"]
    if dtype in ("reject", "investigate"):
        return "finalize"
    if dtype == "escalate":
        return "escalate"
    return "approval_gate"


def _route_after_validate(state: AgentState) -> str:
    if state["validation"]["acceptable"]:
        return "finalize"
    if state.get("iteration", 0) < settings.max_agent_iters:
        return "replan"
    return "escalate"


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("ingest", nodes.ingest)
    g.add_node("agent_reason", nodes.agent_reason)
    g.add_node("guardrail", nodes.guardrail)
    g.add_node("approval_gate", nodes.approval_gate)
    g.add_node("act", nodes.act)
    g.add_node("validate", nodes.validate)
    g.add_node("replan", nodes.replan)
    g.add_node("escalate", nodes.escalate)
    g.add_node("finalize", nodes.finalize)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "agent_reason")
    g.add_edge("agent_reason", "guardrail")
    g.add_conditional_edges("guardrail", _route_after_guardrail,
                            {"finalize": "finalize", "escalate": "escalate",
                             "approval_gate": "approval_gate"})
    g.add_edge("approval_gate", "act")
    g.add_edge("act", "validate")
    g.add_conditional_edges("validate", _route_after_validate,
                            {"finalize": "finalize", "replan": "replan", "escalate": "escalate"})
    g.add_edge("replan", "agent_reason")
    g.add_edge("escalate", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=MemorySaver(), interrupt_before=["act"])


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH
