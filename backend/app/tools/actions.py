"""Write tools: create/modify vendor purchase orders, and the vendor-response simulator (S2).

Creating a PO commits category budget so that post-action validation re-reads real,
persisted state (not the agent's intent) and can detect over-commitment or shortfalls.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Budget, Inventory, Product, VendorProduct, VendorPurchaseOrder


def _new_po_id() -> str:
    return "PO-" + uuid.uuid4().hex[:8].upper()


def _status_for(confirmed_qty: int, qty: int) -> str:
    if confirmed_qty <= 0:
        return "open"
    return "confirmed" if confirmed_qty >= qty else "partial"


def receive_into_inventory(session: Session, po_id: str, new_confirmed_qty: int) -> dict:
    """Set a PO's confirmed qty, move the newly-confirmed delta into on-hand stock,
    and advance the PO status. Confirmed qty can only go up (you can't un-receive)."""
    po = session.get(VendorPurchaseOrder, po_id)
    if not po:
        raise ValueError(f"PO {po_id} not found")
    if new_confirmed_qty < po.confirmed_qty:
        raise ValueError("confirmed_qty cannot be reduced below what is already received")
    if new_confirmed_qty > po.qty:
        raise ValueError("confirmed_qty cannot exceed the ordered qty")

    delta = new_confirmed_qty - po.confirmed_qty
    po.confirmed_qty = new_confirmed_qty
    po.status = _status_for(new_confirmed_qty, po.qty)

    if delta:
        inv = session.get(Inventory, po.sku)
        if inv:
            inv.on_hand += delta
    session.flush()
    return _po_dict(po)


def create_vendor_po(session: Session, sku: str, vendor_id: str, qty: int,
                     unit_price: float, expected_delivery_days: int) -> dict:
    po = VendorPurchaseOrder(
        po_id=_new_po_id(), sku=sku, vendor_id=vendor_id, qty=qty, confirmed_qty=0,
        unit_price=unit_price, status="open", expected_delivery_days=expected_delivery_days)
    session.add(po)

    product = session.get(Product, sku)
    if product:
        budget = session.scalar(select(Budget).where(Budget.category == product.category))
        if budget:
            budget.spent += qty * unit_price

    session.flush()
    return _po_dict(po)


def modify_vendor_po(session: Session, po_id: str, new_qty: int) -> dict:
    po = session.get(VendorPurchaseOrder, po_id)
    if not po:
        raise ValueError(f"PO {po_id} not found")
    product = session.get(Product, po.sku)
    delta = new_qty - po.qty
    if product:
        budget = session.scalar(select(Budget).where(Budget.category == product.category))
        if budget:
            budget.spent += delta * po.unit_price
    po.qty = new_qty
    session.flush()
    return _po_dict(po)


def simulate_vendor_response(session: Session, po_id: str) -> dict:
    """Vendor responds to an open PO, confirming up to its currently available capacity.

    Drives Scenario 2: an order for 500 may only be confirmed for 250.
    """
    po = session.get(VendorPurchaseOrder, po_id)
    if not po:
        raise ValueError(f"PO {po_id} not found")
    vp = session.scalar(
        select(VendorProduct).where(
            VendorProduct.sku == po.sku, VendorProduct.vendor_id == po.vendor_id))
    capacity = vp.available_capacity if vp else po.qty
    confirmed = min(po.qty, capacity)
    po.confirmed_qty = confirmed
    po.status = "confirmed" if confirmed >= po.qty else "partial"
    session.flush()
    return {"po_id": po.po_id, "ordered_qty": po.qty, "confirmed_qty": confirmed,
            "shortfall": po.qty - confirmed, "status": po.status}


def get_purchase_order(session: Session, po_id: str) -> dict:
    po = session.get(VendorPurchaseOrder, po_id)
    if not po:
        raise ValueError(f"PO {po_id} not found")
    return _po_dict(po)


def _po_dict(po: VendorPurchaseOrder) -> dict:
    return {"po_id": po.po_id, "sku": po.sku, "vendor_id": po.vendor_id, "qty": po.qty,
            "confirmed_qty": po.confirmed_qty, "unit_price": po.unit_price, "status": po.status,
            "order_value": po.qty * po.unit_price,
            "expected_delivery_days": po.expected_delivery_days}
