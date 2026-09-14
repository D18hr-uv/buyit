"""Integration tests for data tools against the seeded SQLite DB."""
from app.db.session import session_scope
from app.tools.constraints import compute_net_requirement
from app.tools.queries import (
    get_alternate_suppliers,
    get_demand,
    get_inventory,
    get_open_purchase_orders,
    get_supplier_terms,
)

NODE = "MFC-BOG"


def _net(sku):
    with session_scope() as s:
        inv = get_inventory(s, sku, NODE)
        dem = get_demand(s, sku, NODE)
        pos = get_open_purchase_orders(s, sku, NODE)
        return compute_net_requirement(
            dem["demand_over_horizon"], inv["safety_stock"], inv["on_hand"],
            pos["incoming_open_pos"],
        )


def test_net_requirements_match_designed_scenarios():
    assert _net("SKU-WATER") == 800     # -> accept (rec 800)
    assert _net("SKU-OIL") == 800       # -> modify (budget caps to 500)
    assert _net("SKU-BEANS") == -250    # -> reject
    assert _net("SKU-COFFEE") == 800    # -> accept but HITL (high value)


def test_chocolate_forecast_flagged_unreliable():
    with session_scope() as s:
        dem = get_demand(s, "SKU-CHOC", NODE)
    assert dem["forecast_reliable"] is False  # ~3x spike -> investigate


def test_energy_primary_capacity_limited():
    with session_scope() as s:
        terms = get_supplier_terms(s, "SKU-ENERGY")
        alts = get_alternate_suppliers(s, "SKU-ENERGY", exclude_supplier_id=terms["supplier_id"])
    assert terms["supplier_id"] == "SUP-POWER"
    assert terms["available_capacity"] == 250     # can only supply 250 of 500
    assert any(a["supplier_id"] == "SUP-VOLT" for a in alts)


def test_open_energy_po_exists():
    with session_scope() as s:
        pos = get_open_purchase_orders(s, "SKU-ENERGY", NODE)
    assert any(o["po_id"] == "PO-ENERGY-0500" and o["qty"] == 500 for o in pos["orders"])
