"""Lean inventory-management schema.

Only the tables needed to drive the two purchasing scenarios end-to-end:
products, inventory, vendors (+ their per-product terms), vendor purchase orders,
client orders (which create demand), category budgets, and a reorder/agent log.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"
    sku: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    unit_cost: Mapped[float] = mapped_column(Float)


class Inventory(Base):
    __tablename__ = "inventory"
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"), primary_key=True)
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)


class Vendor(Base):
    __tablename__ = "vendors"
    vendor_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.9)  # 0..1


class VendorProduct(Base):
    """A vendor's terms for supplying a given SKU."""
    __tablename__ = "vendor_products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.vendor_id"))
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[float] = mapped_column(Float)
    available_capacity: Mapped[int] = mapped_column(Integer, default=100000)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class VendorPurchaseOrder(Base):
    __tablename__ = "vendor_purchase_orders"
    po_id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.vendor_id"))
    qty: Mapped[int] = mapped_column(Integer)
    confirmed_qty: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="open")  # open|confirmed|partial|closed|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expected_delivery_days: Mapped[int] = mapped_column(Integer, default=7)


class ClientOrder(Base):
    """A customer order. The stream of client orders is the demand signal."""
    __tablename__ = "client_orders"
    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    qty: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="fulfilled")  # fulfilled|open
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String)
    period: Mapped[str] = mapped_column(String, default="2026-Q3")
    allocated: Mapped[float] = mapped_column(Float)
    spent: Mapped[float] = mapped_column(Float, default=0.0)


class ReorderLog(Base):
    """Every agent run: the reorder/recommendation reviewed + the agent's full working."""
    __tablename__ = "reorder_logs"
    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(String, default="")
    scenario: Mapped[str] = mapped_column(String)
    trigger: Mapped[str] = mapped_column(String, default="recommendation_review")
    status: Mapped[str] = mapped_column(String, default="running")
    decision_type: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    situation_json: Mapped[str] = mapped_column(Text, default="{}")
    trace_json: Mapped[str] = mapped_column(Text, default="[]")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
