const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function req(path, opts) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  health: () => req("/health"),
  scenarios: () => req("/scenarios"),
  startRun: (scenario, situation) =>
    req("/runs", { method: "POST", body: JSON.stringify({ scenario, situation }) }),
  approve: (runId, approved, editedQty) =>
    req(`/runs/${runId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved, edited_qty: editedQty ?? null }),
    }),
  inventory: () => req("/inventory"),
  createInventoryItem: (body) =>
    req("/inventory", { method: "POST", body: JSON.stringify(body) }),
  vendors: () => req("/vendors"),
  purchaseOrders: () => req("/purchase-orders"),
  createPurchaseOrder: (body) =>
    req("/purchase-orders", { method: "POST", body: JSON.stringify(body) }),
  receivePurchaseOrder: (poId, confirmedQty) =>
    req(`/purchase-orders/${poId}/receive`, {
      method: "POST",
      body: JSON.stringify({ confirmed_qty: confirmedQty }),
    }),
  closePurchaseOrder: (poId) =>
    req(`/purchase-orders/${poId}/close`, { method: "POST" }),
  clientOrders: () => req("/client-orders"),
  createClientOrder: (body) =>
    req("/client-orders", { method: "POST", body: JSON.stringify(body) }),
  budgets: () => req("/budgets"),
  logs: () => req("/logs"),
  runEval: () => req("/eval/run", { method: "POST" }),
  reset: () => req("/reset", { method: "POST" }),
};
