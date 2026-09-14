import { useEffect, useState } from "react";
import { api } from "./api.js";
import { Timeline } from "./components/Timeline.jsx";
import { DecisionCard } from "./components/DecisionCard.jsx";
import { ApprovalPanel } from "./components/ApprovalPanel.jsx";
import { POTable } from "./components/POTable.jsx";
import { DataTable } from "./components/DataTable.jsx";
import { LogsTable } from "./components/LogsTable.jsx";
import { EvalPanel } from "./components/EvalPanel.jsx";
import { CreatePOForm } from "./components/CreatePOForm.jsx";
import { CreateOrderForm } from "./components/CreateOrderForm.jsx";
import { CreateSkuForm } from "./components/CreateSkuForm.jsx";
import { ReceivePOForm } from "./components/ReceivePOForm.jsx";
import { AgentDrawer } from "./components/AgentDrawer.jsx";
import { Pill } from "./components/Badge.jsx";
import { Icon } from "./components/Icon.jsx";

const TABS = [
  ["agent", "Agent"],
  ["inventory", "Inventory"],
  ["pos", "Purchase Orders"],
  ["orders", "Client Orders"],
  ["logs", "Reorder Logs"],
  ["eval", "Evaluation"],
];

const ORDER_STATUS_TONE = {
  open: "blue",
  fulfilled: "green",
  confirmed: "green",
  partial: "amber",
  cancelled: "gray",
  pending: "amber",
};

