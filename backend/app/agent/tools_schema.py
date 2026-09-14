"""OpenAI function-calling tool definitions + dispatcher.

These are the tools the LLM can call to investigate and to obtain authoritative numbers.
All arithmetic is computed here in deterministic Python (via app/tools), so even though the
LLM decides *which* tools to call and *what* to conclude, it can never fabricate a number.
`propose_decision` is the terminal tool the LLM calls to commit to a decision.
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.config import get_settings
from app.tools import queries
from app.tools.constraints import compute_net_requirement, evaluate_constraints

settings = get_settings()

# ---- Tool specs exposed to the model (OpenAI function-calling format) ---------------- #
TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "On-hand, reserved, and safety-stock levels for a SKU at a node.",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"}, "node_id": {"type": "string"}},
                "required": ["sku", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_demand",
            "description": "Demand forecast for a SKU at a node, including whether recent actual "
                           "sales make the forecast reliable (deviation > 50% => unreliable).",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"}, "node_id": {"type": "string"}},
                "required": ["sku", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_open_purchase_orders",
            "description": "Open/partial/confirmed POs for a SKU at a node and total incoming qty.",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"}, "node_id": {"type": "string"}},
                "required": ["sku", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_supplier_terms",
            "description": "Terms for a SKU's supplier (primary if supplier_id omitted): lead time, "
                           "min order qty, unit price, available capacity, reliability.",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"},
                               "supplier_id": {"type": "string"}},
                "required": ["sku"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alternate_suppliers",
            "description": "Alternate suppliers for a SKU (excluding one supplier), ranked by "
                           "capacity, lead time, then price.",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"},
                               "exclude_supplier_id": {"type": "string"}},
                "required": ["sku", "exclude_supplier_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget",
            "description": "Remaining category budget at a node.",
            "parameters": {
                "type": "object",
                "properties": {"node_id": {"type": "string"}, "category": {"type": "string"}},
                "required": ["node_id", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_storage",
            "description": "Remaining storage capacity (in storage units) at a node.",
            "parameters": {
                "type": "object",
                "properties": {"node_id": {"type": "string"}},
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assess_purchase",
            "description": "AUTHORITATIVE numbers for a candidate purchase. Computes the net "
                           "requirement and checks every constraint (budget, storage, supplier "
                           "capacity, MOQ, reliability) for a candidate quantity. ALWAYS call "
                           "this before proposing a decision so your numbers are exact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string"},
                    "node_id": {"type": "string"},
                    "candidate_qty": {"type": "integer",
                                      "description": "Quantity you are considering ordering."},
                    "supplier_id": {"type": "string",
                                    "description": "Supplier to evaluate against (default primary)."},
                },
                "required": ["sku", "node_id", "candidate_qty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_decision",
            "description": "Commit to your final decision. For Scenario 1 use accept/modify/reject/"
                           "investigate. For a supplier shortfall use confirm_existing (to verify an "
                           "existing PO), source_alternate (to cover a gap from an alternate "
                           "supplier), or escalate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_type": {
                        "type": "string",
                        "enum": ["accept", "modify", "reject", "investigate",
                                 "confirm_existing", "source_alternate", "escalate"],
                    },
                    "qty": {"type": "integer", "description": "Quantity to order (0 if none)."},
                    "supplier_id": {"type": "string"},
                    "rationale": {"type": "string",
                                  "description": "Concise, buyer-facing explanation citing the "
                                                 "key numbers and any binding constraints."},
                },
                "required": ["decision_type", "qty", "rationale"],
            },
        },
    },
]

READ_TOOL_NAMES = [
    "get_inventory", "get_demand", "get_open_purchase_orders", "get_supplier_terms",
    "get_alternate_suppliers", "get_budget", "get_storage", "assess_purchase",
]


def assess_purchase(session: Session, sku: str, node_id: str, candidate_qty: int,
                    supplier_id: str | None = None) -> Dict[str, Any]:
    """Deterministic assessment: net requirement + constraint checks for a candidate qty."""
    product = queries.get_product(session, sku)
    inv = queries.get_inventory(session, sku, node_id)
    dem = queries.get_demand(session, sku, node_id)
    pos = queries.get_open_purchase_orders(session, sku, node_id)
    supplier = queries.get_supplier_terms(session, sku, supplier_id)
    category = product["category"] if product else "unknown"
    budget = queries.get_budget(session, node_id, category)
    storage = queries.get_storage(session, node_id)

    demand_over_horizon = dem.get("demand_over_horizon", 0) if dem.get("available") else 0
    net_req = compute_net_requirement(
        demand_over_horizon, inv["safety_stock"], inv["on_hand"], pos["incoming_open_pos"])

    constraints = evaluate_constraints(
        qty=max(int(candidate_qty), 0),
        unit_price=supplier["unit_price"] if supplier else 0.0,
        min_order_qty=supplier["min_order_qty"] if supplier else 0,
        budget_remaining=budget.get("remaining", 0.0),
        storage_remaining_units=storage.get("remaining_units", 0.0),
        unit_volume=product["unit_volume"] if product else 1.0,
        supplier_capacity=supplier["available_capacity"] if supplier else 0,
        supplier_reliability=supplier["reliability_score"] if supplier else 0.0,
        min_reliability=settings.min_supplier_reliability,
    )
    return {
        "net_requirement": net_req,
        "demand_over_horizon": demand_over_horizon,
        "on_hand": inv["on_hand"],
        "safety_stock": inv["safety_stock"],
        "incoming_open_pos": pos["incoming_open_pos"],
        "forecast_reliable": dem.get("forecast_reliable", False),
        "demand_available": dem.get("available", False),
        "order_value": max(int(candidate_qty), 0) * (supplier["unit_price"] if supplier else 0.0),
        "evaluated_supplier": supplier,
        "constraints": constraints.to_dict(),
    }


def dispatch(session: Session, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call by name and return a JSON-serializable result."""
    if name == "get_inventory":
        return queries.get_inventory(session, args["sku"], args["node_id"])
    if name == "get_demand":
        return queries.get_demand(session, args["sku"], args["node_id"])
    if name == "get_open_purchase_orders":
        return queries.get_open_purchase_orders(session, args["sku"], args["node_id"])
    if name == "get_supplier_terms":
        return queries.get_supplier_terms(session, args["sku"], args.get("supplier_id")) or {}
    if name == "get_alternate_suppliers":
        return {"alternates": queries.get_alternate_suppliers(
            session, args["sku"], args["exclude_supplier_id"])}
    if name == "get_budget":
        return queries.get_budget(session, args["node_id"], args["category"])
    if name == "get_storage":
        return queries.get_storage(session, args["node_id"])
    if name == "assess_purchase":
        return assess_purchase(session, args["sku"], args["node_id"],
                               args["candidate_qty"], args.get("supplier_id"))
    return {"error": f"unknown tool {name}"}
