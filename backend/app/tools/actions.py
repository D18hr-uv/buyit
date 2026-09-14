"""Write tools: create/modify purchase orders, and the supplier-response simulator (S2).

Creating a PO commits budget + storage so that post-action validation re-reads real,
persisted state (not the agent's intent) and can detect over-commitment or shortfalls.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Budget, Product, PurchaseOrder, Storage, SupplierSku


def _new_po_id() -> str:
    return "PO-" + uuid.uuid4().hex[:8].upper()


def create_purchase_order(
    session: Session,
    sku: str,
    supplier_id: str,
    node_id: str,
    qty: int,
    unit_price: float,
    expected_delivery_days: int,
) -> dict:
    po = PurchaseOrder(
        po_id=_new_po_id(),
        sku=sku,
        supplier_id=supplier_id,
        node_id=node_id,
        qty=qty,
        confirmed_qty=0,
        unit_price=unit_price,
        status="open",
        expected_delivery_days=expected_delivery_days,
    )
    session.add(po)

    # Commit budget + storage
    product = session.get(Product, sku)
    if product:
        budget = session.scalar(
            select(Budget).where(Budget.node_id == node_id, Budget.category == product.category)
        )
        if budget:
            budget.spent += qty * unit_price
        storage = session.get(Storage, node_id)
        if storage:
            storage.used_units += qty * product.unit_volume

    session.flush()
    return _po_dict(po)


def modify_purchase_order(session: Session, po_id: str, new_qty: int) -> dict:
    po = session.get(PurchaseOrder, po_id)
    if not po:
        raise ValueError(f"PO {po_id} not found")
    product = session.get(Product, po.sku)
    delta = new_qty - po.qty
    if product:
        budget = session.scalar(
            select(Budget).where(Budget.node_id == po.node_id, Budget.category == product.category)
        )
        if budget:
            budget.spent += delta * po.unit_price
        storage = session.get(Storage, po.node_id)
        if storage:
            storage.used_units += delta * product.unit_volume
    po.qty = new_qty
    session.flush()
    return _po_dict(po)


def simulate_supplier_response(session: Session, po_id: str) -> dict:
    """Supplier responds to an open PO, confirming up to its currently available capacity.

    This is the driver for Scenario 2: an order for 500 may only be confirmed for 250.
    """
    po = session.get(PurchaseOrder, po_id)
    if not po:
        raise ValueError(f"PO {po_id} not found")
    ss = session.scalar(
        select(SupplierSku).where(
            SupplierSku.sku == po.sku, SupplierSku.supplier_id == po.supplier_id
        )
    )
    capacity = ss.available_capacity if ss else po.qty
    confirmed = min(po.qty, capacity)
    po.confirmed_qty = confirmed
    po.status = "confirmed" if confirmed >= po.qty else "partial"
    session.flush()
    return {
        "po_id": po.po_id, "ordered_qty": po.qty, "confirmed_qty": confirmed,
        "shortfall": po.qty - confirmed, "status": po.status,
    }


def get_purchase_order(session: Session, po_id: str) -> dict:
    po = session.get(PurchaseOrder, po_id)
    if not po:
        raise ValueError(f"PO {po_id} not found")
    return _po_dict(po)


def _po_dict(po: PurchaseOrder) -> dict:
    return {
        "po_id": po.po_id, "sku": po.sku, "supplier_id": po.supplier_id,
        "node_id": po.node_id, "qty": po.qty, "confirmed_qty": po.confirmed_qty,
        "unit_price": po.unit_price, "status": po.status,
        "order_value": po.qty * po.unit_price,
        "expected_delivery_days": po.expected_delivery_days,
    }
