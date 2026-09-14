"""Seed the mock supply-chain database with data engineered to exercise every decision
branch (accept / modify / reject / investigate) plus the Scenario-2 supplier shortfall.

Run: `python -m app.db.seed`
"""
from __future__ import annotations

import json

from app.db.models import (
    Budget,
    DemandForecast,
    FulfillmentNode,
    Inventory,
    Product,
    PurchaseOrder,
    Storage,
    Supplier,
    SupplierSku,
)
from app.db.session import Base, engine, session_scope
from app.rag.seed_rules import BUSINESS_RULES
from app.rag.store import init_and_seed

NODE = "MFC-BOG"


def reset_schema() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed() -> None:
    reset_schema()
    with session_scope() as s:
        s.add(FulfillmentNode(node_id=NODE, name="Bogotá Micro-Fulfillment Center", region="LATAM"))

        # ---------------- Products ----------------
        products = [
            Product(sku="SKU-WATER", name="Bottled Water 1L", category="beverages",
                    unit_cost=0.8, unit_volume=1.0, is_perishable=False, shelf_life_days=365),
            Product(sku="SKU-OIL", name="Cooking Oil 1L", category="oils",
                    unit_cost=2.5, unit_volume=2.0, is_perishable=False, shelf_life_days=365),
            Product(sku="SKU-BEANS", name="Canned Beans 400g", category="canned",
                    unit_cost=0.6, unit_volume=0.5, is_perishable=False, shelf_life_days=730),
            Product(sku="SKU-CHOC", name="Seasonal Chocolate Bar", category="confectionery",
                    unit_cost=1.5, unit_volume=0.3, is_perishable=True, shelf_life_days=120),
            Product(sku="SKU-ENERGY", name="Energy Drink 250ml", category="beverages",
                    unit_cost=1.2, unit_volume=0.4, is_perishable=False, shelf_life_days=300),
            Product(sku="SKU-COFFEE", name="Premium Coffee Beans 1kg", category="coffee",
                    unit_cost=60.0, unit_volume=1.5, is_perishable=False, shelf_life_days=365),
        ]
        s.add_all(products)

        # ---------------- Inventory ----------------
        inv = [
            Inventory(sku="SKU-WATER", node_id=NODE, on_hand=150, reserved=0, safety_stock=100),
            Inventory(sku="SKU-OIL", node_id=NODE, on_hand=100, reserved=0, safety_stock=150),
            Inventory(sku="SKU-BEANS", node_id=NODE, on_hand=400, reserved=0, safety_stock=50),
            Inventory(sku="SKU-CHOC", node_id=NODE, on_hand=200, reserved=0, safety_stock=100),
            Inventory(sku="SKU-ENERGY", node_id=NODE, on_hand=100, reserved=0, safety_stock=150),
            Inventory(sku="SKU-COFFEE", node_id=NODE, on_hand=100, reserved=0, safety_stock=150),
        ]
        s.add_all(inv)

        # ---------------- Demand forecasts ----------------
        # WATER: net = 900 + 100 - 150 - 50(incoming) = 800  -> ACCEPT (rec 800)
        # OIL:   net = 750 + 150 - 100 - 0   = 800, budget caps to 500 -> MODIFY
        # BEANS: net = 300 +  50 - 400 - 200 = -250 -> REJECT
        # CHOC:  forecast unreliable (spike ~3x) -> INVESTIGATE
        # ENERGY(S2 base): net = 1200 + 200 - 300 - 500 = 600
        # COFFEE: net = 750 + 150 - 100 - 0 = 800, value 800*65=52000 > threshold -> HITL
        demand = [
            DemandForecast(sku="SKU-WATER", node_id=NODE, daily_forecast=30, horizon_days=30,
                           recent_daily_actuals=json.dumps([29, 31, 30, 28, 32])),
            DemandForecast(sku="SKU-OIL", node_id=NODE, daily_forecast=25, horizon_days=30,
                           recent_daily_actuals=json.dumps([24, 26, 25, 25, 24])),
            DemandForecast(sku="SKU-BEANS", node_id=NODE, daily_forecast=10, horizon_days=30,
                           recent_daily_actuals=json.dumps([9, 11, 10, 10, 10])),
            DemandForecast(sku="SKU-CHOC", node_id=NODE, daily_forecast=20, horizon_days=30,
                           recent_daily_actuals=json.dumps([58, 62, 60, 65, 61])),
            # With full 500 incoming: net = 450 + 150 - 100 - 500 = 0 (covered).
            # After supplier confirms only 250: gap = 450 + 150 - 100 - 250 = 250.
            DemandForecast(sku="SKU-ENERGY", node_id=NODE, daily_forecast=15, horizon_days=30,
                           recent_daily_actuals=json.dumps([14, 15, 16, 15, 15])),
            DemandForecast(sku="SKU-COFFEE", node_id=NODE, daily_forecast=25, horizon_days=30,
                           recent_daily_actuals=json.dumps([24, 25, 26, 25, 25])),
        ]
        s.add_all(demand)

        # ---------------- Suppliers ----------------
        suppliers = [
            Supplier(supplier_id="SUP-AQUA", name="AquaCorp", reliability_score=0.95),
            Supplier(supplier_id="SUP-OLEO", name="OleoLatam", reliability_score=0.90),
            Supplier(supplier_id="SUP-CONS", name="ConservasSA", reliability_score=0.90),
            Supplier(supplier_id="SUP-DULCE", name="DulceMax", reliability_score=0.85),
            Supplier(supplier_id="SUP-POWER", name="PowerDrinks", reliability_score=0.80),
            Supplier(supplier_id="SUP-VOLT", name="VoltBeverages", reliability_score=0.88),
            Supplier(supplier_id="SUP-ANDES", name="AndesRoasters", reliability_score=0.92),
        ]
        s.add_all(suppliers)

        supplier_skus = [
            SupplierSku(supplier_id="SUP-AQUA", sku="SKU-WATER", lead_time_days=5, min_order_qty=100,
                        unit_price=0.9, available_capacity=100000, is_primary=True),
            SupplierSku(supplier_id="SUP-OLEO", sku="SKU-OIL", lead_time_days=7, min_order_qty=100,
                        unit_price=3.0, available_capacity=100000, is_primary=True),
            SupplierSku(supplier_id="SUP-CONS", sku="SKU-BEANS", lead_time_days=10, min_order_qty=100,
                        unit_price=0.7, available_capacity=100000, is_primary=True),
            SupplierSku(supplier_id="SUP-DULCE", sku="SKU-CHOC", lead_time_days=14, min_order_qty=200,
                        unit_price=1.7, available_capacity=100000, is_primary=True),
            # Energy: primary can currently only supply 250 units (drives S2 shortfall)
            SupplierSku(supplier_id="SUP-POWER", sku="SKU-ENERGY", lead_time_days=6, min_order_qty=100,
                        unit_price=1.4, available_capacity=250, is_primary=True),
            # Energy alternate: plenty of capacity, slightly pricier + longer lead
            SupplierSku(supplier_id="SUP-VOLT", sku="SKU-ENERGY", lead_time_days=9, min_order_qty=100,
                        unit_price=1.55, available_capacity=100000, is_primary=False),
            SupplierSku(supplier_id="SUP-ANDES", sku="SKU-COFFEE", lead_time_days=12, min_order_qty=100,
                        unit_price=65.0, available_capacity=100000, is_primary=True),
        ]
        s.add_all(supplier_skus)

        # ---------------- Open purchase orders (incoming supply) ----------------
        open_pos = [
            PurchaseOrder(po_id="PO-WATER-0001", sku="SKU-WATER", supplier_id="SUP-AQUA",
                          node_id=NODE, qty=50, confirmed_qty=50, unit_price=0.9,
                          status="confirmed", expected_delivery_days=5),
            PurchaseOrder(po_id="PO-BEANS-0001", sku="SKU-BEANS", supplier_id="SUP-CONS",
                          node_id=NODE, qty=200, confirmed_qty=200, unit_price=0.7,
                          status="confirmed", expected_delivery_days=10),
            # Scenario 2: existing open PO for 500 energy drinks, not yet confirmed
            PurchaseOrder(po_id="PO-ENERGY-0500", sku="SKU-ENERGY", supplier_id="SUP-POWER",
                          node_id=NODE, qty=500, confirmed_qty=0, unit_price=1.4,
                          status="open", expected_delivery_days=6),
        ]
        s.add_all(open_pos)

        # ---------------- Budgets (per node + category) ----------------
        budgets = [
            Budget(node_id=NODE, category="beverages", allocated=1_000_000, spent=0),
            # Oils budget is tight: remaining 1500 / price 3.0 -> max 500 units -> forces MODIFY
            Budget(node_id=NODE, category="oils", allocated=1_600, spent=100),
            Budget(node_id=NODE, category="canned", allocated=500_000, spent=0),
            Budget(node_id=NODE, category="confectionery", allocated=500_000, spent=0),
            Budget(node_id=NODE, category="coffee", allocated=1_000_000, spent=0),
        ]
        s.add_all(budgets)

        # ---------------- Storage (ample; not the binding constraint here) ----------------
        s.add(Storage(node_id=NODE, total_capacity_units=1_000_000, used_units=200_000))

    # ---------------- RAG business rules / SOPs ----------------
    init_and_seed(BUSINESS_RULES)
    print(f"Seeded database ({engine.dialect.name}) and {len(BUSINESS_RULES)} business rules.")


if __name__ == "__main__":
    seed()
