"""Service layer that drives the compiled graph, handling HITL pause/auto-resume,
and persists each run for observability."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from app.agent.graph import get_graph
from app.db.models import AgentRun
from app.db.session import session_scope

_MAX_STEPS = 30  # safety backstop against runaway resume loops


def _config(run_id: str) -> Dict[str, Any]:
    return {"configurable": {"thread_id": run_id}}


def _snapshot(run_id: str):
    return get_graph().get_state(_config(run_id))


def _drive(run_id: str) -> Dict[str, Any]:
    """Resume the graph past every low-risk `act`, stopping at END or a human gate."""
    graph = get_graph()
    cfg = _config(run_id)
    for _ in range(_MAX_STEPS):
        snap = graph.get_state(cfg)
        if not snap.next:                       # reached END
            break
        if "act" in snap.next:
            vals = snap.values
            waiting = vals.get("needs_human") and \
                vals.get("approval", {}).get("status") != "approved"
            if waiting:
                break                            # pause for human approval
        graph.invoke(None, cfg)                  # resume
    return graph.get_state(cfg).values


def _persist(values: Dict[str, Any]) -> None:
    run_id = values["run_id"]
    with session_scope() as s:
        run = s.get(AgentRun, run_id)
        if not run:
            run = AgentRun(run_id=run_id, scenario=values.get("scenario", "S1"))
            s.add(run)
        run.status = values.get("status", "running")
        run.situation_json = json.dumps(values.get("situation", {}))
        run.trace_json = json.dumps(values.get("trace", []))
        run.result_json = json.dumps({
            "decision": values.get("decision"),
            "action_result": values.get("action_result"),
            "validation": values.get("validation"),
            "analysis_summary": (values.get("analysis") or {}).get("summary"),
            "needs_human": values.get("needs_human", False),
            "feedback": values.get("feedback", []),
            "iteration": values.get("iteration", 0),
        })


def start_run(scenario: str, situation: Dict[str, Any]) -> Dict[str, Any]:
    run_id = "run-" + uuid.uuid4().hex[:10]
    graph = get_graph()
    initial = {"run_id": run_id, "scenario": scenario, "situation": situation,
               "trace": [], "feedback": []}
    graph.invoke(initial, _config(run_id))   # runs to first interrupt or END
    values = _drive(run_id)
    _persist(values)
    return _public(values)


def approve_run(run_id: str, approved: bool, edited_qty: Optional[int] = None) -> Dict[str, Any]:
    graph = get_graph()
    cfg = _config(run_id)
    snap = graph.get_state(cfg)
    if not snap.next or "act" not in snap.next:
        return _public(snap.values)  # nothing to approve

    if approved:
        graph.update_state(cfg, {
            "approval": {"status": "approved", "edited_qty": edited_qty},
            "needs_human": False,
        })
        values = _drive(run_id)
    else:
        # Human rejected the action: finalize without executing.
        graph.update_state(cfg, {
            "approval": {"status": "rejected"},
            "status": "done",
            "decision": {**snap.values.get("decision", {}), "type": "reject"},
            "trace": [{"node": "approval_gate", "title": "Rejected by human",
                       "summary": "Buyer rejected the proposed action; no PO created.",
                       "data": {}}],
        })
        values = graph.get_state(cfg).values
        values["status"] = "done"
    _persist(values)
    return _public(values)


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    with session_scope() as s:
        run = s.get(AgentRun, run_id)
        if not run:
            return None
        return {
            "run_id": run.run_id, "scenario": run.scenario, "status": run.status,
            "situation": json.loads(run.situation_json), "trace": json.loads(run.trace_json),
            "result": json.loads(run.result_json),
        }


def _public(values: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": values["run_id"],
        "scenario": values.get("scenario"),
        "status": values.get("status"),
        "situation": values.get("situation"),
        "decision": values.get("decision"),
        "needs_human": values.get("needs_human", False),
        "action_result": values.get("action_result"),
        "validation": values.get("validation"),
        "feedback": values.get("feedback", []),
        "iteration": values.get("iteration", 0),
        "retrieved_rules": values.get("retrieved_rules", []),
        "analysis": values.get("analysis"),
        "trace": values.get("trace", []),
    }
