"""LangGraph node implementations.

The agent is genuinely LLM-driven when an API key with quota is present: in `agent_reason`
the model calls tools to investigate and proposes a decision. `guardrail` then independently
recomputes the authoritative numbers and VALIDATES the proposal, overriding it if it violates
a constraint or contradicts the math (this is where hallucinations are caught).

With no usable LLM the same node runs a deterministic planner, so tests, evaluation, and the
demo all work identically offline.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from app.agent.policy import decide_purchase
from app.agent.prompts import AGENT_SYSTEM, build_agent_user
from app.agent.state import AgentState
from app.agent.tools_schema import READ_TOOL_NAMES, TOOL_SPECS, dispatch
from app.config import get_settings
from app.db.session import session_scope
from app.llm.provider import get_chat
from app.tools import actions, queries
from app.tools.constraints import (
    ConstraintCheck,
    ConstraintResult,
    compute_net_requirement,
    evaluate_constraints,
)

settings = get_settings()
MAX_TOOL_STEPS = 8


def _ev(node: str, title: str, summary: str, data: Dict | None = None) -> Dict:
    return {"node": node, "title": title, "summary": summary, "data": data or {}}


# --------------------------------------------------------------------------- helpers
def _phase(state: AgentState) -> str:
    if state.get("scenario") != "S2":
        return "review"
    return "cover_gap" if state.get("feedback") else "verify_existing"


def _gather_facts(session, situation: Dict) -> Dict:
    sku = situation["sku"]
    product = queries.get_product(session, sku)
    category = product["category"] if product else "unknown"
    primary = queries.get_vendor_terms(session, sku)
    return {
        "product": product,
        "inventory": queries.get_inventory(session, sku),
        "demand": queries.get_demand(session, sku),
        "open_pos": queries.get_open_purchase_orders(session, sku),
        "primary_vendor": primary,
        "budget": queries.get_budget(session, category),
        "alternate_vendors": queries.get_alternate_vendors(
            session, sku, primary["vendor_id"] if primary else ""),
    }


def _constraint_result_for(facts: Dict, vendor: Optional[Dict], qty: int) -> ConstraintResult:
    return evaluate_constraints(
        qty=max(int(qty), 0),
        unit_price=vendor["unit_price"] if vendor else 0.0,
        min_order_qty=vendor["min_order_qty"] if vendor else 0,
        budget_remaining=facts["budget"].get("remaining", 0.0),
        vendor_capacity=vendor["available_capacity"] if vendor else 0,
        vendor_reliability=vendor["reliability_score"] if vendor else 0.0,
        min_reliability=settings.min_supplier_reliability,
    )


def _net_requirement(facts: Dict) -> int:
    dem = facts["demand"]
    demand = dem.get("demand_over_horizon", 0) if dem.get("available") else 0
    return compute_net_requirement(
        demand, facts["inventory"]["safety_stock"], facts["inventory"]["on_hand"],
        facts["open_pos"]["incoming_open_pos"])


# --------------------------------------------------------------------------- ingest
def ingest(state: AgentState) -> AgentState:
    sit = state["situation"]
    scenario = state.get("scenario", "S1")
    summary = (
        f"Scenario {scenario}: review reorder recommendation to buy "
        f"{sit.get('recommended_qty')} units of {sit.get('sku')}."
        if scenario == "S1"
        else f"Scenario {scenario}: vendor response for existing PO {sit.get('po_id')}.")
    return {"iteration": state.get("iteration", 0), "status": "running",
            "trace": [_ev("ingest", "Situation received",
                          summary + " (recommendation treated as UNVERIFIED)", sit)]}


# --------------------------------------------------------------------------- agent_reason
def agent_reason(state: AgentState) -> AgentState:
    phase = _phase(state)
    chat = get_chat()
    if chat.provider == "openai":
        try:
            return _agent_reason_llm(state, chat)
        except Exception as exc:
            out = _agent_reason_stub(state, phase)
            out["trace"] = [_ev("agent_reason", "LLM call failed — fell back to deterministic",
                                f"{type(exc).__name__}: {exc}. Used the deterministic planner.",
                                out["trace"][0]["data"])]
            return out
    return _agent_reason_stub(state, phase)


def _agent_reason_llm(state: AgentState, chat) -> AgentState:
    sit = state["situation"]
    messages = [
        {"role": "system", "content": AGENT_SYSTEM},
        {"role": "user", "content": build_agent_user(
            sit, state.get("scenario", "S1"), state.get("feedback"))},
    ]
    tool_calls_made: List[str] = []
    proposed: Optional[Dict] = None
    steps = 0

    with session_scope() as session:
        while steps < MAX_TOOL_STEPS:
            steps += 1
            msg = chat.call_tools(messages, TOOL_SPECS)
            if not msg["tool_calls"]:
                messages.append({"role": "assistant", "content": msg["content"]})
                messages.append({"role": "user",
                                 "content": "Call propose_decision with your final decision."})
                continue
            messages.append({
                "role": "assistant", "content": msg["content"],
                "tool_calls": [{"id": t["id"], "type": "function",
                                "function": {"name": t["name"],
                                             "arguments": json.dumps(t["arguments"])}}
                               for t in msg["tool_calls"]]})
            for tc in msg["tool_calls"]:
                if tc["name"] == "propose_decision":
                    proposed = tc["arguments"]
                    messages.append({"role": "tool", "tool_call_id": tc["id"],
                                     "content": "decision recorded"})
                else:
                    tool_calls_made.append(tc["name"])
                    result = dispatch(session, tc["name"], tc["arguments"])
                    messages.append({"role": "tool", "tool_call_id": tc["id"],
                                     "content": json.dumps(result, default=str)})
            if proposed is not None:
                break

    summary = (f"LLM investigated with {len(tool_calls_made)} tool call(s) and proposed: "
               f"{(proposed or {}).get('decision_type', 'no decision')}.")
    return {"proposed_decision": proposed,
            "trace": [_ev("agent_reason", "Agent reasoning (LLM tool-calling)", summary,
                          {"tool_calls": tool_calls_made, "llm_proposed": proposed})]}


def _agent_reason_stub(state: AgentState, phase: str) -> AgentState:
    with session_scope() as session:
        facts = _gather_facts(session, state["situation"])
    baseline = _baseline_decision(state, facts, phase)
    proposed = {"decision_type": baseline["type"], "qty": baseline["qty"],
                "vendor_id": baseline.get("vendor_id"),
                "rationale": " ".join(baseline.get("factors", []))}
    return {"proposed_decision": proposed,
            "trace": [_ev("agent_reason", "Agent reasoning (deterministic planner)",
                          f"Investigated {len(READ_TOOL_NAMES)} tools and proposed: {baseline['type']}.",
                          {"tool_calls": READ_TOOL_NAMES, "llm_proposed": proposed})]}


# --------------------------------------------------------------------------- baseline
def _baseline_decision(state: AgentState, facts: Dict, phase: str) -> Dict:
    sit = state["situation"]

    if phase == "verify_existing":
        po = facts["open_pos"]["orders"][0]
        return {"type": "confirm_existing", "qty": po["qty"], "vendor_id": po["vendor_id"],
                "po_id": po["po_id"], "confidence": "medium",
                "factors": [f"Existing PO {po['po_id']} for {po['qty']} units is open with "
                            f"{po['vendor_id']}. Verify the vendor can fulfill it."]}

    if phase == "cover_gap":
        gap = state["feedback"][-1]["gap"]
        alts = facts["alternate_vendors"]
        vendor = alts[0] if alts else None
        if vendor:
            cres = _constraint_result_for(facts, vendor, gap)
            reliable = vendor["reliability_score"] >= settings.min_supplier_reliability
            if reliable and cres.max_feasible_qty >= min(gap, vendor["min_order_qty"] or 1):
                qty = min(gap, cres.max_feasible_qty)
                return {"type": "source_alternate", "qty": qty, "vendor_id": vendor["vendor_id"],
                        "confidence": "medium",
                        "factors": [f"Shortfall of {gap} units. Alternate vendor {vendor['name']} "
                                    f"can supply {qty} (lead time {vendor['lead_time_days']}d, "
                                    f"reliability {vendor['reliability_score']:.2f}). Sourcing the gap."]}
        return {"type": "escalate", "qty": 0, "vendor_id": None, "confidence": "low",
                "factors": [f"Shortfall of {gap} units cannot be covered by an acceptable "
                            f"alternate vendor. Escalating to a human buyer."]}

    # review (S1)
    primary = facts["primary_vendor"]
    recommended = sit.get("recommended_qty", 0)
    cres = _constraint_result_for(facts, primary, recommended)
    dem = facts["demand"]
    decision = decide_purchase(
        net_requirement=_net_requirement(facts),
        recommended_qty=recommended,
        demand_available=dem.get("available", False),
        forecast_reliable=dem.get("forecast_reliable", False),
        constraints=cres,
        min_order_qty=primary["min_order_qty"] if primary else 0)
    decision["vendor_id"] = primary["vendor_id"] if primary else None
    return decision


# --------------------------------------------------------------------------- guardrail
def guardrail(state: AgentState) -> AgentState:
    phase = _phase(state)
    with session_scope() as session:
        facts = _gather_facts(session, state["situation"])

    baseline = _baseline_decision(state, facts, phase)
    proposed = state.get("proposed_decision") or {}

    same_type = proposed.get("decision_type") == baseline["type"]
    same_qty = int(proposed.get("qty", -1) or 0) == baseline["qty"]
    same_vendor = (baseline["type"] != "source_alternate"
                   or proposed.get("vendor_id") == baseline.get("vendor_id"))
    agreed = bool(proposed) and same_type and same_qty and same_vendor

    decision = dict(baseline)
    decision["overridden"] = not agreed and bool(proposed)
    decision["llm_proposed"] = proposed or None
    if agreed and proposed.get("rationale"):
        decision["rationale"] = proposed["rationale"]
    else:
        decision["rationale"] = " ".join(baseline.get("factors", []))
        if decision["overridden"]:
            decision["factors"] = list(baseline.get("factors", [])) + [
                f"Guardrail override: the model proposed {proposed.get('decision_type')} "
                f"(qty {proposed.get('qty')}), which conflicts with the verified "
                f"numbers/constraints; corrected to {baseline['type']} (qty {baseline['qty']})."]
            decision["rationale"] = " ".join(decision["factors"])

    vendor = (facts["alternate_vendors"] or [None])[0] if phase == "cover_gap" \
        else facts["primary_vendor"]
    cres = _constraint_result_for(facts, vendor, decision.get("qty", 0))
    net_req = _net_requirement(facts)
    analysis = {
        "phase": phase, "net_requirement": net_req,
        "forecast_reliable": facts["demand"].get("forecast_reliable", False),
        "demand_available": facts["demand"].get("available", False),
        "evaluated_vendor": vendor, "constraints": cres.to_dict(),
        "summary": {
            "net_requirement": net_req, "on_hand": facts["inventory"]["on_hand"],
            "incoming": facts["open_pos"]["incoming_open_pos"],
            "demand_over_horizon": facts["demand"].get("demand_over_horizon", 0),
            "budget_remaining": facts["budget"].get("remaining")}}

    order_value = decision.get("qty", 0) * (vendor["unit_price"] if vendor else 0)
    needs_human = False
    hitl_reasons: List[str] = []
    if decision["type"] in ("accept", "modify", "source_alternate", "confirm_existing"):
        if order_value > settings.approval_value_threshold:
            needs_human = True
            hitl_reasons.append(f"Order value {order_value:.0f} exceeds approval threshold "
                                f"{settings.approval_value_threshold:.0f}.")
        if vendor and vendor["reliability_score"] < settings.min_supplier_reliability:
            needs_human = True
            hitl_reasons.append(f"Vendor reliability {vendor['reliability_score']:.2f} below "
                                f"minimum {settings.min_supplier_reliability:.2f}.")
        if decision.get("confidence") == "low":
            needs_human = True
            hitl_reasons.append("Low decision confidence.")
    decision["order_value"] = order_value
    decision["hitl_reasons"] = hitl_reasons

    title = "Guardrail: validated" + (" & OVERRODE the model" if decision["overridden"]
                                      else " the decision")
    return {"facts": facts, "analysis": analysis, "decision": decision,
            "needs_human": needs_human,
            "approval": {"status": "pending"} if needs_human else {"status": "not_required"},
            "trace": [_ev("guardrail", title, decision["rationale"],
                          {"decision": decision, "analysis_summary": analysis["summary"],
                           "constraints": analysis["constraints"], "needs_human": needs_human,
                           "hitl_reasons": hitl_reasons, "overridden": decision["overridden"]})]}


# --------------------------------------------------------------------------- approval_gate
def approval_gate(state: AgentState) -> AgentState:
    if state.get("needs_human"):
        return {"status": "awaiting_approval",
                "trace": [_ev("approval_gate", "Human approval required",
                              "; ".join(state["decision"].get("hitl_reasons", [])),
                              {"hitl_reasons": state["decision"].get("hitl_reasons", [])})]}
    return {"status": "running",
            "trace": [_ev("approval_gate", "Auto-approved (low risk)",
                          "Action within autonomous policy limits; executing.")]}


# --------------------------------------------------------------------------- act
def act(state: AgentState) -> AgentState:
    decision = state["decision"]
    sit = state["situation"]

    approval = state.get("approval", {})
    if approval.get("status") == "approved" and approval.get("edited_qty") is not None:
        decision = {**decision, "qty": approval["edited_qty"]}

    with session_scope() as s:
        if decision["type"] == "confirm_existing":
            result = actions.simulate_vendor_response(s, decision["po_id"])
            result["expected_qty"] = decision["qty"]
            title = "Requested vendor confirmation"
            summary = (f"Ordered {result['ordered_qty']}, vendor confirmed "
                       f"{result['confirmed_qty']} (shortfall {result['shortfall']}).")
        else:
            vendor = queries.get_vendor_terms(s, sit["sku"], decision.get("vendor_id"))
            po = actions.create_vendor_po(
                s, sku=sit["sku"], vendor_id=decision["vendor_id"], qty=decision["qty"],
                unit_price=vendor["unit_price"], expected_delivery_days=vendor["lead_time_days"])
            result = po
            title = f"Created purchase order {po['po_id']}"
            summary = (f"PO {po['po_id']}: {po['qty']} units of {po['sku']} from "
                       f"{po['vendor_id']} @ {po['unit_price']} (value {po['order_value']:.0f}).")

    return {"status": "running", "action_result": result,
            "trace": [_ev("act", title, summary, {"action_result": result})]}


# --------------------------------------------------------------------------- validate
def validate(state: AgentState) -> AgentState:
    decision = state["decision"]
    result = state["action_result"]
    facts = state["facts"]

    checks: List[Dict] = []
    acceptable = True
    feedback_items: List[Dict] = []

    if decision["type"] == "confirm_existing":
        expected, confirmed = result["expected_qty"], result["confirmed_qty"]
        match = confirmed >= expected
        checks.append({"name": "vendor_fulfilled_order", "passed": match,
                       "detail": f"expected {expected}, confirmed {confirmed}"})
        if not match:
            inv, dem = facts["inventory"], facts["demand"]
            incoming_after = facts["open_pos"]["incoming_open_pos"] - (expected - confirmed)
            net_after = compute_net_requirement(
                dem.get("demand_over_horizon", 0), inv["safety_stock"], inv["on_hand"],
                incoming_after)
            if net_after <= 0:
                checks.append({"name": "inventory_covers_shortfall", "passed": True,
                               "detail": f"net requirement after shortfall = {net_after} <= 0"})
            else:
                acceptable = False
                checks.append({"name": "inventory_covers_shortfall", "passed": False,
                               "detail": f"uncovered gap of {net_after} units remains"})
                feedback_items.append({
                    "reason": "vendor_shortfall", "shortfall": result["shortfall"],
                    "gap": net_after,
                    "detail": f"Vendor confirmed only {confirmed}/{expected}; {net_after} units "
                              f"still uncovered after inventory."})
    else:
        with session_scope() as s:
            po = actions.get_purchase_order(s, result["po_id"])
            product = queries.get_product(s, po["sku"])
            budget = queries.get_budget(s, product["category"])
        qty_ok = po["qty"] == decision["qty"]
        budget_ok = budget["spent"] <= budget["allocated"] + 1e-6
        checks += [
            {"name": "po_persisted_with_expected_qty", "passed": qty_ok,
             "detail": f"persisted qty {po['qty']} vs intended {decision['qty']}"},
            {"name": "budget_not_exceeded", "passed": budget_ok,
             "detail": f"spent {budget['spent']:.0f} vs allocated {budget['allocated']:.0f}"}]
        acceptable = qty_ok and budget_ok
        if not acceptable:
            feedback_items.append({"reason": "post_action_constraint_violation",
                                   "detail": "Persisted PO violates a constraint; re-planning."})

    validation = {"acceptable": acceptable, "checks": checks}
    summary = ("Outcome validated: all checks passed." if acceptable
               else "Discrepancy detected: " + "; ".join(f["detail"] for f in feedback_items))
    out: AgentState = {"validation": validation,
                       "trace": [_ev("validate", "Validated outcome", summary,
                                     {"validation": validation})]}
    if feedback_items:
        out["feedback"] = feedback_items
    return out


# --------------------------------------------------------------------------- replan / escalate / finalize
def replan(state: AgentState) -> AgentState:
    fb = state["feedback"][-1]
    return {"iteration": state.get("iteration", 0) + 1, "status": "running",
            "trace": [_ev("replan", "Re-planning after feedback",
                          f"Feedback: {fb['detail']} Looping back to the agent.",
                          {"feedback": fb, "iteration": state.get("iteration", 0) + 1})]}


def escalate(state: AgentState) -> AgentState:
    reason = " ".join(state["decision"].get("factors", [])) if state.get("decision") else ""
    if state.get("feedback"):
        reason = state["feedback"][-1].get("detail", reason)
    return {"status": "escalated",
            "trace": [_ev("escalate", "Escalated to human buyer",
                          reason or "Situation requires human judgement.", {"reason": reason})]}


def finalize(state: AgentState) -> AgentState:
    status = "escalated" if state.get("status") == "escalated" else "done"
    dtype = state.get("decision", {}).get("type", "n/a")
    return {"status": status,
            "trace": [_ev("finalize", "Run complete",
                          f"Final decision: {dtype}; status: {status}.")]}
