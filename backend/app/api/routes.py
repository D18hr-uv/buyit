"""FastAPI routes for the inventory-management purchasing agent."""
from __future__ import annotations

import json
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
    VendorPurchaseOrder,
)
from app.db.session import session_scope
from app.eval.runner import run_eval
from app.presets import PRESETS

router = APIRouter()
settings = get_settings()


class RunRequest(BaseModel):
    scenario: str
    situation: Dict[str, Any]


class ApprovalRequest(BaseModel):
    approved: bool
    edited_qty: Optional[int] = None


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


@router.get("/client-orders")
def client_orders():
    with session_scope() as s:
        rows = s.scalars(
            select(ClientOrder).order_by(ClientOrder.created_at.desc())).all()
        return {"client_orders": [
            {"order_id": o.order_id, "sku": o.sku, "qty": o.qty, "status": o.status,
             "created_at": o.created_at.isoformat()} for o in rows]}


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
             "result": json.loads(r.result_json)} for r in rows]}


@router.post("/eval/run")
def eval_run():
    return run_eval()


@router.post("/reset")
def reset():
    from app.db.seed import seed
    seed()
    return {"status": "reset", "message": "Demo database re-seeded to its initial state."}
