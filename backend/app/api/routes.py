"""FastAPI routes for the purchasing agent."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.agent import runner
from app.config import get_settings
from app.db.models import FulfillmentNode, Product, PurchaseOrder
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
    return {"status": "ok", "llm": "openai" if settings.use_real_llm else "stub"}


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


@router.get("/catalog")
def catalog():
    with session_scope() as s:
        products = [
            {"sku": p.sku, "name": p.name, "category": p.category}
            for p in s.scalars(select(Product)).all()
        ]
        nodes = [
            {"node_id": n.node_id, "name": n.name, "region": n.region}
            for n in s.scalars(select(FulfillmentNode)).all()
        ]
    return {"products": products, "nodes": nodes}


@router.get("/purchase-orders")
def purchase_orders():
    with session_scope() as s:
        pos = s.scalars(select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())).all()
        return {"purchase_orders": [
            {"po_id": p.po_id, "sku": p.sku, "supplier_id": p.supplier_id, "node_id": p.node_id,
             "qty": p.qty, "confirmed_qty": p.confirmed_qty, "unit_price": p.unit_price,
             "status": p.status, "order_value": p.qty * p.unit_price}
            for p in pos
        ]}


@router.post("/eval/run")
def eval_run():
    return run_eval()
