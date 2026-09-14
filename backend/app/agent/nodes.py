"""LangGraph node implementations.

Design: nodes orchestrate and interpret; all arithmetic comes from deterministic tools
(app/tools) and the pure policy (app/agent/policy). The LLM only narrates. Every node
appends structured events to `trace` for observability + the UI timeline.
"""
from __future__ import annotations

from typing import Dict, List

from app.agent.policy import decide_purchase
from app.agent.prompts import NARRATE_SYSTEM, build_narration_user
from app.agent.state import AgentState
from app.config import get_settings
from app.db.session import session_scope
from app.llm.provider import get_chat
from app.rag import store as rag_store
from app.tools import actions, queries
from app.tools.constraints import compute_net_requirement, evaluate_constraints

settings = get_settings()


def _ev(node: str, title: str, summary: str, data: Dict | None = None) -> Dict:
    return {"node": node, "title": title, "summary": summary, "data": data or {}}


# --------------------------------------------------------------------------- #
def ingest(state: AgentState) -> AgentState:
    sit = state["situation"]
    scenario = state.get("scenario", "S1")
    summary = (
        f"Scenario {scenario}: review recommendation to buy "
        f"{sit.get('recommended_qty')} units of {sit.get('sku')} at {sit.get('node_id')}."
        if scenario == "S1"
        else f"Scenario {scenario}: supplier response for existing PO {sit.get('po_id')}."
    )
    return {
        "iteration": 0,
        "status": "running",
        "trace": [_ev("ingest", "Situation received",
                      summary + " (recommendation treated as UNVERIFIED)", sit)],
    }


# --------------------------------------------------------------------------- #
def gather_context(state: AgentState) -> AgentState:
    sit = state["situation"]
    node_id = sit["node_id"]
    with session_scope() as s:
        sku = sit["sku"]
        product = queries.get_product(s, sku)
        category = product["category"] if product else "unknown"
        facts = {
            "product": product,
            "inventory": queries.get_inventory(s, sku, node_id),
            "demand": queries.get_demand(s, sku, node_id),
            "open_pos": queries.get_open_purchase_orders(s, sku, node_id),
            "primary_supplier": queries.get_supplier_terms(s, sku),
            "budget": queries.get_budget(s, node_id, category),
            "storage": queries.get_storage(s, node_id),
        }
        primary_id = facts["primary_supplier"]["supplier_id"] if facts["primary_supplier"] else ""
        facts["alternate_suppliers"] = queries.get_alternate_suppliers(s, sku, primary_id)

    query = (f"purchasing {sku} {facts['product']['name'] if facts['product'] else ''} "
             f"budget storage supplier lead time forecast reliability shortfall")
    rules = rag_store.retrieve(query, k=4)

    tool_calls = ["get_product", "get_inventory", "get_demand", "get_open_purchase_orders",
                  "get_supplier_terms", "get_budget", "get_storage", "get_alternate_suppliers"]
    return {
        "facts": facts,
        "retrieved_rules": rules,
        "trace": [_ev("gather_context", "Gathered context",
                      f"Called {len(tool_calls)} data tools + retrieved {len(rules)} SOPs.",
                      {"tool_calls": tool_calls, "retrieved_rules": rules,
                       "inventory": facts["inventory"], "demand": facts["demand"],
                       "open_pos": facts["open_pos"], "budget": facts["budget"],
                       "storage": facts["storage"]})],
    }


# --------------------------------------------------------------------------- #
def _phase(state: AgentState) -> str:
    """S2 has two phases: verify the existing PO, then (after a shortfall) cover the gap."""
    if state.get("scenario") != "S2":
        return "review"
    return "cover_gap" if state.get("feedback") else "verify_existing"


