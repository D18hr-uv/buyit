"""OpenAI function-calling tool definitions + dispatcher.

Tools the LLM can call to investigate and to obtain authoritative numbers. All arithmetic is
computed here in deterministic Python (via app/tools), so even though the LLM decides which
tools to call and what to conclude, it can never fabricate a number. `propose_decision` is
the terminal tool the LLM calls to commit to a decision.
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.config import get_settings
from app.tools import queries
from app.tools.constraints import compute_net_requirement, evaluate_constraints

settings = get_settings()

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "get_inventory",
        "description": "On-hand, reserved, safety stock, and reorder point for a SKU.",
        "parameters": {"type": "object", "properties": {"sku": {"type": "string"}},
                       "required": ["sku"]}}},
    {"type": "function", "function": {
        "name": "get_demand",
        "description": "Demand signal for a SKU derived from the client-order stream: recent "
                       "sales rate, projected demand over the horizon, and whether the rate is "
                       "stable (a >50% week-over-week change flags an anomaly).",
        "parameters": {"type": "object", "properties": {"sku": {"type": "string"}},
                       "required": ["sku"]}}},
    {"type": "function", "function": {
        "name": "get_open_purchase_orders",
        "description": "Open/partial/confirmed vendor POs for a SKU and total incoming quantity.",
        "parameters": {"type": "object", "properties": {"sku": {"type": "string"}},
                       "required": ["sku"]}}},
    {"type": "function", "function": {
        "name": "get_vendor_terms",
        "description": "Terms for a SKU's vendor (primary if vendor_id omitted): lead time, "
                       "min order qty, unit price, available capacity, reliability.",
        "parameters": {"type": "object",
                       "properties": {"sku": {"type": "string"}, "vendor_id": {"type": "string"}},
                       "required": ["sku"]}}},
    {"type": "function", "function": {
        "name": "get_alternate_vendors",
        "description": "Alternate vendors for a SKU (excluding one), ranked by capacity, lead "
                       "time, then price.",
        "parameters": {"type": "object",
                       "properties": {"sku": {"type": "string"},
                                      "exclude_vendor_id": {"type": "string"}},
                       "required": ["sku", "exclude_vendor_id"]}}},
    {"type": "function", "function": {
        "name": "get_budget",
        "description": "Remaining budget for a product category.",
        "parameters": {"type": "object", "properties": {"category": {"type": "string"}},
                       "required": ["category"]}}},
    {"type": "function", "function": {
        "name": "assess_purchase",
        "description": "AUTHORITATIVE numbers for a candidate purchase: computes the net "
                       "requirement and checks every constraint (budget, vendor capacity, MOQ, "
                       "reliability) for a candidate quantity. ALWAYS call this before proposing "
                       "a decision so your numbers are exact.",
        "parameters": {"type": "object", "properties": {
            "sku": {"type": "string"},
            "candidate_qty": {"type": "integer"},
            "vendor_id": {"type": "string", "description": "Vendor to evaluate (default primary)."},
        }, "required": ["sku", "candidate_qty"]}}},
    {"type": "function", "function": {
        "name": "propose_decision",
        "description": "Commit to your final decision. Scenario 1: accept/modify/reject/"
                       "investigate. Vendor shortfall: confirm_existing, source_alternate, or "
                       "escalate.",
        "parameters": {"type": "object", "properties": {
            "decision_type": {"type": "string",
                              "enum": ["accept", "modify", "reject", "investigate",
                                       "confirm_existing", "source_alternate", "escalate"]},
            "qty": {"type": "integer"},
            "vendor_id": {"type": "string"},
            "rationale": {"type": "string"},
        }, "required": ["decision_type", "qty", "rationale"]}}},
]

READ_TOOL_NAMES = ["get_inventory", "get_demand", "get_open_purchase_orders",
                   "get_vendor_terms", "get_alternate_vendors", "get_budget", "assess_purchase"]


def assess_purchase(session: Session, sku: str, candidate_qty: int,
                    vendor_id: str | None = None) -> Dict[str, Any]:
    product = queries.get_product(session, sku)
    inv = queries.get_inventory(session, sku)
    dem = queries.get_demand(session, sku)
    pos = queries.get_open_purchase_orders(session, sku)
    vendor = queries.get_vendor_terms(session, sku, vendor_id)
    category = product["category"] if product else "unknown"
    budget = queries.get_budget(session, category)

    demand_over_horizon = dem.get("demand_over_horizon", 0) if dem.get("available") else 0
    net_req = compute_net_requirement(
        demand_over_horizon, inv["safety_stock"], inv["on_hand"], pos["incoming_open_pos"])

    constraints = evaluate_constraints(
        qty=max(int(candidate_qty), 0),
        unit_price=vendor["unit_price"] if vendor else 0.0,
        min_order_qty=vendor["min_order_qty"] if vendor else 0,
        budget_remaining=budget.get("remaining", 0.0),
        vendor_capacity=vendor["available_capacity"] if vendor else 0,
        vendor_reliability=vendor["reliability_score"] if vendor else 0.0,
        min_reliability=settings.min_supplier_reliability,
    )
    return {
        "net_requirement": net_req, "demand_over_horizon": demand_over_horizon,
        "on_hand": inv["on_hand"], "safety_stock": inv["safety_stock"],
        "incoming_open_pos": pos["incoming_open_pos"],
        "forecast_reliable": dem.get("forecast_reliable", False),
        "demand_available": dem.get("available", False),
        "order_value": max(int(candidate_qty), 0) * (vendor["unit_price"] if vendor else 0.0),
        "evaluated_vendor": vendor, "constraints": constraints.to_dict(),
    }


def dispatch(session: Session, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "get_inventory":
        return queries.get_inventory(session, args["sku"])
    if name == "get_demand":
        return queries.get_demand(session, args["sku"])
    if name == "get_open_purchase_orders":
        return queries.get_open_purchase_orders(session, args["sku"])
    if name == "get_vendor_terms":
        return queries.get_vendor_terms(session, args["sku"], args.get("vendor_id")) or {}
    if name == "get_alternate_vendors":
        return {"alternates": queries.get_alternate_vendors(
            session, args["sku"], args["exclude_vendor_id"])}
    if name == "get_budget":
        return queries.get_budget(session, args["category"])
    if name == "assess_purchase":
        return assess_purchase(session, args["sku"], args["candidate_qty"], args.get("vendor_id"))
    return {"error": f"unknown tool {name}"}
