"""FastAPI routes for the inventory-management purchasing agent."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.agent import runner
from app.config import get_settings
from app.db.models import (
    Budget,
    ClientOrder,
    Inventory,
    Product,
    ReorderLog,
    Vendor,
    VendorProduct,
    VendorPurchaseOrder,
)
from app.db.session import session_scope
from app.eval.runner import run_eval
from app.presets import PRESETS
from app.tools.actions import close_po, create_vendor_po, receive_into_inventory

router = APIRouter()
settings = get_settings()


class RunRequest(BaseModel):
    scenario: str
    situation: Dict[str, Any]


class ApprovalRequest(BaseModel):
    approved: bool
    edited_qty: Optional[int] = None


class CreatePORequest(BaseModel):
    sku: str
    vendor_id: str
    qty: int
    unit_price: Optional[float] = None
    expected_delivery_days: Optional[int] = None
    confirmed_qty: int = 0


class ReceivePORequest(BaseModel):
    confirmed_qty: int


class CreateOrderRequest(BaseModel):
    sku: str
    qty: int
    status: str = "open"


class CreateProductRequest(BaseModel):
    sku: str
    name: str
    category: str
    unit_cost: float
    on_hand: int = 0
    safety_stock: int = 0
    reorder_point: int = 0


@router.get("/health")
def health():
    from app.llm.provider import llm_available
    return {"status": "ok", "llm": "openai" if llm_available() else "stub"}


@router.get("/scenarios")
def scenarios():
    return {"presets": PRESETS}


@router.post("/runs")
def create_run(req: RunRequest):
    if req.scenario not in ("S1", "S2"):
        raise HTTPException(400, "scenario must be 'S1' or 'S2'")
    return runner.start_run(req.scenario, req.situation)


@router.get("/runs/{run_id}")
def read_run(run_id: str):
    run = runner.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@router.post("/runs/{run_id}/approve")
def approve(run_id: str, req: ApprovalRequest):
    return runner.approve_run(run_id, approved=req.approved, edited_qty=req.edited_qty)


@router.get("/inventory")
def inventory():
    with session_scope() as s:
        rows = s.execute(
            select(Product, Inventory).join(Inventory, Product.sku == Inventory.sku)
        ).all()
        return {"inventory": [
            {"sku": p.sku, "name": p.name, "category": p.category, "unit_cost": p.unit_cost,
             "on_hand": inv.on_hand, "reserved": inv.reserved, "safety_stock": inv.safety_stock,
             "reorder_point": inv.reorder_point}
            for p, inv in rows]}


@router.post("/inventory")
def create_inventory_item(req: CreateProductRequest):
    sku = req.sku.strip()
    if not sku:
        raise HTTPException(400, "sku is required")
    if req.unit_cost < 0:
        raise HTTPException(400, "unit_cost must be non-negative")
    with session_scope() as s:
        if s.get(Product, sku):
            raise HTTPException(409, f"SKU {sku} already exists")
        s.add(Product(sku=sku, name=req.name, category=req.category, unit_cost=req.unit_cost))
        s.add(Inventory(sku=sku, on_hand=req.on_hand, reserved=0,
                        safety_stock=req.safety_stock, reorder_point=req.reorder_point))
        s.flush()
        return {"item": {
            "sku": sku, "name": req.name, "category": req.category, "unit_cost": req.unit_cost,
            "on_hand": req.on_hand, "reserved": 0, "safety_stock": req.safety_stock,
            "reorder_point": req.reorder_point}}


@router.get("/vendors")
def vendors():
    with session_scope() as s:
        return {"vendors": [
            {"vendor_id": v.vendor_id, "name": v.name, "reliability_score": v.reliability_score}
            for v in s.scalars(select(Vendor)).all()]}


@router.get("/purchase-orders")
def purchase_orders():
    with session_scope() as s:
        pos = s.scalars(
            select(VendorPurchaseOrder).order_by(VendorPurchaseOrder.created_at.desc())).all()
        return {"purchase_orders": [
            {"po_id": p.po_id, "sku": p.sku, "vendor_id": p.vendor_id, "qty": p.qty,
             "confirmed_qty": p.confirmed_qty, "unit_price": p.unit_price, "status": p.status,
             "order_value": p.qty * p.unit_price} for p in pos]}


@router.post("/purchase-orders")
def create_purchase_order(req: CreatePORequest):
    if req.qty <= 0:
        raise HTTPException(400, "qty must be positive")
    if not 0 <= req.confirmed_qty <= req.qty:
        raise HTTPException(400, "confirmed_qty must be between 0 and qty")
    with session_scope() as s:
        if not s.get(Product, req.sku):
            raise HTTPException(404, f"unknown SKU {req.sku}")
        if not s.get(Vendor, req.vendor_id):
            raise HTTPException(404, f"unknown vendor {req.vendor_id}")

        vp = s.scalar(
            select(VendorProduct).where(
                VendorProduct.sku == req.sku, VendorProduct.vendor_id == req.vendor_id))
        unit_price = req.unit_price
        if unit_price is None:
            product = s.get(Product, req.sku)
            unit_price = vp.unit_price if vp else product.unit_cost
        delivery = req.expected_delivery_days
        if delivery is None:
            delivery = vp.lead_time_days if vp else 7

        po = create_vendor_po(s, sku=req.sku, vendor_id=req.vendor_id, qty=req.qty,
                              unit_price=unit_price, expected_delivery_days=delivery)
        if req.confirmed_qty > 0:
            po = receive_into_inventory(s, po["po_id"], req.confirmed_qty)
        return {"purchase_order": po}


@router.post("/purchase-orders/{po_id}/receive")
def receive_purchase_order(po_id: str, req: ReceivePORequest):
    with session_scope() as s:
        try:
            po = receive_into_inventory(s, po_id, req.confirmed_qty)
        except ValueError as e:
            msg = str(e)
            raise HTTPException(404 if "not found" in msg else 400, msg)
        return {"purchase_order": po}


@router.post("/purchase-orders/{po_id}/close")
def close_purchase_order(po_id: str):
    with session_scope() as s:
        try:
            po = close_po(s, po_id)
        except ValueError as e:
            raise HTTPException(404, str(e))
        return {"purchase_order": po}


@router.get("/client-orders")
def client_orders():
    with session_scope() as s:
        rows = s.scalars(
            select(ClientOrder).order_by(ClientOrder.created_at.desc())).all()
        return {"client_orders": [
            {"order_id": o.order_id, "sku": o.sku, "qty": o.qty, "status": o.status,
             "created_at": o.created_at.isoformat()} for o in rows]}


@router.post("/client-orders")
def create_client_order(req: CreateOrderRequest):
    if req.qty <= 0:
        raise HTTPException(400, "qty must be positive")
    with session_scope() as s:
        if not s.get(Product, req.sku):
            raise HTTPException(404, f"unknown SKU {req.sku}")
        order = ClientOrder(
            order_id="CO-" + uuid.uuid4().hex[:8].upper(),
            sku=req.sku, qty=req.qty, status=req.status)
        s.add(order)
        s.flush()
        return {"client_order": {
            "order_id": order.order_id, "sku": order.sku, "qty": order.qty,
            "status": order.status, "created_at": order.created_at.isoformat()}}


@router.get("/budgets")
def budgets():
    with session_scope() as s:
        return {"budgets": [
            {"category": b.category, "allocated": b.allocated, "spent": b.spent,
             "remaining": b.allocated - b.spent} for b in s.scalars(select(Budget)).all()]}


@router.get("/logs")
def logs():
    with session_scope() as s:
        rows = s.scalars(select(ReorderLog).order_by(ReorderLog.created_at.desc())).all()
        return {"logs": [
            {"run_id": r.run_id, "sku": r.sku, "scenario": r.scenario, "trigger": r.trigger,
             "decision_type": r.decision_type, "status": r.status,
             "created_at": r.created_at.isoformat(),
             "result": json.loads(r.result_json),
             "trace": json.loads(r.trace_json)} for r in rows]}


@router.post("/eval/run")
def eval_run():
    return run_eval()


@router.post("/reset")
def reset():
    from app.db.seed import seed
    seed()
    return {"status": "reset", "message": "Demo database re-seeded to its initial state."}
