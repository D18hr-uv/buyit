"""Read-only data tools the agent uses to gather context from the operational DB."""
from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Budget,
    DemandForecast,
    Inventory,
    Product,
    PurchaseOrder,
    Storage,
    Supplier,
    SupplierSku,
)

FORECAST_DEVIATION_THRESHOLD = 0.5  # >50% deviation => forecast considered unreliable


def get_product(session: Session, sku: str) -> Optional[dict]:
    p = session.get(Product, sku)
    if not p:
        return None
    return {
        "sku": p.sku, "name": p.name, "category": p.category,
        "unit_cost": p.unit_cost, "unit_volume": p.unit_volume,
        "is_perishable": p.is_perishable, "shelf_life_days": p.shelf_life_days,
    }


def get_inventory(session: Session, sku: str, node_id: str) -> dict:
    inv = session.scalar(
        select(Inventory).where(Inventory.sku == sku, Inventory.node_id == node_id)
    )
    if not inv:
        return {"sku": sku, "node_id": node_id, "on_hand": 0, "reserved": 0, "safety_stock": 0,
                "available": 0}
    return {
        "sku": sku, "node_id": node_id, "on_hand": inv.on_hand,
        "reserved": inv.reserved, "safety_stock": inv.safety_stock,
        "available": inv.on_hand - inv.reserved,
    }


def get_demand(session: Session, sku: str, node_id: str) -> dict:
    fc = session.scalar(
        select(DemandForecast).where(DemandForecast.sku == sku, DemandForecast.node_id == node_id)
    )
    if not fc:
        return {"available": False}
    actuals = json.loads(fc.recent_daily_actuals or "[]")
    demand_over_horizon = fc.daily_forecast * fc.horizon_days
    deviation = None
    reliable = True
    if actuals:
        avg_actual = sum(actuals) / len(actuals)
        if fc.daily_forecast > 0:
            deviation = (avg_actual - fc.daily_forecast) / fc.daily_forecast
            reliable = abs(deviation) <= FORECAST_DEVIATION_THRESHOLD
    return {
        "available": True,
        "daily_forecast": fc.daily_forecast,
        "horizon_days": fc.horizon_days,
        "demand_over_horizon": demand_over_horizon,
        "recent_daily_actuals": actuals,
        "avg_recent_actual": (sum(actuals) / len(actuals)) if actuals else None,
        "deviation": deviation,
        "forecast_reliable": reliable,
    }


def get_open_purchase_orders(session: Session, sku: str, node_id: str) -> dict:
    pos = session.scalars(
        select(PurchaseOrder).where(
            PurchaseOrder.sku == sku,
            PurchaseOrder.node_id == node_id,
            PurchaseOrder.status.in_(["open", "partial", "confirmed"]),
        )
    ).all()
    orders = []
    incoming = 0
    for po in pos:
        # incoming = what we still expect to receive
        expected = po.confirmed_qty if po.status in ("confirmed", "partial") else po.qty
        incoming += expected
        orders.append({
            "po_id": po.po_id, "qty": po.qty, "confirmed_qty": po.confirmed_qty,
            "status": po.status, "supplier_id": po.supplier_id,
            "expected_delivery_days": po.expected_delivery_days,
        })
    return {"incoming_open_pos": incoming, "orders": orders}


def _supplier_row(session: Session, ss: SupplierSku) -> dict:
    sup = session.get(Supplier, ss.supplier_id)
    return {
        "supplier_id": ss.supplier_id,
        "name": sup.name if sup else ss.supplier_id,
        "reliability_score": sup.reliability_score if sup else 0.0,
        "lead_time_days": ss.lead_time_days,
        "min_order_qty": ss.min_order_qty,
        "unit_price": ss.unit_price,
        "available_capacity": ss.available_capacity,
        "is_primary": ss.is_primary,
    }


def get_supplier_terms(session: Session, sku: str, supplier_id: Optional[str] = None) -> Optional[dict]:
    """Terms for a specific supplier, or the primary supplier if none given."""
    stmt = select(SupplierSku).where(SupplierSku.sku == sku)
    if supplier_id:
        stmt = stmt.where(SupplierSku.supplier_id == supplier_id)
    else:
        stmt = stmt.order_by(SupplierSku.is_primary.desc())
    ss = session.scalars(stmt).first()
    return _supplier_row(session, ss) if ss else None


def get_alternate_suppliers(session: Session, sku: str, exclude_supplier_id: str) -> List[dict]:
    rows = session.scalars(
        select(SupplierSku).where(
            SupplierSku.sku == sku, SupplierSku.supplier_id != exclude_supplier_id
        )
    ).all()
    alts = [_supplier_row(session, r) for r in rows]
    # Prefer higher capacity then shorter lead time then lower price
    alts.sort(key=lambda a: (-a["available_capacity"], a["lead_time_days"], a["unit_price"]))
    return alts


def get_budget(session: Session, node_id: str, category: str) -> dict:
    b = session.scalar(
        select(Budget).where(Budget.node_id == node_id, Budget.category == category)
    )
    if not b:
        return {"available": False, "remaining": 0.0, "allocated": 0.0, "spent": 0.0}
    return {
        "available": True, "category": category, "period": b.period,
        "allocated": b.allocated, "spent": b.spent, "remaining": b.allocated - b.spent,
    }


def get_storage(session: Session, node_id: str) -> dict:
    s = session.get(Storage, node_id)
    if not s:
        return {"available": False, "remaining_units": 0.0, "total": 0.0, "used": 0.0}
    return {
        "available": True, "total": s.total_capacity_units, "used": s.used_units,
        "remaining_units": s.total_capacity_units - s.used_units,
    }
