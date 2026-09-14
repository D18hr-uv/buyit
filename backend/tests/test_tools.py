"""Integration tests for data tools against the seeded SQLite DB."""
from app.db.session import session_scope
from app.tools.constraints import compute_net_requirement
from app.tools.queries import (
    get_alternate_vendors,
    get_demand,
    get_inventory,
    get_open_purchase_orders,
    get_vendor_terms,
)


def _net(sku):
    with session_scope() as s:
        inv = get_inventory(s, sku)
        dem = get_demand(s, sku)
        pos = get_open_purchase_orders(s, sku)
        return compute_net_requirement(
            dem["demand_over_horizon"], inv["safety_stock"], inv["on_hand"],
            pos["incoming_open_pos"])


def test_net_requirements_match_designed_scenarios():
    assert _net("SKU-WATER") == 800     # -> accept (rec 800)
    assert _net("SKU-OIL") == 800       # -> modify (budget caps to 500)
    assert _net("SKU-BEANS") == -250    # -> reject
    assert _net("SKU-COFFEE") == 800    # -> accept but HITL (high value)


def test_demand_derived_from_client_orders():
    with session_scope() as s:
        dem = get_demand(s, "SKU-WATER")
    assert dem["available"] is True
    assert dem["demand_over_horizon"] == 900     # ~30/day * 30
    assert dem["forecast_reliable"] is True


def test_chocolate_demand_anomaly_flagged():
    with session_scope() as s:
        dem = get_demand(s, "SKU-CHOC")
    assert dem["forecast_reliable"] is False       # ~3x week-over-week spike -> investigate


def test_energy_primary_capacity_limited():
    with session_scope() as s:
        terms = get_vendor_terms(s, "SKU-ENERGY")
        alts = get_alternate_vendors(s, "SKU-ENERGY", exclude_vendor_id=terms["vendor_id"])
    assert terms["vendor_id"] == "SUP-POWER"
    assert terms["available_capacity"] == 250
    assert any(a["vendor_id"] == "SUP-VOLT" for a in alts)


def test_open_energy_po_exists():
    with session_scope() as s:
        pos = get_open_purchase_orders(s, "SKU-ENERGY")
    assert any(o["po_id"] == "PO-ENERGY-0500" and o["qty"] == 500 for o in pos["orders"])
