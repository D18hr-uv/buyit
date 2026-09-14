import { Badge } from "./Badge.jsx";
import { Icon } from "./Icon.jsx";

// icon + node-marker color per trace node type.
const NODE_META = {
  ingest: { icon: "inbox", color: "border-secondary text-secondary" },
  agent_reason: { icon: "smart_toy", color: "border-primary text-primary" },
  guardrail: { icon: "shield", color: "border-tertiary text-tertiary" },
  approval_gate: { icon: "person_check", color: "border-[#F59E0B] text-[#92400E]" },
  act: { icon: "bolt", color: "border-primary text-primary" },
  validate: { icon: "check", color: "border-tertiary text-tertiary" },
  replan: { icon: "sync", color: "border-[#F59E0B] text-[#92400E]" },
  escalate: { icon: "priority_high", color: "border-primary text-primary" },
  finalize: { icon: "flag", color: "border-on-surface text-on-surface" },
};

function DataDetails({ node, data }) {
  if (!data || Object.keys(data).length === 0) return null;

  if (node === "agent_reason") {
    const p = data.llm_proposed;
    return (
      <div className="mt-2.5 space-y-2.5 text-body-sm">
        {(data.tool_calls || []).length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {data.tool_calls.map((t, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 rounded border border-outline-variant bg-surface-container px-2.5 py-1 font-code-sm text-code-sm text-on-surface"
              >
                <Icon name="terminal" className="text-[13px] text-on-surface-variant" />
                {t}()
              </span>
            ))}
          </div>
        )}
        {p && (
          <div className="flex items-center justify-between rounded border border-primary/30 bg-surface-container-lowest p-2.5">
            <span className="text-body-sm font-body-sm text-on-surface">
              Model proposed:{" "}
              <strong className="font-semibold text-primary">
                {p.decision_type}
                {p.qty ? ` · qty ${p.qty}` : ""}
                {p.vendor_id ? ` · ${p.vendor_id}` : ""}
              </strong>
            </span>
          </div>
        )}
        {data.retrieved_rules?.length > 0 && (
          <details className="text-body-sm text-on-surface-variant">
            <summary className="cursor-pointer font-medium">
              RAG: {data.retrieved_rules.length} business rules retrieved
            </summary>
            <ul className="ml-4 mt-1 list-disc space-y-0.5">
              {data.retrieved_rules.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    );
  }

  if (node === "guardrail" || node === "analyze") {
    const s = data.analysis_summary || {};
    const checks = data.constraints?.checks || [];
    return (
      <div className="mt-2.5 space-y-2.5 text-body-sm">
        {data.overridden && (
          <div className="rounded bg-error-container px-2 py-1 font-medium text-on-error-container">
            ⚠ Guardrail overrode the model's proposal
          </div>
        )}
        {Object.keys(s).length > 0 && (
          <div className="grid grid-cols-2 gap-2 pt-0.5 sm:grid-cols-4">
            {Object.entries(s).map(([k, v]) => (
              <div
                key={k}
                className="rounded border border-outline-variant bg-surface-container-lowest p-2"
              >
                <span className="block text-label-xs font-label-xs text-on-surface-variant">
                  {k}
                </span>
                <span className="font-code-md text-code-md font-bold text-on-surface">
                  {String(v)}
                </span>
              </div>
            ))}
          </div>
        )}
        {checks.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {checks.map((c) => (
              <Badge key={c.name} ok={c.passed}>
                {c.name}
              </Badge>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <details className="mt-1 text-body-sm text-on-surface-variant">
      <summary className="cursor-pointer">details</summary>
      <pre className="mt-1 overflow-x-auto rounded bg-surface-container-low p-2 font-code-sm text-code-sm">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
}

export function Timeline({ trace }) {
  if (!trace?.length) return null;
  return (
    <div className="relative space-y-7 pl-6 before:absolute before:bottom-2 before:left-3 before:top-2 before:w-[2px] before:bg-outline-variant/60">
      {trace.map((ev, i) => {
        const meta = NODE_META[ev.node] || {
          icon: "circle",
          color: "border-outline text-on-surface-variant",
        };
        return (
          <div key={i} className="group relative flex items-start gap-4">
            <div
              className={`absolute -left-6 mt-0.5 flex h-6 w-6 items-center justify-center rounded-full border-2 bg-surface-container-lowest shadow-sm ${meta.color}`}
            >
              <Icon name={meta.icon} className="text-[14px]" />
            </div>
            <div className="flex-1 rounded-lg border border-outline-variant/40 bg-surface-container-low/40 p-3.5">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-title-md font-title-md text-on-surface">
                  {ev.title}
                </span>
                <span className="font-code-sm text-code-sm uppercase tracking-wide text-on-surface-variant">
                  {ev.node}
                </span>
              </div>
              <p className="text-body-sm font-body-sm text-on-surface-variant">
                {ev.summary}
              </p>
              <DataDetails node={ev.node} data={ev.data} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
