"""Read-only data tools the agent uses to gather context from the inventory DB."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Budget,
    ClientOrder,
    Inventory,
    Product,
    Vendor,
    VendorProduct,
    VendorPurchaseOrder,
)

HORIZON_DAYS = 30
DEVIATION_THRESHOLD = 0.5  # >50% week-over-week change => demand anomaly => investigate


def get_product(session: Session, sku: str) -> Optional[dict]:
    p = session.get(Product, sku)
    if not p:
        return None
    return {"sku": p.sku, "name": p.name, "category": p.category, "unit_cost": p.unit_cost}


def get_inventory(session: Session, sku: str) -> dict:
    inv = session.get(Inventory, sku)
    if not inv:
        return {"sku": sku, "on_hand": 0, "reserved": 0, "safety_stock": 0, "reorder_point": 0,
                "available": 0}
    return {"sku": sku, "on_hand": inv.on_hand, "reserved": inv.reserved,
            "safety_stock": inv.safety_stock, "reorder_point": inv.reorder_point,
            "available": inv.on_hand - inv.reserved}


def get_demand(session: Session, sku: str) -> dict:
    """Derive the demand signal from the client-order stream.

    Uses the last 7 days as the current sales rate, projects it over the planning horizon,
    and flags an anomaly if the rate deviates >50% from the previous 7 days.
    """
    now = datetime.now(timezone.utc)
    orders = session.scalars(
        select(ClientOrder).where(ClientOrder.sku == sku)
    ).all()
    if not orders:
        return {"available": False}

    def _window_sum(days_from: int, days_to: int) -> int:
        lo, hi = now - timedelta(days=days_to), now - timedelta(days=days_from)
        return sum(o.qty for o in orders if lo <= _aware(o.created_at) < hi)

    last7 = _window_sum(0, 7)
    prev7 = _window_sum(7, 14)
    daily_rate = last7 / 7.0
    demand_over_horizon = round(daily_rate * HORIZON_DAYS)

    deviation = None
    reliable = True
    if prev7 > 0:
        deviation = (last7 - prev7) / prev7
        reliable = abs(deviation) <= DEVIATION_THRESHOLD

    return {
        "available": True,
        "last_7d_units": last7,
        "prev_7d_units": prev7,
        "daily_rate": round(daily_rate, 2),
        "horizon_days": HORIZON_DAYS,
        "demand_over_horizon": demand_over_horizon,
        "deviation": deviation,
        "forecast_reliable": reliable,
    }


def get_open_purchase_orders(session: Session, sku: str) -> dict:
    pos = session.scalars(
        select(VendorPurchaseOrder).where(
            VendorPurchaseOrder.sku == sku,
            VendorPurchaseOrder.status.in_(["open", "partial", "confirmed"]),
        )
    ).all()
    orders, incoming = [], 0
    for po in pos:
        expected = po.confirmed_qty if po.status in ("confirmed", "partial") else po.qty
        incoming += expected
        orders.append({"po_id": po.po_id, "qty": po.qty, "confirmed_qty": po.confirmed_qty,
                       "status": po.status, "vendor_id": po.vendor_id,
                       "expected_delivery_days": po.expected_delivery_days})
    return {"incoming_open_pos": incoming, "orders": orders}


def _vendor_row(session: Session, vp: VendorProduct) -> dict:
    v = session.get(Vendor, vp.vendor_id)
    return {"vendor_id": vp.vendor_id, "name": v.name if v else vp.vendor_id,
            "reliability_score": v.reliability_score if v else 0.0,
            "lead_time_days": vp.lead_time_days, "min_order_qty": vp.min_order_qty,
            "unit_price": vp.unit_price, "available_capacity": vp.available_capacity,
            "is_primary": vp.is_primary}


def get_vendor_terms(session: Session, sku: str, vendor_id: Optional[str] = None) -> Optional[dict]:
    stmt = select(VendorProduct).where(VendorProduct.sku == sku)
    if vendor_id:
        stmt = stmt.where(VendorProduct.vendor_id == vendor_id)
    else:
        stmt = stmt.order_by(VendorProduct.is_primary.desc())
    vp = session.scalars(stmt).first()
    return _vendor_row(session, vp) if vp else None


def get_alternate_vendors(session: Session, sku: str, exclude_vendor_id: str) -> List[dict]:
    rows = session.scalars(
        select(VendorProduct).where(
            VendorProduct.sku == sku, VendorProduct.vendor_id != exclude_vendor_id)
    ).all()
    alts = [_vendor_row(session, r) for r in rows]
    alts.sort(key=lambda a: (-a["available_capacity"], a["lead_time_days"], a["unit_price"]))
    return alts


def get_budget(session: Session, category: str) -> dict:
    b = session.scalar(select(Budget).where(Budget.category == category))
    if not b:
        return {"available": False, "remaining": 0.0, "allocated": 0.0, "spent": 0.0}
    return {"available": True, "category": category, "period": b.period,
            "allocated": b.allocated, "spent": b.spent, "remaining": b.allocated - b.spent}


def _aware(dt: datetime) -> datetime:
    """Normalize naive timestamps (SQLite) to UTC-aware for comparison."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
