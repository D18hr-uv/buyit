import { useEffect, useState } from "react";
import { api } from "./api.js";
import { Timeline } from "./components/Timeline.jsx";
import { DecisionCard } from "./components/DecisionCard.jsx";
import { ApprovalPanel } from "./components/ApprovalPanel.jsx";
import { POTable } from "./components/POTable.jsx";
import { DataTable } from "./components/DataTable.jsx";
import { EvalPanel } from "./components/EvalPanel.jsx";
import { Pill } from "./components/Badge.jsx";

const TABS = [
  ["agent", "Agent"],
  ["inventory", "Inventory"],
  ["pos", "Purchase Orders"],
  ["orders", "Client Orders"],
  ["logs", "Reorder Logs"],
  ["eval", "Evaluation"],
];

export default function App() {
  const [presets, setPresets] = useState([]);
  const [health, setHealth] = useState(null);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("agent");
  const [data, setData] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    api.scenarios().then((d) => setPresets(d.presets)).catch((e) => setError(String(e)));
    api.health().then(setHealth).catch(() => {});
  }, []);

  // Fetch data for the active data-tab.
  useEffect(() => {
    (async () => {
      try {
        if (tab === "inventory") {
          const d = await api.inventory();
          setData((s) => ({ ...s, inventory: d.inventory }));
        } else if (tab === "pos") {
          const d = await api.purchaseOrders();
          setData((s) => ({ ...s, pos: d.purchase_orders }));
        } else if (tab === "orders") {
          const d = await api.clientOrders();
          setData((s) => ({ ...s, orders: d.client_orders }));
        } else if (tab === "logs") {
          const d = await api.logs();
          setData((s) => ({ ...s, logs: d.logs }));
        }
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [tab, run]);

  async function launch(preset) {
    setBusy(true); setError(null); setRun(null);
    try {
      setRun(await api.startRun(preset.scenario, preset.situation));
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  async function decideApproval(approved, editedQty) {
    setBusy(true);
    try {
      setRun(await api.approve(run.run_id, approved, editedQty));
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  async function resetDemo() {
    setBusy(true);
    try { await api.reset(); setRun(null); setData({}); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            <span className="text-[#f0503c]">AI</span> Purchasing Agent
          </h1>
          <p className="text-sm text-gray-500">
            Inventory management with an agent that investigates → decides → acts → validates.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {health && <Pill tone={health.llm === "openai" ? "green" : "gray"}>LLM: {health.llm}</Pill>}
          <button onClick={resetDemo} disabled={busy}
            className="rounded-lg bg-white px-3 py-1 text-xs font-medium text-gray-600 ring-1 ring-gray-200 hover:bg-gray-50 disabled:opacity-50">
            Reset demo data
          </button>
        </div>
      </header>

      <nav className="mb-5 flex flex-wrap gap-2">
        {TABS.map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)}
            className={"rounded-lg px-3 py-1.5 text-sm font-medium " +
              (tab === id ? "bg-[#f0503c] text-white" : "bg-white text-gray-600 ring-1 ring-gray-200")}>
            {label}
          </button>
        ))}
      </nav>

      {error && <div className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      {tab === "agent" && (
        <div className="grid gap-5 md:grid-cols-[300px_1fr]">
          <section>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">Scenarios</h2>
            <div className="space-y-2">
              {presets.map((p) => (
                <button key={p.id} onClick={() => launch(p)} disabled={busy}
                  className="w-full rounded-xl border border-gray-200 bg-white p-3 text-left hover:border-[#f0503c] disabled:opacity-50">
                  <div className="text-sm font-semibold text-gray-800">{p.label}</div>
                  <div className="mt-0.5 text-xs text-gray-500">{p.expectation}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-4">
            {busy && !run && (
              <div className="rounded-xl border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                Agent is investigating…
              </div>
            )}
            {!run && !busy && (
              <div className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
                Pick a scenario to run the agent.
              </div>
            )}
            {run && (
              <>
                <DecisionCard run={run} />
                {run.status === "awaiting_approval" && (
                  <ApprovalPanel run={run} busy={busy}
                    onApprove={(qty) => decideApproval(true, qty)}
                    onReject={() => decideApproval(false)} />
                )}
                <div className="rounded-xl border border-gray-200 bg-white p-4">
                  <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                    Reasoning timeline
                  </h3>
                  <Timeline trace={run.trace} />
                </div>
              </>
            )}
          </section>
        </div>
      )}

      {tab === "inventory" && (
        <DataTable rows={data.inventory} columns={[
          { key: "sku", label: "SKU" }, { key: "name", label: "Product" },
          { key: "category", label: "Category" }, { key: "on_hand", label: "On hand" },
          { key: "safety_stock", label: "Safety" }, { key: "reorder_point", label: "Reorder pt" },
          { key: "unit_cost", label: "Unit cost" },
        ]} />
      )}

      {tab === "pos" && <POTable pos={data.pos} />}

      {tab === "orders" && (
        <DataTable rows={data.orders} columns={[
          { key: "order_id", label: "Order" }, { key: "sku", label: "SKU" },
          { key: "qty", label: "Qty" }, { key: "status", label: "Status" },
          { key: "created_at", label: "Date", fmt: (v) => new Date(v).toLocaleDateString() },
        ]} empty="No client orders." />
      )}

      {tab === "logs" && (
        <DataTable rows={data.logs} columns={[
          { key: "created_at", label: "When", fmt: (v) => new Date(v).toLocaleString() },
          { key: "scenario", label: "Scenario" }, { key: "sku", label: "SKU" },
          { key: "trigger", label: "Trigger" }, { key: "decision_type", label: "Decision" },
          { key: "status", label: "Status", fmt: (v) => <Pill tone={v === "escalated" ? "coral" : "green"}>{v}</Pill> },
        ]} empty="No agent runs logged yet — run a scenario on the Agent tab." />
      )}

      {tab === "eval" && <EvalPanel />}
    </div>
  );
}
