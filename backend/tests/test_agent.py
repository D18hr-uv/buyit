"""End-to-end agent tests (stub LLM, SQLite) for all decision branches + the S2 loop."""
from app.agent import runner

NODE = "MFC-BOG"


def _s1(sku, qty=800):
    return runner.start_run("S1", {"sku": sku, "node_id": NODE, "recommended_qty": qty})


def test_s1_accept():
    r = _s1("SKU-WATER", 800)
    assert r["decision"]["type"] == "accept"
    assert r["decision"]["qty"] == 800
    assert r["needs_human"] is False
    assert r["action_result"]["po_id"]                     # PO created
    assert r["validation"]["acceptable"] is True
    assert r["status"] == "done"


def test_s1_modify_budget_capped():
    r = _s1("SKU-OIL", 800)
    assert r["decision"]["type"] == "modify"
    assert r["decision"]["qty"] == 500                     # budget caps 800 -> 500
    assert r["validation"]["acceptable"] is True


def test_s1_reject_already_covered():
    r = _s1("SKU-BEANS", 800)
    assert r["decision"]["type"] == "reject"
    assert r["action_result"] in (None, {}) or "po_id" not in (r["action_result"] or {})
    assert r["status"] == "done"


def test_s1_investigate_unreliable_forecast():
    r = _s1("SKU-CHOC", 800)
    assert r["decision"]["type"] == "investigate"


def test_s1_hitl_high_value_requires_approval_then_executes():
    r = _s1("SKU-COFFEE", 800)
    assert r["decision"]["type"] == "accept"
    assert r["needs_human"] is True
    assert r["status"] == "awaiting_approval"
    assert r["action_result"] is None or "po_id" not in (r["action_result"] or {})

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


def test_s2_supplier_shortfall_feedback_loop():
    r = runner.start_run("S2", {"sku": "SKU-ENERGY", "node_id": NODE, "po_id": "PO-ENERGY-0500"})
    # The loop: confirm_existing -> shortfall detected -> replan -> source_alternate
    assert r["iteration"] >= 1
    assert any(f["reason"] == "supplier_shortfall" for f in r["feedback"])
    assert r["decision"]["type"] == "source_alternate"
    assert r["decision"]["supplier_id"] == "SUP-VOLT"
    assert r["decision"]["qty"] == 250                     # exactly the shortfall gap
    assert r["validation"]["acceptable"] is True
    assert r["status"] == "done"