def analyze(state: AgentState) -> AgentState:
    facts = state["facts"]
    sit = state["situation"]
    inv = facts["inventory"]
    dem = facts["demand"]
    phase = _phase(state)

    demand_over_horizon = dem.get("demand_over_horizon", 0) if dem.get("available") else 0

    # Incoming = expected receipts. In S2 verify phase we optimistically expect the full
    # existing PO; the shortfall is only discovered after we act.
    incoming = facts["open_pos"]["incoming_open_pos"]

    net_req = compute_net_requirement(
        demand_over_horizon, inv["safety_stock"], inv["on_hand"], incoming,
    )

    # Choose the supplier to evaluate against.
    if phase == "cover_gap":
        alts = facts["alternate_suppliers"]
        supplier = alts[0] if alts else facts["primary_supplier"]
        required = state["feedback"][-1].get("gap", max(net_req, 0))
    else:
        supplier = facts["primary_supplier"]
        required = sit.get("recommended_qty", net_req) if phase == "review" else facts[
            "open_pos"]["orders"][0]["qty"] if facts["open_pos"]["orders"] else net_req

    budget = facts["budget"]
    storage = facts["storage"]
    constraints = evaluate_constraints(
        qty=max(int(required), 0),
        unit_price=supplier["unit_price"] if supplier else 0.0,
        min_order_qty=supplier["min_order_qty"] if supplier else 0,
        budget_remaining=budget.get("remaining", 0.0),
        storage_remaining_units=storage.get("remaining_units", 0.0),
        unit_volume=facts["product"]["unit_volume"] if facts["product"] else 1.0,
        supplier_capacity=supplier["available_capacity"] if supplier else 0,
        supplier_reliability=supplier["reliability_score"] if supplier else 0.0,
        min_reliability=settings.min_supplier_reliability,
    )

    analysis = {
        "phase": phase,
        "net_requirement": net_req,
        "demand_over_horizon": demand_over_horizon,
        "incoming_open_pos": incoming,
        "forecast_reliable": dem.get("forecast_reliable", False),
        "demand_available": dem.get("available", False),
        "evaluated_supplier": supplier,
        "constraints": constraints.to_dict(),
        "summary": {
            "net_requirement": net_req,
            "on_hand": inv["on_hand"],
            "incoming": incoming,
            "demand_over_horizon": demand_over_horizon,
            "budget_remaining": budget.get("remaining"),
            "storage_remaining_units": storage.get("remaining_units"),
        },
    }
    return {
        "analysis": analysis,
        "trace": [_ev("analyze", "Analyzed situation",
                      f"net requirement = demand {demand_over_horizon} + safety "
                      f"{inv['safety_stock']} - on hand {inv['on_hand']} - incoming {incoming} "
                      f"= {net_req}. Constraints checked.",
                      {"analysis_summary": analysis["summary"],
                       "constraints": analysis["constraints"], "phase": phase})],
    }


# --------------------------------------------------------------------------- #
def decide(state: AgentState) -> AgentState:
    from app.tools.constraints import ConstraintResult, ConstraintCheck

    a = state["analysis"]
    sit = state["situation"]
    phase = a["phase"]
    supplier = a["evaluated_supplier"]

    # Rebuild a ConstraintResult from the dict for the policy call.
    cdict = a["constraints"]
    cres = ConstraintResult(
        all_passed=cdict["all_passed"],
        max_feasible_qty=cdict["max_feasible_qty"],
        checks=[ConstraintCheck(**c) for c in cdict["checks"]],
        violations=cdict["violations"],
    )

    if phase == "verify_existing":
        # First S2 action: rely on the existing PO, expecting full fulfillment.
        po = state["facts"]["open_pos"]["orders"][0]
        decision = {
            "type": "confirm_existing", "qty": po["qty"], "supplier_id": po["supplier_id"],
            "po_id": po["po_id"], "confidence": "medium",
            "factors": [f"Existing PO {po['po_id']} for {po['qty']} units is open with "
                        f"{po['supplier_id']}. Verifying the supplier can fulfill it."],
        }
    elif phase == "cover_gap":
        gap = state["feedback"][-1]["gap"]
        if supplier and cres.max_feasible_qty >= min(gap, supplier["min_order_qty"] or 1) and \
                supplier["reliability_score"] >= settings.min_supplier_reliability:
            qty = min(gap, cres.max_feasible_qty)
            decision = {
                "type": "source_alternate", "qty": qty, "supplier_id": supplier["supplier_id"],
                "confidence": "medium",
                "factors": [f"Shortfall of {gap} units. Alternate supplier "
                            f"{supplier['name']} can supply {qty} (lead time "
                            f"{supplier['lead_time_days']}d, reliability "
                            f"{supplier['reliability_score']:.2f}). Sourcing the gap."],
            }
        else:
            decision = {
                "type": "escalate", "qty": 0, "supplier_id": None, "confidence": "low",
                "factors": [f"Shortfall of {gap} units cannot be covered by an acceptable "
                            f"alternate supplier. Escalating to a human buyer."],
            }
    else:  # S1 review
        decision = decide_purchase(
            net_requirement=a["net_requirement"],
            recommended_qty=sit.get("recommended_qty", 0),
            demand_available=a["demand_available"],
            forecast_reliable=a["forecast_reliable"],
            constraints=cres,
            min_order_qty=supplier["min_order_qty"] if supplier else 0,
        )
        decision["supplier_id"] = supplier["supplier_id"] if supplier else None

    # Guardrail: does this need human approval?
    order_value = decision["qty"] * (supplier["unit_price"] if supplier else 0)
    needs_human = False
    hitl_reasons: List[str] = []
    if decision["type"] in ("accept", "modify", "source_alternate", "confirm_existing"):
        if order_value > settings.approval_value_threshold:
            needs_human = True
            hitl_reasons.append(
                f"Order value {order_value:.0f} exceeds approval threshold "
                f"{settings.approval_value_threshold:.0f}.")
        if supplier and supplier["reliability_score"] < settings.min_supplier_reliability:
            needs_human = True
            hitl_reasons.append(
                f"Supplier reliability {supplier['reliability_score']:.2f} below minimum "
                f"{settings.min_supplier_reliability:.2f}.")
        if decision["confidence"] == "low":
            needs_human = True
            hitl_reasons.append("Low decision confidence.")

    decision["order_value"] = order_value
    decision["hitl_reasons"] = hitl_reasons

    # Narration (LLM optional; deterministic fallback = joined factors).
    rationale = " ".join(decision["factors"])
    chat = get_chat()
    if chat.provider == "openai":
        try:
            rationale = chat.complete(
                NARRATE_SYSTEM, build_narration_user(decision, a, state.get("retrieved_rules", [])))
        except Exception:
            pass
    decision["rationale"] = rationale

    return {
        "decision": decision,
        "needs_human": needs_human,
        "approval": {"status": "pending"} if needs_human else {"status": "not_required"},
        "trace": [_ev("decide", f"Decision: {decision['type'].upper()}",
                      rationale,
                      {"decision": decision, "needs_human": needs_human,
                       "hitl_reasons": hitl_reasons})],
    }


