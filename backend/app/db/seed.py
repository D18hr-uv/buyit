"""Seed the inventory database with data engineered to exercise every decision branch
(accept / modify / reject / investigate) plus the Scenario-2 vendor shortfall.

Demand is driven by the client-order stream: orders in the last 7 days set the sales rate
(projected over a 30-day horizon), and a >50% jump vs the previous 7 days flags an anomaly.

Run: `python -m app.db.seed`
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import (
    Budget,
    ClientOrder,
    Inventory,
    Product,
    Vendor,
    VendorProduct,
    VendorPurchaseOrder,
)
from app.db.session import Base, engine, session_scope

NOW = datetime.now(timezone.utc)


def reset_schema() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _orders(sku: str, last7: int, prev7: int) -> list[ClientOrder]:
    """Two orders in the last 7 days and two in the prior 7 days, summing to the targets."""
    out = []
    for i, (days_ago, qty) in enumerate([
        (2, last7 // 2), (5, last7 - last7 // 2),
        (9, prev7 // 2), (12, prev7 - prev7 // 2),
    ]):
        out.append(ClientOrder(order_id=f"CO-{sku}-{i}", sku=sku, qty=qty, status="fulfilled",
                               created_at=NOW - timedelta(days=days_ago)))
    return out


def seed() -> None:
    reset_schema()
    with session_scope() as s:
        # ---------------- Products ----------------
        s.add_all([
            Product(sku="SKU-WATER", name="Bottled Water 1L", category="beverages", unit_cost=0.8),
            Product(sku="SKU-OIL", name="Cooking Oil 1L", category="oils", unit_cost=2.5),
            Product(sku="SKU-BEANS", name="Canned Beans 400g", category="canned", unit_cost=0.6),
            Product(sku="SKU-CHOC", name="Seasonal Chocolate Bar", category="confectionery", unit_cost=1.5),
            Product(sku="SKU-ENERGY", name="Energy Drink 250ml", category="beverages", unit_cost=1.2),
            Product(sku="SKU-COFFEE", name="Premium Coffee Beans 1kg", category="coffee", unit_cost=60.0),
        ])
        s.flush()  # persist products before inserting rows that reference them (FK order)

        # ---------------- Inventory ----------------
        s.add_all([
            Inventory(sku="SKU-WATER", on_hand=150, safety_stock=100, reorder_point=200),
            Inventory(sku="SKU-OIL", on_hand=100, safety_stock=150, reorder_point=250),
            Inventory(sku="SKU-BEANS", on_hand=400, safety_stock=50, reorder_point=100),
            Inventory(sku="SKU-CHOC", on_hand=200, safety_stock=100, reorder_point=300),
            Inventory(sku="SKU-ENERGY", on_hand=100, safety_stock=150, reorder_point=250),
            Inventory(sku="SKU-COFFEE", on_hand=100, safety_stock=150, reorder_point=250),
        ])

        # ---------------- Client orders (the demand signal) ----------------
        # WATER  ~30/day  -> demand 900, net = 900+100-150-50   = 800  -> ACCEPT (rec 800)
        # OIL    ~25/day  -> demand 750, net = 750+150-100-0     = 800, budget caps 500 -> MODIFY
        # BEANS  ~10/day  -> demand 300, net = 300+50-400-200    = -250 -> REJECT
        # CHOC   spike 20->60/day (+200%) -> anomaly -> INVESTIGATE
        # ENERGY ~15/day  -> demand 450, net w/ full 500 PO = 0; confirmed 250 -> gap 250 (S2)
        # COFFEE ~25/day  -> demand 750, net = 800, value 800*65=52000 > threshold -> HITL
        s.add_all(
            _orders("SKU-WATER", last7=210, prev7=210)
            + _orders("SKU-OIL", last7=175, prev7=175)
            + _orders("SKU-BEANS", last7=70, prev7=70)
            + _orders("SKU-CHOC", last7=420, prev7=140)     # +200% spike
            + _orders("SKU-ENERGY", last7=105, prev7=105)
            + _orders("SKU-COFFEE", last7=175, prev7=175)
        )

        # ---------------- Vendors ----------------
        s.add_all([
            Vendor(vendor_id="SUP-AQUA", name="AquaCorp", reliability_score=0.95),
            Vendor(vendor_id="SUP-OLEO", name="OleoLatam", reliability_score=0.90),
            Vendor(vendor_id="SUP-CONS", name="ConservasSA", reliability_score=0.90),
            Vendor(vendor_id="SUP-DULCE", name="DulceMax", reliability_score=0.85),
            Vendor(vendor_id="SUP-POWER", name="PowerDrinks", reliability_score=0.80),
            Vendor(vendor_id="SUP-VOLT", name="VoltBeverages", reliability_score=0.88),
            Vendor(vendor_id="SUP-ANDES", name="AndesRoasters", reliability_score=0.92),
        ])
        s.flush()  # persist vendors before vendor_products / POs (FK order)
        s.add_all([
            VendorProduct(vendor_id="SUP-AQUA", sku="SKU-WATER", lead_time_days=5, min_order_qty=100,
                          unit_price=0.9, available_capacity=100000, is_primary=True),
            VendorProduct(vendor_id="SUP-OLEO", sku="SKU-OIL", lead_time_days=7, min_order_qty=100,
                          unit_price=3.0, available_capacity=100000, is_primary=True),
            VendorProduct(vendor_id="SUP-CONS", sku="SKU-BEANS", lead_time_days=10, min_order_qty=100,
                          unit_price=0.7, available_capacity=100000, is_primary=True),
            VendorProduct(vendor_id="SUP-DULCE", sku="SKU-CHOC", lead_time_days=14, min_order_qty=200,
                          unit_price=1.7, available_capacity=100000, is_primary=True),
            # Energy primary can currently only supply 250 (drives the S2 shortfall)
            VendorProduct(vendor_id="SUP-POWER", sku="SKU-ENERGY", lead_time_days=6, min_order_qty=100,
                          unit_price=1.4, available_capacity=250, is_primary=True),
            # Energy alternate: plenty of capacity, slightly pricier + longer lead
            VendorProduct(vendor_id="SUP-VOLT", sku="SKU-ENERGY", lead_time_days=9, min_order_qty=100,
                          unit_price=1.55, available_capacity=100000, is_primary=False),
            VendorProduct(vendor_id="SUP-ANDES", sku="SKU-COFFEE", lead_time_days=12, min_order_qty=100,
                          unit_price=65.0, available_capacity=100000, is_primary=True),
        ])

        # ---------------- Vendor purchase orders (incoming supply) ----------------
        s.add_all([
            VendorPurchaseOrder(po_id="PO-WATER-0001", sku="SKU-WATER", vendor_id="SUP-AQUA",
                                qty=50, confirmed_qty=50, unit_price=0.9, status="confirmed",
                                expected_delivery_days=5),
            VendorPurchaseOrder(po_id="PO-BEANS-0001", sku="SKU-BEANS", vendor_id="SUP-CONS",
                                qty=200, confirmed_qty=200, unit_price=0.7, status="confirmed",
                                expected_delivery_days=10),
            # Scenario 2: existing open PO for 500 energy drinks, not yet confirmed
            VendorPurchaseOrder(po_id="PO-ENERGY-0500", sku="SKU-ENERGY", vendor_id="SUP-POWER",
                                qty=500, confirmed_qty=0, unit_price=1.4, status="open",
                                expected_delivery_days=6),
        ])

        # ---------------- Budgets (per category) ----------------
        s.add_all([
            Budget(category="beverages", allocated=1_000_000, spent=0),
            Budget(category="oils", allocated=1_600, spent=100),   # remaining 1500 -> caps oil to 500
            Budget(category="canned", allocated=500_000, spent=0),
            Budget(category="confectionery", allocated=500_000, spent=0),
            Budget(category="coffee", allocated=1_000_000, spent=0),
        ])

    print(f"Seeded inventory database ({engine.dialect.name}).")


if __name__ == "__main__":
    seed()
