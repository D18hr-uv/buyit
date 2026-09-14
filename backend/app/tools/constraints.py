"""Deterministic decision math + constraint validation.

These are PURE functions (no DB, no LLM) so they are trivially unit-testable and are the
single source of truth for every number the agent reports. The LLM never computes these.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import List


def compute_net_requirement(
    demand_over_horizon: float,
    safety_stock: int,
    on_hand: int,
    incoming_open_pos: int,
) -> int:
    """Units we actually need to purchase to cover demand + safety, net of supply on hand
    and already incoming. Never negative below zero is meaningful (=> over-supplied)."""
    net = demand_over_horizon + safety_stock - on_hand - incoming_open_pos
    return int(math.ceil(net))


@dataclass
class ConstraintCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class ConstraintResult:
    all_passed: bool
    max_feasible_qty: int
    checks: List[ConstraintCheck] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "all_passed": self.all_passed,
            "max_feasible_qty": self.max_feasible_qty,
            "violations": self.violations,
            "checks": [asdict(c) for c in self.checks],
        }


def evaluate_constraints(
    qty: int,
    unit_price: float,
    min_order_qty: int,
    budget_remaining: float,
    vendor_capacity: int,
    vendor_reliability: float,
    min_reliability: float,
) -> ConstraintResult:
    """Check a proposed purchase `qty` against every constraint and compute the largest
    quantity that would satisfy the quantitative constraints (budget + vendor capacity)."""
    checks: List[ConstraintCheck] = []

    order_value = qty * unit_price

    # Budget
    budget_ok = order_value <= budget_remaining + 1e-6
    checks.append(ConstraintCheck(
        "budget",
        budget_ok,
        f"order value {order_value:.2f} vs remaining budget {budget_remaining:.2f}",
    ))

    # Vendor capacity
    capacity_ok = qty <= vendor_capacity
    checks.append(ConstraintCheck(
        "vendor_capacity",
        capacity_ok,
        f"qty {qty} vs vendor capacity {vendor_capacity}",
    ))

    # Minimum order quantity
    moq_ok = qty == 0 or qty >= min_order_qty
    checks.append(ConstraintCheck(
        "min_order_qty",
        moq_ok,
        f"qty {qty} vs MOQ {min_order_qty}",
    ))

    # Vendor reliability
    reliability_ok = vendor_reliability >= min_reliability
    checks.append(ConstraintCheck(
        "vendor_reliability",
        reliability_ok,
        f"reliability {vendor_reliability:.2f} vs min {min_reliability:.2f}",
    ))

    max_by_budget = math.floor(budget_remaining / unit_price) if unit_price > 0 else qty
    max_feasible = max(0, min(max_by_budget, vendor_capacity))

    violations = [c.name for c in checks if not c.passed]
    # reliability failing does not reduce max_feasible_qty; it is a routing signal (HITL)
    all_passed = len(violations) == 0

    return ConstraintResult(
        all_passed=all_passed,
        max_feasible_qty=max_feasible,
        checks=checks,
        violations=violations,
    )
