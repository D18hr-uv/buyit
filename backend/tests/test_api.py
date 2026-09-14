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
