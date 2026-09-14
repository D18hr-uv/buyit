"""Evaluation harness.

Runs each scenario through the agent and scores it against the six questions the
assignment asks (decision correct? got the info? respected constraints? right action?
validated? recovered on failure?). Prints a scorecard and returns it as JSON.

Run: `python -m app.eval.runner`
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from app.agent import runner as agent_runner
from app.db.seed import seed
from app.eval.scenarios import EVAL_SCENARIOS


def _tool_calls_in_trace(trace: List[Dict[str, Any]]) -> List[str]:
    for ev in trace:
        if ev.get("node") == "gather_context":
            return ev.get("data", {}).get("tool_calls", [])
    return []


def _score_one(sc: Dict[str, Any]) -> Dict[str, Any]:
    seed()  # deterministic, isolated state per scenario
    exp = sc["expected"]

    run = agent_runner.start_run(sc["scenario"], sc["situation"])
    if sc.get("auto_approve") and run.get("needs_human"):
        # Verify it actually paused before approving (the HITL check).
        paused = run["status"] == "awaiting_approval"
        run = agent_runner.approve_run(run["run_id"], approved=True)
        run["_paused_for_human"] = paused

    decision = run.get("decision") or {}
    action = run.get("action_result") or {}
    validation = run.get("validation") or {}
    tool_calls = _tool_calls_in_trace(run.get("trace", []))

    checks: Dict[str, bool] = {}

    # 1. Was the decision correct?
    ok = decision.get("type") == exp["decision"]
    if "qty" in exp:
        ok = ok and decision.get("qty") == exp["qty"]
    checks["decision_correct"] = ok

    # 2. Did the agent obtain the necessary information?
    checks["obtained_info"] = all(t in tool_calls for t in sc["required_tools"])

    # 3. Did it respect relevant constraints?
    if exp.get("action"):
        checks["respected_constraints"] = validation.get("acceptable") is True
    else:
        checks["respected_constraints"] = True  # no action => nothing to violate

    # 4. Did it take the appropriate action?
    took_action = bool(action.get("po_id"))
    checks["appropriate_action"] = took_action == bool(exp.get("action"))

    # 5. Did it validate the result?
    if exp.get("action"):
        checks["validated_result"] = bool(validation.get("checks"))
    else:
        checks["validated_result"] = True

    # 6. HITL: did it pause for approval when required?
    if exp.get("needs_human"):
        checks["paused_for_human"] = run.get("_paused_for_human", False)

    # 7. Recovery: did the feedback loop recover from a failed initial action?
    if exp.get("recovered"):
        checks["recovered_from_failure"] = (
            run.get("iteration", 0) >= 1
            and any(f.get("reason") == "supplier_shortfall" for f in run.get("feedback", []))
            and run.get("status") == "done"
        )

    passed = all(checks.values())
    return {
        "id": sc["id"],
        "scenario": sc["scenario"],
        "passed": passed,
        "checks": checks,
        "decision": decision.get("type"),
        "qty": decision.get("qty"),
        "status": run.get("status"),
        "iteration": run.get("iteration", 0),
    }


def run_eval() -> Dict[str, Any]:
    results = [_score_one(sc) for sc in EVAL_SCENARIOS]
    passed = sum(1 for r in results if r["passed"])
    return {"summary": {"passed": passed, "total": len(results)}, "results": results}


def _print_scorecard(report: Dict[str, Any]) -> None:
    print("\n=== AI Purchasing Agent — Evaluation Scorecard ===\n")
    header = f"{'scenario':<16}{'decision':<18}{'qty':<7}{'status':<10}{'result'}"
    print(header)
    print("-" * len(header))
    for r in report["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"{r['id']:<16}{str(r['decision']):<18}{str(r['qty']):<7}{r['status']:<10}{mark}")
        if not r["passed"]:
            for name, ok in r["checks"].items():
                if not ok:
                    print(f"    - failed check: {name}")
    s = report["summary"]
    print(f"\nTotal: {s['passed']}/{s['total']} scenarios passed.\n")


if __name__ == "__main__":
    report = run_eval()
    _print_scorecard(report)
    print(json.dumps(report, indent=2))