# --------------------------------------------------------------------------- #
def approval_gate(state: AgentState) -> AgentState:
    """Marks whether we're proceeding autonomously or waiting for a human.

    Actual pausing is done by the compiled graph's `interrupt_before=['act']`; the API
    inspects `needs_human` to decide whether to auto-resume or wait for the buyer.
    """
    if state.get("needs_human"):
        return {
            "status": "awaiting_approval",
            "trace": [_ev("approval_gate", "Human approval required",
                          "; ".join(state["decision"].get("hitl_reasons", [])),
                          {"hitl_reasons": state["decision"].get("hitl_reasons", [])})],
        }
    return {
        "status": "running",
        "trace": [_ev("approval_gate", "Auto-approved (low risk)",
                      "Action within autonomous policy limits; executing.")],
    }


# --------------------------------------------------------------------------- #
def act(state: AgentState) -> AgentState:
    decision = state["decision"]
    sit = state["situation"]
    facts = state["facts"]

    # Respect a human edit to the quantity, if provided on approval.
    approval = state.get("approval", {})
    if approval.get("status") == "approved" and approval.get("edited_qty") is not None:
        decision = {**decision, "qty": approval["edited_qty"]}

    with session_scope() as s:
        if decision["type"] == "confirm_existing":
            # The action here is to confirm the supplier response for the existing PO.
            result = actions.simulate_supplier_response(s, decision["po_id"])
            result["expected_qty"] = decision["qty"]
            title = "Requested supplier confirmation"
            summary = (f"Ordered {result['ordered_qty']}, supplier confirmed "
                       f"{result['confirmed_qty']} (shortfall {result['shortfall']}).")
        else:
            supplier = queries.get_supplier_terms(s, sit["sku"], decision.get("supplier_id"))
            po = actions.create_purchase_order(
                s, sku=sit["sku"], supplier_id=decision["supplier_id"],
                node_id=sit["node_id"], qty=decision["qty"],
                unit_price=supplier["unit_price"], expected_delivery_days=supplier["lead_time_days"],
            )
            result = po
            title = f"Created purchase order {po['po_id']}"
            summary = (f"PO {po['po_id']}: {po['qty']} units of {po['sku']} from "
                       f"{po['supplier_id']} @ {po['unit_price']} (value {po['order_value']:.0f}).")

    return {
        "status": "running",
        "action_result": result,
        "trace": [_ev("act", title, summary, {"action_result": result})],
    }


