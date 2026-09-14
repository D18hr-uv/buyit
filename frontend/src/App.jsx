import { useEffect, useState } from "react";
import { api } from "./api.js";
import { Timeline } from "./components/Timeline.jsx";
import { DecisionCard } from "./components/DecisionCard.jsx";
import { ApprovalPanel } from "./components/ApprovalPanel.jsx";
import { POTable } from "./components/POTable.jsx";
import { EvalPanel } from "./components/EvalPanel.jsx";
import { Pill } from "./components/Badge.jsx";

export default function App() {
  const [presets, setPresets] = useState([]);
  const [health, setHealth] = useState(null);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("agent");
  const [pos, setPos] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.scenarios().then((d) => setPresets(d.presets)).catch((e) => setError(String(e)));
    api.health().then(setHealth).catch(() => {});
    refreshPos();
  }, []);

  async function refreshPos() {
    try {
      setPos((await api.purchaseOrders()).purchase_orders);
    } catch {}
  }

  async function launch(preset) {
    setBusy(true);
    setError(null);
    setRun(null);
    try {
      const r = await api.startRun(preset.scenario, preset.situation);
      setRun(r);
      await refreshPos();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function decideApproval(approved, editedQty) {
    setBusy(true);
    try {
      const r = await api.approve(run.run_id, approved, editedQty);
      setRun(r);
      await refreshPos();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            <span className="text-[#f0503c]">AI</span> Purchasing Agent
          </h1>
          <p className="text-sm text-gray-500">
            Investigate → decide → act → validate, with a human-in-the-loop and a feedback loop.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {health && (
            <Pill tone={health.llm === "openai" ? "green" : "gray"}>LLM: {health.llm}</Pill>
          )}
          <button
            onClick={async () => {
              setBusy(true);
              try {
                await api.reset();
                setRun(null);
                await refreshPos();
              } finally {
                setBusy(false);
              }
            }}
            disabled={busy}
            className="rounded-lg bg-white px-3 py-1 text-xs font-medium text-gray-600 ring-1 ring-gray-200 hover:bg-gray-50 disabled:opacity-50"
          >
            Reset demo data
          </button>
        </div>
      </header>

      <nav className="mb-5 flex gap-2">
        {[
          ["agent", "Agent"],
          ["pos", "Purchase Orders"],
          ["eval", "Evaluation"],
        ].map(([id, label]) => (
          <button
            key={id}
            onClick={() => {
              setTab(id);
              if (id === "pos") refreshPos();
            }}
            className={
              "rounded-lg px-3 py-1.5 text-sm font-medium " +
              (tab === id ? "bg-[#f0503c] text-white" : "bg-white text-gray-600 ring-1 ring-gray-200")
            }
          >
            {label}
          </button>
        ))}
      </nav>

      {error && (
        <div className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      )}

      {tab === "agent" && (
        <div className="grid gap-5 md:grid-cols-[300px_1fr]">
          <section>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Scenarios
            </h2>
            <div className="space-y-2">
              {presets.map((p) => (
                <button
                  key={p.id}
                  onClick={() => launch(p)}
                  disabled={busy}
                  className="w-full rounded-xl border border-gray-200 bg-white p-3 text-left hover:border-[#f0503c] disabled:opacity-50"
                >
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
                  <ApprovalPanel
                    run={run}
                    busy={busy}
                    onApprove={(qty) => decideApproval(true, qty)}
                    onReject={() => decideApproval(false)}
                  />
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

      {tab === "pos" && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
              Purchase Orders
            </h2>
            <button
              onClick={refreshPos}
              className="rounded-lg bg-white px-3 py-1 text-sm ring-1 ring-gray-200 hover:bg-gray-50"
            >
              Refresh
            </button>
          </div>
          <POTable pos={pos} />
        </section>
      )}

      {tab === "eval" && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
            Evaluation Scorecard
          </h2>
          <EvalPanel />
        </section>
      )}
    </div>
  );
}
