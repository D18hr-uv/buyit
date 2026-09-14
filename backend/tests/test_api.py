"""Endpoint tests for the manual create-record routes (PO + client order)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# SKU-WATER is supplied by SUP-AQUA in the seed (has a VendorProduct with terms).
SKU = "SKU-WATER"
VENDOR = "SUP-AQUA"


def test_create_purchase_order_auto_price():
    before = len(client.get("/purchase-orders").json()["purchase_orders"])

    res = client.post("/purchase-orders", json={"sku": SKU, "vendor_id": VENDOR, "qty": 120})
    assert res.status_code == 200
    po = res.json()["purchase_order"]
    assert po["po_id"].startswith("PO-")
    assert po["qty"] == 120
    assert po["status"] == "open"
    assert po["confirmed_qty"] == 0
    assert po["unit_price"] > 0                      # resolved from the vendor's contract
    assert po["order_value"] == po["qty"] * po["unit_price"]

    pos = client.get("/purchase-orders").json()["purchase_orders"]
    assert len(pos) == before + 1
    assert any(p["po_id"] == po["po_id"] for p in pos)


def test_create_purchase_order_respects_explicit_price():
    res = client.post(
        "/purchase-orders",
        json={"sku": SKU, "vendor_id": VENDOR, "qty": 10, "unit_price": 2.5})
    assert res.status_code == 200
    po = res.json()["purchase_order"]
    assert po["unit_price"] == 2.5
    assert po["order_value"] == 25.0


def _on_hand(sku):
    row = next(r for r in client.get("/inventory").json()["inventory"] if r["sku"] == sku)
    return row["on_hand"]


def test_create_po_with_confirmed_qty_moves_stock():
    before = _on_hand(SKU)
    res = client.post(
        "/purchase-orders",
        json={"sku": SKU, "vendor_id": VENDOR, "qty": 100, "confirmed_qty": 40})
    assert res.status_code == 200
    po = res.json()["purchase_order"]
    assert po["confirmed_qty"] == 40
    assert po["status"] == "partial"
    assert _on_hand(SKU) == before + 40


def test_create_po_confirmed_exceeding_qty_rejected():
    assert client.post(
        "/purchase-orders",
        json={"sku": SKU, "vendor_id": VENDOR, "qty": 10, "confirmed_qty": 20}
    ).status_code == 400


def test_receive_po_moves_stock_and_advances_status():
    po = client.post(
        "/purchase-orders", json={"sku": SKU, "vendor_id": VENDOR, "qty": 60}
    ).json()["purchase_order"]
    assert po["status"] == "open" and po["confirmed_qty"] == 0
    before = _on_hand(SKU)

    # partial receive
    r1 = client.post(f"/purchase-orders/{po['po_id']}/receive", json={"confirmed_qty": 25})
    assert r1.status_code == 200
    assert r1.json()["purchase_order"]["status"] == "partial"
    assert _on_hand(SKU) == before + 25

    # full receive moves only the delta (35 more), status -> confirmed
    r2 = client.post(f"/purchase-orders/{po['po_id']}/receive", json={"confirmed_qty": 60})
    assert r2.json()["purchase_order"]["status"] == "confirmed"
    assert _on_hand(SKU) == before + 60


def test_receive_po_rejects_reduction_and_overflow_and_missing():
    po = client.post(
        "/purchase-orders", json={"sku": SKU, "vendor_id": VENDOR, "qty": 30, "confirmed_qty": 20}
    ).json()["purchase_order"]
    assert client.post(
        f"/purchase-orders/{po['po_id']}/receive", json={"confirmed_qty": 10}
    ).status_code == 400  # can't reduce below received
    assert client.post(
        f"/purchase-orders/{po['po_id']}/receive", json={"confirmed_qty": 999}
    ).status_code == 400  # exceeds ordered
    assert client.post(
        "/purchase-orders/PO-NOPE/receive", json={"confirmed_qty": 1}
    ).status_code == 404


def test_contextual_s1_run_computes_recommended_qty():
    # No recommended_qty supplied -> backend derives it from the SKU's net requirement.
    res = client.post("/runs", json={"scenario": "S1", "situation": {"sku": "SKU-WATER"}})
    assert res.status_code == 200
    body = res.json()
    assert body.get("decision") is not None
    # SKU-WATER's designed net requirement is 800 -> the agent should act on ~that qty.
    assert body["decision"].get("qty", 0) > 0


def test_contextual_s1_requires_sku():
    assert client.post("/runs", json={"scenario": "S1", "situation": {}}).status_code == 400


def test_close_po_blocks_further_receiving():
    po = client.post(
        "/purchase-orders", json={"sku": SKU, "vendor_id": VENDOR, "qty": 40, "confirmed_qty": 10}
    ).json()["purchase_order"]

    res = client.post(f"/purchase-orders/{po['po_id']}/close")
    assert res.status_code == 200
    assert res.json()["purchase_order"]["status"] == "closed"

    # a closed PO can no longer be received
    assert client.post(
        f"/purchase-orders/{po['po_id']}/receive", json={"confirmed_qty": 30}
    ).status_code == 400
    assert client.post("/purchase-orders/PO-NOPE/close").status_code == 404


def test_create_purchase_order_validates_input():
    assert client.post(
        "/purchase-orders", json={"sku": SKU, "vendor_id": VENDOR, "qty": 0}
    ).status_code == 400
    assert client.post(
        "/purchase-orders", json={"sku": "NOPE", "vendor_id": VENDOR, "qty": 5}
    ).status_code == 404
    assert client.post(
        "/purchase-orders", json={"sku": SKU, "vendor_id": "NOPE", "qty": 5}
    ).status_code == 404


def test_create_client_order():
    before = len(client.get("/client-orders").json()["client_orders"])

    res = client.post("/client-orders", json={"sku": SKU, "qty": 42, "status": "open"})
    assert res.status_code == 200
    order = res.json()["client_order"]
    assert order["order_id"].startswith("CO-")
    assert order["sku"] == SKU
    assert order["qty"] == 42
    assert order["status"] == "open"

    orders = client.get("/client-orders").json()["client_orders"]
    assert len(orders) == before + 1
    assert any(o["order_id"] == order["order_id"] for o in orders)


def test_create_client_order_validates_input():
    assert client.post("/client-orders", json={"sku": "NOPE", "qty": 5}).status_code == 404
    assert client.post("/client-orders", json={"sku": SKU, "qty": 0}).status_code == 400


def test_create_inventory_item():
    before = len(client.get("/inventory").json()["inventory"])

    res = client.post("/inventory", json={
        "sku": "SKU-NEW1", "name": "Test Widget", "category": "Pantry",
        "unit_cost": 3.5, "on_hand": 40, "safety_stock": 10, "reorder_point": 25})
    assert res.status_code == 200
    item = res.json()["item"]
    assert item["sku"] == "SKU-NEW1"
    assert item["on_hand"] == 40 and item["reorder_point"] == 25

    inv = client.get("/inventory").json()["inventory"]
    assert len(inv) == before + 1
    row = next(r for r in inv if r["sku"] == "SKU-NEW1")
    assert row["name"] == "Test Widget" and row["unit_cost"] == 3.5

    # A newly created SKU can immediately back a client order.
    assert client.post("/client-orders", json={"sku": "SKU-NEW1", "qty": 5}).status_code == 200


def test_create_inventory_item_rejects_duplicate_and_bad_input():
    assert client.post("/inventory", json={
        "sku": SKU, "name": "dup", "category": "x", "unit_cost": 1.0
    }).status_code == 409
    assert client.post("/inventory", json={
        "sku": "SKU-BADCOST", "name": "n", "category": "x", "unit_cost": -1.0
    }).status_code == 400
