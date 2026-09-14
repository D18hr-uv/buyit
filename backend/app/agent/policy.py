"""Pure decision policy: maps computed analysis to a decision.

Kept separate from DB/LLM so it is deterministic and unit-testable. This is where the
"recommendation is not necessarily correct" principle lives: we reconcile the recommended
quantity against the independently computed net requirement and the hard constraints.
"""
from __future__ import annotations

from typing import Dict

from app.tools.constraints import ConstraintResult

TOLERANCE = 0.10  # accept the recommendation if within +/-10% of computed need


def decide_purchase(
    net_requirement: int,
    recommended_qty: int,
    demand_available: bool,
    forecast_reliable: bool,
    constraints: ConstraintResult,
    min_order_qty: int,
) -> Dict:
    """Return a decision dict: type, qty, confidence, factors[]."""
    factors = []

    # 1. Evidence gate -> investigate
    if not demand_available:
        return _decision("investigate", 0, "low",
                         ["No demand forecast available; cannot verify the recommendation."])
    if not forecast_reliable:
        return _decision(
            "investigate", 0, "low",
            ["Recent actual sales deviate >50% from forecast; forecast is unreliable. "
             "Investigate demand before committing to a large purchase."],
        )

    # 2. Already covered -> reject
    if net_requirement <= 0:
        return _decision(
            "reject", 0, "high",
            [f"On-hand inventory plus incoming POs already cover demand and safety stock "
             f"(net requirement = {net_requirement}). No purchase needed."],
        )

    # 3. Reconcile recommendation against computed net requirement
    lo, hi = net_requirement * (1 - TOLERANCE), net_requirement * (1 + TOLERANCE)
    if lo <= recommended_qty <= hi:
        base_qty = recommended_qty
        factors.append(f"Recommendation {recommended_qty} matches computed net requirement "
                       f"{net_requirement} (within {int(TOLERANCE*100)}%).")
    elif recommended_qty > hi:
        base_qty = net_requirement
        factors.append(f"Recommendation {recommended_qty} overshoots net requirement "
                       f"{net_requirement}; reducing to the computed need.")
    else:
        base_qty = net_requirement
        factors.append(f"Recommendation {recommended_qty} is below net requirement "
                       f"{net_requirement}; increasing to cover demand + safety stock.")

    # 4. Apply hard constraints
    final_qty = base_qty
    if final_qty > constraints.max_feasible_qty:
        final_qty = constraints.max_feasible_qty
        capped_by = [v for v in constraints.violations if v in ("budget", "vendor_capacity")]
        factors.append(f"Capped to {final_qty} by constraint(s): {', '.join(capped_by) or 'capacity'}.")

    # 5. Minimum order quantity
    if 0 < final_qty < min_order_qty:
        if min_order_qty <= constraints.max_feasible_qty:
            final_qty = min_order_qty
            factors.append(f"Raised to supplier minimum order quantity {min_order_qty}.")
        else:
            return _decision(
                "escalate", 0, "low",
                factors + [f"Cannot satisfy MOQ {min_order_qty} within constraints "
                           f"(max feasible {constraints.max_feasible_qty}). Escalating to a human."],
            )

    if final_qty <= 0:
        return _decision("escalate", 0, "low",
                         factors + ["No feasible quantity under current constraints; escalating."])

    # 6. Accept vs modify
    if final_qty == recommended_qty:
        confidence = "high" if constraints.all_passed else "medium"
        return _decision("accept", final_qty, confidence,
                         factors + ["Recommendation accepted."])
    confidence = "medium"
    return _decision("modify", final_qty, confidence,
                     factors + [f"Modifying recommended {recommended_qty} -> {final_qty}."])


def _decision(dtype: str, qty: int, confidence: str, factors) -> Dict:
    return {"type": dtype, "qty": qty, "confidence": confidence, "factors": list(factors)}
