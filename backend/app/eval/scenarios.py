"""Test scenarios with expected outcomes, used by the evaluation harness.

`required_tools` = data tools the agent MUST have called to make a defensible decision.
`expected` encodes what a correct agent should conclude and do.
"""

REQUIRED_TOOLS = [
    "get_inventory", "get_demand", "get_open_purchase_orders",
    "get_supplier_terms", "get_budget", "get_storage",
]

EVAL_SCENARIOS = [
    {
        "id": "s1-accept",
        "scenario": "S1",
        "situation": {"sku": "SKU-WATER", "node_id": "MFC-BOG", "recommended_qty": 800},
        "required_tools": REQUIRED_TOOLS,
        "expected": {"decision": "accept", "qty": 800, "needs_human": False,
                     "action": True, "validated": True},
    },
    {
        "id": "s1-modify",
        "scenario": "S1",
        "situation": {"sku": "SKU-OIL", "node_id": "MFC-BOG", "recommended_qty": 800},
        "required_tools": REQUIRED_TOOLS,
        "expected": {"decision": "modify", "qty": 500, "needs_human": False,
                     "action": True, "validated": True},
    },
    {
        "id": "s1-reject",
        "scenario": "S1",
        "situation": {"sku": "SKU-BEANS", "node_id": "MFC-BOG", "recommended_qty": 800},
        "required_tools": REQUIRED_TOOLS,
        "expected": {"decision": "reject", "needs_human": False, "action": False},
    },
    {
        "id": "s1-investigate",
        "scenario": "S1",
        "situation": {"sku": "SKU-CHOC", "node_id": "MFC-BOG", "recommended_qty": 800},
        "required_tools": REQUIRED_TOOLS,
        "expected": {"decision": "investigate", "action": False},
    },
    {
        "id": "s1-hitl",
        "scenario": "S1",
        "situation": {"sku": "SKU-COFFEE", "node_id": "MFC-BOG", "recommended_qty": 800},
        "required_tools": REQUIRED_TOOLS,
        "auto_approve": True,
        "expected": {"decision": "accept", "qty": 800, "needs_human": True,
                     "action": True, "validated": True},
    },
    {
        "id": "s2-shortfall",
        "scenario": "S2",
        "situation": {"sku": "SKU-ENERGY", "node_id": "MFC-BOG", "po_id": "PO-ENERGY-0500"},
        "required_tools": REQUIRED_TOOLS + ["get_alternate_suppliers"],
        "expected": {"decision": "source_alternate", "qty": 250, "needs_human": False,
                     "action": True, "validated": True, "recovered": True},
    },
]