# --------------------------------------------------------------------------- #
def validate(state: AgentState) -> AgentState:
    """Re-read persisted state and check the outcome is acceptable. Detects the S2 shortfall."""
    decision = state["decision"]
    result = state["action_result"]
    facts = state["facts"]
    sit = state["situation"]

    checks: List[Dict] = []
    acceptable = True
    feedback_items: List[Dict] = []

    if decision["type"] == "confirm_existing":
        # Expected vs actual fulfillment.
        expected = result["expected_qty"]
        confirmed = result["confirmed_qty"]
        match = confirmed >= expected
        checks.append({"name": "supplier_fulfilled_order", "passed": match,
                       "detail": f"expected {expected}, confirmed {confirmed}"})
        if not match:
            # Recompute coverage with the CONFIRMED qty to see if inventory saves us.
            inv = facts["inventory"]
            dem = facts["demand"]
            incoming_after = facts["open_pos"]["incoming_open_pos"] - (expected - confirmed)
            net_after = compute_net_requirement(
                dem.get("demand_over_horizon", 0), inv["safety_stock"], inv["on_hand"],
                incoming_after)
            if net_after <= 0:
                checks.append({"name": "inventory_covers_shortfall", "passed": True,
                               "detail": f"net requirement after shortfall = {net_after} <= 0"})
            else:
                acceptable = False
                gap = net_after
                checks.append({"name": "inventory_covers_shortfall", "passed": False,
                               "detail": f"uncovered gap of {gap} units remains"})
                feedback_items.append({
                    "reason": "supplier_shortfall",
                    "shortfall": result["shortfall"],
                    "gap": gap,
                    "detail": f"Supplier confirmed only {confirmed}/{expected}; "
                              f"{gap} units still uncovered after inventory.",
                })
    else:
        # Re-read the created PO and re-validate against persisted budget/storage.
        with session_scope() as s:
            po = actions.get_purchase_order(s, result["po_id"])
            product = queries.get_product(s, po["sku"])
            budget = queries.get_budget(s, po["node_id"], product["category"])
            storage = queries.get_storage(s, po["node_id"])
        qty_ok = po["qty"] == decision["qty"]
        budget_ok = budget["spent"] <= budget["allocated"] + 1e-6
        storage_ok = storage["used"] <= storage["total"] + 1e-6
        checks += [
            {"name": "po_persisted_with_expected_qty", "passed": qty_ok,
             "detail": f"persisted qty {po['qty']} vs intended {decision['qty']}"},
            {"name": "budget_not_exceeded", "passed": budget_ok,
             "detail": f"spent {budget['spent']:.0f} vs allocated {budget['allocated']:.0f}"},
            {"name": "storage_not_exceeded", "passed": storage_ok,
             "detail": f"used {storage['used']:.0f} vs total {storage['total']:.0f}"},
        ]
        acceptable = qty_ok and budget_ok and storage_ok
        if not acceptable:
            feedback_items.append({
                "reason": "post_action_constraint_violation",
                "detail": "Persisted PO violates a constraint; re-planning.",
            })

    validation = {"acceptable": acceptable, "checks": checks}
    summary = ("Outcome validated: all checks passed." if acceptable
               else "Discrepancy detected: " + "; ".join(f["detail"] for f in feedback_items))
    out: AgentState = {
        "validation": validation,
        "trace": [_ev("validate", "Validated outcome", summary,
                      {"validation": validation})],
    }
    if feedback_items:
        out["feedback"] = feedback_items
    return out


# --------------------------------------------------------------------------- #
def replan(state: AgentState) -> AgentState:
    fb = state["feedback"][-1]
    return {
        "iteration": state.get("iteration", 0) + 1,
        "status": "running",
        "trace": [_ev("replan", "Re-planning after feedback",
                      f"Feedback: {fb['detail']} Looping back to analyze.",
                      {"feedback": fb, "iteration": state.get("iteration", 0) + 1})],
    }


# --------------------------------------------------------------------------- #
def escalate(state: AgentState) -> AgentState:
    reason = " ".join(state["decision"].get("factors", [])) if state.get("decision") else ""
    if state.get("feedback"):
        reason = state["feedback"][-1].get("detail", reason)
    return {
        "status": "escalated",
        "trace": [_ev("escalate", "Escalated to human buyer",
                      reason or "Situation requires human judgement.",
                      {"reason": reason})],
    }


# --------------------------------------------------------------------------- #
def finalize(state: AgentState) -> AgentState:
    status = "escalated" if state.get("status") == "escalated" else "done"
    dtype = state.get("decision", {}).get("type", "n/a")
    return {
        "status": status,
        "trace": [_ev("finalize", "Run complete",
                      f"Final decision: {dtype}; status: {status}.")],
    }
