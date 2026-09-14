"""Shared agent state passed between LangGraph nodes."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    scenario: str                       # "S1" | "S2"
    situation: Dict[str, Any]           # input: sku, node_id, recommended_qty, po_id, ...
    facts: Dict[str, Any]               # gathered context from tools
    retrieved_rules: List[str]          # RAG SOPs
    proposed_decision: Dict[str, Any]   # the LLM's proposed decision (pre-guardrail)
    analysis: Dict[str, Any]            # computed numbers + constraint results
    decision: Dict[str, Any]            # {type, qty, supplier_id, rationale, confidence, factors}
    needs_human: bool
    approval: Dict[str, Any]            # {status: pending|approved|rejected, edited_qty?}
    action_result: Dict[str, Any]       # created/modified PO or supplier response
    validation: Dict[str, Any]          # post-action validation outcome
    iteration: int
    status: str                         # running|awaiting_approval|done|escalated
    # Accumulated across nodes (reducers append instead of replace):
    feedback: Annotated[List[Dict[str, Any]], operator.add]
    trace: Annotated[List[Dict[str, Any]], operator.add]
