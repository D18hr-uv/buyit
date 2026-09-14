"""Preset scenarios surfaced in the dashboard launcher."""

PRESETS = [
    {"id": "s1-accept", "label": "S1 · Accept (recommendation matches need)", "scenario": "S1",
     "situation": {"sku": "SKU-WATER", "recommended_qty": 800},
     "expectation": "Recommendation of 800 matches the computed net requirement; accept and place PO."},
    {"id": "s1-modify", "label": "S1 · Modify (budget constraint)", "scenario": "S1",
     "situation": {"sku": "SKU-OIL", "recommended_qty": 800},
     "expectation": "Need is 800 but the oils budget only allows 500; modify down to 500."},
    {"id": "s1-reject", "label": "S1 · Reject (already covered)", "scenario": "S1",
     "situation": {"sku": "SKU-BEANS", "recommended_qty": 800},
     "expectation": "Inventory + open POs already cover demand; reject the purchase."},
    {"id": "s1-investigate", "label": "S1 · Investigate (demand anomaly)", "scenario": "S1",
     "situation": {"sku": "SKU-CHOC", "recommended_qty": 800},
     "expectation": "Recent sales spiked ~3x vs the prior week; investigate before committing."},
    {"id": "s1-hitl", "label": "S1 · Human approval (high value)", "scenario": "S1",
     "situation": {"sku": "SKU-COFFEE", "recommended_qty": 800},
     "expectation": "Order value > 50,000 threshold; pause for buyer approval before executing."},
    {"id": "s2-shortfall", "label": "S2 · Vendor shortfall (feedback loop)", "scenario": "S2",
     "situation": {"sku": "SKU-ENERGY", "po_id": "PO-ENERGY-0500"},
     "expectation": "Vendor confirms only 250 of 500; re-plan and source the 250 gap from an alternate."},
]