export default function App() {
  const [presets, setPresets] = useState([]);
  const [health, setHealth] = useState(null);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [activePreset, setActivePreset] = useState(null);
  const [tab, setTab] = useState("agent");
  const [data, setData] = useState({});
  const [error, setError] = useState(null);
  const [skus, setSkus] = useState([]);
  const [categories, setCategories] = useState([]);
  const [vendorList, setVendorList] = useState([]);
  const [creating, setCreating] = useState(null); // "po" | "order" | "sku" | null
  const [receivingPo, setReceivingPo] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);
  // Contextual agent run shown in a slide-over drawer over the current tab.
  const [drawer, setDrawer] = useState(null); // { run, busy, subtitle } | null

  // Reference data for the create-record forms (SKUs, categories, vendors).
  function loadRefData() {
    api.inventory()
      .then((d) => {
        setSkus(d.inventory.map((r) => ({ sku: r.sku, name: r.name })));
        setCategories([...new Set(d.inventory.map((r) => r.category))].sort());
      })
      .catch(() => {});
    api.vendors().then((d) => setVendorList(d.vendors)).catch(() => {});
  }

  useEffect(() => {
    api.scenarios().then((d) => setPresets(d.presets)).catch((e) => setError(String(e)));
    api.health().then(setHealth).catch(() => {});
    loadRefData();
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
  }, [tab, run, refreshTick]);

  function onRecordCreated() {
    setCreating(null);
    setReceivingPo(null);
    setRefreshTick((t) => t + 1);
    loadRefData(); // keep SKU/category lists fresh for the other create forms
  }

  async function closePo(po) {
    try {
      await api.closePurchaseOrder(po.po_id);
      setRefreshTick((t) => t + 1);
    } catch (e) {
      setError(String(e));
    }
  }

  // Launch a scenario run in-context (from an inventory/PO row) into the drawer.
  async function launchContextual(scenario, situation, subtitle) {
    setError(null);
    setDrawer({ run: null, busy: true, subtitle });
    try {
      const r = await api.startRun(scenario, situation);
      setDrawer({ run: r, busy: false, subtitle });
      setRefreshTick((t) => t + 1); // a run may create a PO / move stock
    } catch (e) {
      setError(String(e));
      setDrawer(null);
    }
  }

  async function drawerDecide(approved, editedQty) {
    if (!drawer?.run) return;
    setDrawer((d) => ({ ...d, busy: true }));
    try {
      const r = await api.approve(drawer.run.run_id, approved, editedQty);
      setDrawer((d) => ({ ...d, run: r, busy: false }));
      setRefreshTick((t) => t + 1);
    } catch (e) {
      setError(String(e));
      setDrawer((d) => ({ ...d, busy: false }));
    }
  }

  async function launch(preset) {
    setBusy(true); setError(null); setRun(null); setActivePreset(preset.id);
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
    try { await api.reset(); setRun(null); setData({}); setActivePreset(null); }
    finally { setBusy(false); }
  }

  const inv = data.inventory || [];
  const belowReorder = inv.filter((r) => r.on_hand < r.reorder_point).length;
  const invValue = inv.reduce((sum, r) => sum + (r.on_hand || 0) * (r.unit_cost || 0), 0);

  return (
    <div className="flex min-h-screen flex-col bg-background text-on-surface antialiased">
      {/* TOP APP BAR */}
      <header className="sticky top-0 z-50 flex h-16 w-full items-center justify-between border-b border-outline-variant bg-surface px-6 shadow-sm">
        <div className="flex items-center gap-8">
          <span className="flex items-center gap-1.5 text-headline-sm font-headline-sm font-bold tracking-tight text-on-surface">
            Buy<span className="text-[#F0503C]">It</span>
          </span>
          <nav className="hidden items-center gap-1 md:flex">
            {TABS.map(([id, label]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={
                  "rounded-lg px-3 py-1.5 text-title-md font-title-md transition-colors " +
                  (tab === id
                    ? "bg-[#F0503C]/10 text-[#F0503C] font-semibold"
                    : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface")
                }
              >
                {label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {health && (
            <div
              className={
                "hidden items-center gap-1.5 rounded-full border px-2.5 py-1 font-code-sm text-code-sm sm:flex " +
                (health.llm === "openai"
                  ? "border-tertiary-container/30 bg-tertiary-container/10 text-tertiary"
                  : "border-outline-variant bg-surface-container text-on-surface-variant")
              }
            >
              <span
                className={
                  "h-2 w-2 rounded-full " +
                  (health.llm === "openai" ? "animate-pulse bg-tertiary" : "bg-outline")
                }
              />
              LLM: {health.llm}
            </div>
          )}
          <button
            onClick={resetDemo}
            disabled={busy}
            className="hidden items-center gap-1.5 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-body-sm font-body-sm text-on-surface transition-all hover:bg-surface-container-low active:scale-[0.98] disabled:opacity-50 lg:flex"
          >
            <Icon name="refresh" className="text-[16px]" />
            Reset demo data
          </button>
          <div className="flex items-center gap-1">
            <button
              className="relative rounded-lg p-2 text-on-surface-variant transition-colors hover:bg-surface-container-low"
              title="Notifications"
            >
              <Icon name="notifications" className="text-[20px]" />
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary ring-2 ring-surface" />
            </button>
            <button
              className="rounded-lg p-2 text-on-surface-variant transition-colors hover:bg-surface-container-low"
              title="Settings"
            >
              <Icon name="settings" className="text-[20px]" />
            </button>
          </div>
          <div className="ml-1 flex h-8 w-8 items-center justify-center rounded-full bg-primary-fixed text-title-md font-title-md font-bold text-on-primary-fixed">
            CM
          </div>
        </div>
      </header>

      {/* MOBILE NAV (top bar nav is hidden below md) */}
      <nav className="flex gap-1 overflow-x-auto border-b border-outline-variant bg-surface px-3 py-2 md:hidden">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={
              "shrink-0 rounded-lg px-3 py-1.5 text-body-sm font-title-md transition-colors " +
              (tab === id
                ? "bg-[#F0503C]/10 text-[#F0503C] font-semibold"
                : "text-on-surface-variant hover:bg-surface-container-low")
            }
          >
            {label}
          </button>
        ))}
      </nav>

      {/* RUNTIME SUB-HEADER */}
      <section className="hidden items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-6 py-2.5 sm:flex">
        <div className="flex items-center gap-3">
          <span className="text-label-xs font-label-xs text-on-surface-variant">
            ACTIVE AGENT RUNTIME:
          </span>
          <span className="inline-flex items-center gap-1.5 rounded border border-surface-container-highest bg-surface-container px-2 py-0.5 font-code-sm text-code-sm text-on-surface">
            procurement-daemon-v4.2.1-prod
          </span>
          <span className="hidden font-body-sm text-body-sm text-on-surface-variant sm:inline">
            · Target: Quick-Commerce DC-East Hub
          </span>
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <span className="text-label-xs font-label-xs text-on-surface-variant">
            CONFIDENCE THRESHOLD:
          </span>
          <span className="font-code-sm text-code-sm font-semibold text-on-surface">&gt; 92.0%</span>
        </div>
      </section>

      {/* MAIN */}
      <main
        className={
          "mx-auto w-full flex-1 p-6 " +
          (tab === "agent" ? "max-w-[1600px]" : "max-w-7xl")
        }
      >
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-error-container bg-error-container px-3 py-2 text-body-sm text-on-error-container">
            <Icon name="error" className="text-[18px]" />
            {error}
          </div>
        )}

        {tab === "agent" && (
          <div className="flex flex-col gap-6 md:flex-row">
            {/* Scenarios aside */}
            <aside className="flex w-full shrink-0 flex-col gap-4 md:w-[320px]">
              <div className="flex items-center justify-between px-1">
                <h2 className="text-label-xs font-label-xs uppercase tracking-wider text-on-surface-variant">
                  Scenarios
                </h2>
                <span className="rounded-full bg-surface-container px-2 py-0.5 font-code-sm text-code-sm text-on-surface-variant">
                  {presets.length} Presets
                </span>
              </div>
              <div className="flex flex-col gap-2.5">
                {presets.map((p) => {
                  const active = activePreset === p.id;
                  return (
                    <button
                      key={p.id}
                      onClick={() => launch(p)}
                      disabled={busy}
                      className={
                        "group relative rounded-xl p-3.5 text-left transition-all disabled:opacity-50 " +
                        (active
                          ? "border-2 border-primary/70 bg-gradient-to-r from-primary/5 via-surface-container-lowest to-surface-container-lowest shadow-sm"
                          : "border border-outline-variant bg-surface-container-lowest hover:border-outline hover:bg-surface-container-low")
                      }
                    >
                      <div className="mb-1 flex items-start justify-between gap-2">
                        <h3 className="flex items-center gap-1.5 text-body-sm font-title-md font-semibold text-on-surface">
                          {active && (
                            <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                          )}
                          {p.label}
                        </h3>
                      </div>
                      <p className="text-body-sm font-body-sm text-on-surface-variant">
                        {p.expectation}
                      </p>
                    </button>
                  );
                })}
              </div>
            </aside>

            {/* Workspace */}
            <section className="flex flex-1 flex-col gap-6">
              {busy && !run && (
                <div className="flex items-center justify-center gap-2 rounded-xl border border-outline-variant bg-surface-container-lowest p-6 text-body-sm text-on-surface-variant shadow-sm">
                  <Icon name="progress_activity" className="animate-spin text-[18px] text-primary" />
                  Agent is investigating…
                </div>
              )}
              {!run && !busy && (
                <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-outline-variant bg-surface-container-lowest p-10 text-center text-body-sm text-on-surface-variant">
                  <Icon name="smart_toy" className="text-[32px] text-outline" />
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
                  <article className="flex flex-col gap-6 rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm md:p-6">
                    <div className="flex items-center gap-2.5 border-b border-outline-variant/60 pb-3">
                      <Icon name="timeline" className="text-[22px] text-primary" />
                      <h3 className="text-headline-sm font-headline-sm text-on-surface">
                        Agent Reasoning &amp; Execution Trace
                      </h3>
                    </div>
                    <Timeline trace={run.trace} />
                  </article>
                </>
              )}
            </section>
          </div>
        )}

        {tab === "inventory" && (
          <DataTable
            title="Inventory Management"
            badge="LIVE SYNC"
            subtitle="Real-time warehouse counts, safety buffers, and agent replenishment thresholds."
            headerAction={
              <button
                onClick={() => setCreating("sku")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-title-md font-title-md text-on-primary shadow-sm transition-all hover:bg-primary-container active:scale-[0.98]"
              >
                <Icon name="add" className="text-[18px]" />
                New SKU
              </button>
            }
            stats={[
              { label: "Total SKUs", value: inv.length, icon: "inventory_2" },
              {
                label: "Below Reorder Pt",
                value: belowReorder,
                tone: "primary",
                icon: "warning",
              },
              {
                label: "Total Inventory Value",
                value: `$${Math.round(invValue).toLocaleString()}`,
                icon: "payments",
              },
            ]}
            rows={inv}
            columns={[
              {
                key: "sku",
                label: "SKU",
                mono: true,
                fmt: (v) => <span className="font-semibold text-secondary">{v}</span>,
              },
              { key: "name", label: "Product" },
              {
                key: "category",
                label: "Category",
                fmt: (v) => (
                  <span className="rounded-full bg-surface-container px-2.5 py-0.5 text-label-xs font-label-xs text-on-secondary-container">
                    {v}
                  </span>
                ),
              },
              { key: "on_hand", label: "On hand", align: "right", mono: true },
              { key: "safety_stock", label: "Safety", align: "right", mono: true },
              { key: "reorder_point", label: "Reorder pt", align: "right", mono: true },
              {
                key: "unit_cost",
                label: "Unit cost",
                align: "right",
                mono: true,
                fmt: (v) => `$${v}`,
              },
              {
                key: "_status",
                label: "Stock Status",
                align: "center",
                fmt: (_, row) => {
                  const low = row.on_hand < row.reorder_point;
                  return (
                    <span
                      className={
                        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-label-xs font-label-xs font-semibold " +
                        (low
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-emerald-200 bg-emerald-50 text-emerald-800")
                      }
                    >
                      <span
                        className={
                          "h-1.5 w-1.5 rounded-full " +
                          (low ? "animate-pulse bg-red-500" : "bg-emerald-500")
                        }
                      />
                      {low ? "Low Stock" : "In Stock"}
                    </span>
                  );
                },
              },
              {
                key: "_agent",
                label: "Agent",
                align: "center",
                fmt: (_, row) =>
                  row.on_hand < row.reorder_point ? (
                    <button
                      onClick={() =>
                        launchContextual(
                          "S1",
                          { sku: row.sku },
                          `${row.sku} · S1 reorder review`
                        )
                      }
                      title="Review reorder (agent S1)"
                      aria-label="Review reorder"
                      className="inline-flex items-center justify-center rounded-md border border-outline-variant bg-surface-container p-1.5 text-primary transition-colors hover:bg-surface-container-high"
                    >
                      <Icon name="smart_toy" className="text-[16px]" />
                    </button>
                  ) : (
                    <span className="text-label-xs font-label-xs text-on-surface-variant">—</span>
                  ),
              },
            ]}
          />
        )}

        {tab === "pos" && (
          <POTable
            pos={data.pos}
            onReceive={setReceivingPo}
            onClosePo={closePo}
            onReplan={(po) =>
              launchContextual(
                "S2",
                { sku: po.sku, po_id: po.po_id },
                `${po.po_id} · ${po.sku} · S2 re-plan`
              )
            }
            action={
              <button
                onClick={() => setCreating("po")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-title-md font-title-md text-on-primary shadow-sm transition-all hover:bg-primary-container active:scale-[0.98]"
              >
                <Icon name="add" className="text-[18px]" />
                New PO
              </button>
            }
          />
        )}

        {tab === "orders" && (
          <DataTable
            title="Client Orders"
            subtitle="Demand signals from downstream clients driving replenishment needs."
            headerAction={
              <button
                onClick={() => setCreating("order")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-title-md font-title-md text-on-primary shadow-sm transition-all hover:bg-primary-container active:scale-[0.98]"
              >
                <Icon name="add" className="text-[18px]" />
                New order
              </button>
            }
            rows={data.orders}
            empty="No client orders."
            columns={[
              { key: "order_id", label: "Order", mono: true },
              {
                key: "sku",
                label: "SKU",
                mono: true,
                fmt: (v) => <span className="font-semibold text-secondary">{v}</span>,
              },
              { key: "qty", label: "Qty", align: "right", mono: true },
              {
                key: "status",
                label: "Status",
                align: "center",
                fmt: (v) => <Pill tone={ORDER_STATUS_TONE[v] || "gray"}>{v}</Pill>,
              },
              {
                key: "created_at",
                label: "Date",
                fmt: (v) => new Date(v).toLocaleDateString(),
              },
            ]}
          />
        )}

        {tab === "logs" && <LogsTable rows={data.logs} />}

        {tab === "eval" && <EvalPanel />}
      </main>

      {creating === "po" && (
        <CreatePOForm
          skus={skus}
          vendors={vendorList}
          onClose={() => setCreating(null)}
          onCreated={onRecordCreated}
        />
      )}
      {creating === "order" && (
        <CreateOrderForm
          skus={skus}
          onClose={() => setCreating(null)}
          onCreated={onRecordCreated}
        />
      )}
      {creating === "sku" && (
        <CreateSkuForm
          categories={categories}
          onClose={() => setCreating(null)}
          onCreated={onRecordCreated}
        />
      )}
      {receivingPo && (
        <ReceivePOForm
          po={receivingPo}
          onClose={() => setReceivingPo(null)}
          onCreated={onRecordCreated}
        />
      )}
      {drawer && (
        <AgentDrawer
          run={drawer.run}
          busy={drawer.busy}
          subtitle={drawer.subtitle}
          onApprove={(qty) => drawerDecide(true, qty)}
          onReject={() => drawerDecide(false)}
          onClose={() => setDrawer(null)}
        />
      )}

      {/* FOOTER */}
      <footer className="mt-auto flex flex-col items-center justify-between gap-3 border-t border-outline-variant bg-surface-container-lowest px-6 py-3 font-code-sm text-code-sm text-on-surface-variant sm:flex-row">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-tertiary" />
            Gateway: US-East-1 (Active)
          </span>
          <span className="text-outline-variant">·</span>
          <span>Policy Version: 2026.02-R3</span>
        </div>
        <span>BuyIt Decision Command Center</span>
      </footer>
    </div>
  );
}
