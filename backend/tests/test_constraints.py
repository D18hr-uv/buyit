"""Unit tests for the deterministic decision math (the source of truth)."""
from app.tools.constraints import compute_net_requirement, evaluate_constraints


def test_net_requirement_basic():
    assert compute_net_requirement(900, 100, 150, 50) == 800


def test_net_requirement_over_supplied_is_negative():
    assert compute_net_requirement(300, 50, 400, 200) == -250


def test_net_requirement_rounds_up():
    assert compute_net_requirement(100.4, 0, 0, 0) == 101


def test_all_constraints_pass():
    r = evaluate_constraints(
        qty=800, unit_price=0.9, min_order_qty=100, budget_remaining=1_000_000,
        vendor_capacity=100000, vendor_reliability=0.95, min_reliability=0.7)
    assert r.all_passed
    assert r.violations == []


def test_budget_binds_max_feasible():
    # remaining 1500 / price 3.0 -> 500 units feasible; 800 requested violates budget
    r = evaluate_constraints(
        qty=800, unit_price=3.0, min_order_qty=100, budget_remaining=1500,
        vendor_capacity=100000, vendor_reliability=0.9, min_reliability=0.7)
    assert not r.all_passed
    assert "budget" in r.violations
    assert r.max_feasible_qty == 500


def test_vendor_capacity_binds_max_feasible():
    r = evaluate_constraints(
        qty=800, unit_price=1.0, min_order_qty=100, budget_remaining=1_000_000,
        vendor_capacity=250, vendor_reliability=0.9, min_reliability=0.7)
    assert "vendor_capacity" in r.violations
    assert r.max_feasible_qty == 250


def test_moq_violation():
    r = evaluate_constraints(
        qty=50, unit_price=1.0, min_order_qty=100, budget_remaining=1_000_000,
        vendor_capacity=100000, vendor_reliability=0.9, min_reliability=0.7)
    assert "min_order_qty" in r.violations


def test_low_reliability_flagged_but_does_not_cap_qty():
    r = evaluate_constraints(
        qty=800, unit_price=1.0, min_order_qty=100, budget_remaining=1_000_000,
        vendor_capacity=100000, vendor_reliability=0.6, min_reliability=0.7)
    assert "vendor_reliability" in r.violations
    assert r.max_feasible_qty == 100000
