"""End-to-end agent tests (stub planner, SQLite) for all decision branches + the S2 loop."""
from app.agent import nodes, runner


def test_guardrail_overrides_hallucinated_quantity():
    """If the (LLM) proposal contradicts the verified numbers, the guardrail corrects it."""
    state = {
        "scenario": "S1",
        "situation": {"sku": "SKU-WATER", "recommended_qty": 800},
        "feedback": [],
        "proposed_decision": {"decision_type": "accept", "qty": 9999,
                              "vendor_id": "SUP-AQUA", "rationale": "buy lots"},
    }
    out = nodes.guardrail(state)
    d = out["decision"]
    assert d["overridden"] is True
    assert d["qty"] == 800
    assert d["llm_proposed"]["qty"] == 9999


def _s1(sku, qty=800):
    return runner.start_run("S1", {"sku": sku, "recommended_qty": qty})


def test_s1_accept():
    r = _s1("SKU-WATER", 800)
    assert r["decision"]["type"] == "accept"
    assert r["decision"]["qty"] == 800
    assert r["needs_human"] is False
    assert r["action_result"]["po_id"]
    assert r["validation"]["acceptable"] is True
    assert r["status"] == "done"


def test_s1_modify_budget_capped():
    r = _s1("SKU-OIL", 800)
    assert r["decision"]["type"] == "modify"
    assert r["decision"]["qty"] == 500
    assert r["validation"]["acceptable"] is True


def test_s1_reject_already_covered():
    r = _s1("SKU-BEANS", 800)
    assert r["decision"]["type"] == "reject"
    assert r["action_result"] in (None, {}) or "po_id" not in (r["action_result"] or {})
    assert r["status"] == "done"


def test_s1_investigate_demand_anomaly():
    r = _s1("SKU-CHOC", 800)
    assert r["decision"]["type"] == "investigate"


def test_s1_hitl_high_value_requires_approval_then_executes():
    r = _s1("SKU-COFFEE", 800)
    assert r["decision"]["type"] == "accept"
    assert r["needs_human"] is True
    assert r["status"] == "awaiting_approval"
    approved = runner.approve_run(r["run_id"], approved=True)
    assert approved["action_result"]["po_id"]
    assert approved["validation"]["acceptable"] is True
    assert approved["status"] == "done"


def test_s1_hitl_rejection_creates_no_po():
    r = _s1("SKU-COFFEE", 800)
    assert r["needs_human"] is True
    rejected = runner.approve_run(r["run_id"], approved=False)
    assert rejected["decision"]["type"] == "reject"
    assert rejected["status"] == "done"


def test_s2_vendor_shortfall_feedback_loop():
    r = runner.start_run("S2", {"sku": "SKU-ENERGY", "po_id": "PO-ENERGY-0500"})
    assert r["iteration"] >= 1
    assert any(f["reason"] == "vendor_shortfall" for f in r["feedback"])
    assert r["decision"]["type"] == "source_alternate"
    assert r["decision"]["vendor_id"] == "SUP-VOLT"
    assert r["decision"]["qty"] == 250
    assert r["validation"]["acceptable"] is True
    assert r["status"] == "done"
