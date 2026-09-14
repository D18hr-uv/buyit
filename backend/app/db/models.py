"""Operational data model (mock supply-chain domain)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"
    sku: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    unit_cost: Mapped[float] = mapped_column(Float)          # reference cost
    unit_volume: Mapped[float] = mapped_column(Float)        # storage units per unit
    is_perishable: Mapped[bool] = mapped_column(Boolean, default=False)
    shelf_life_days: Mapped[int] = mapped_column(Integer, default=365)


class FulfillmentNode(Base):
    __tablename__ = "fulfillment_nodes"
    node_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    region: Mapped[str] = mapped_column(String)


class Inventory(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    node_id: Mapped[str] = mapped_column(ForeignKey("fulfillment_nodes.node_id"))
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)


class DemandForecast(Base):
    __tablename__ = "demand_forecast"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    node_id: Mapped[str] = mapped_column(ForeignKey("fulfillment_nodes.node_id"))
    daily_forecast: Mapped[float] = mapped_column(Float)      # forecasted units/day
    horizon_days: Mapped[int] = mapped_column(Integer, default=30)
    recent_daily_actuals: Mapped[str] = mapped_column(Text, default="[]")  # JSON list


class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.9)   # 0..1
    region: Mapped[str] = mapped_column(String, default="LATAM")


class SupplierSku(Base):
    __tablename__ = "supplier_skus"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.supplier_id"))
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[float] = mapped_column(Float)
    available_capacity: Mapped[int] = mapped_column(Integer, default=100000)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.supplier_id"))
    node_id: Mapped[str] = mapped_column(ForeignKey("fulfillment_nodes.node_id"))
    qty: Mapped[int] = mapped_column(Integer)
    confirmed_qty: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="open")  # open|confirmed|partial|closed|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    expected_delivery_days: Mapped[int] = mapped_column(Integer, default=7)


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("fulfillment_nodes.node_id"))
    category: Mapped[str] = mapped_column(String)
    period: Mapped[str] = mapped_column(String, default="2026-Q3")
    allocated: Mapped[float] = mapped_column(Float)
    spent: Mapped[float] = mapped_column(Float, default=0.0)


class Storage(Base):
    __tablename__ = "storage"
    node_id: Mapped[str] = mapped_column(ForeignKey("fulfillment_nodes.node_id"), primary_key=True)
    total_capacity_units: Mapped[float] = mapped_column(Float)
    used_units: Mapped[float] = mapped_column(Float, default=0.0)


class AgentRun(Base):
    """Persisted trace of an agent run for observability + the UI timeline."""
    __tablename__ = "agent_runs"
    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="running")  # running|awaiting_approval|done|escalated
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    situation_json: Mapped[str] = mapped_column(Text, default="{}")
    trace_json: Mapped[str] = mapped_column(Text, default="[]")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
