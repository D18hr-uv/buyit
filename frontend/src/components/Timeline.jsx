import { Badge } from "./Badge.jsx";

const NODE_META = {
  ingest: { icon: "📥", color: "bg-gray-400" },
  agent_reason: { icon: "🤖", color: "bg-blue-500" },
  guardrail: { icon: "🛡️", color: "bg-[#f0503c]" },
  approval_gate: { icon: "🙋", color: "bg-amber-500" },
  act: { icon: "⚡", color: "bg-purple-500" },
  validate: { icon: "✅", color: "bg-emerald-500" },
  replan: { icon: "🔁", color: "bg-orange-500" },
  escalate: { icon: "🚨", color: "bg-rose-600" },
  finalize: { icon: "🏁", color: "bg-gray-600" },
};

function DataDetails({ node, data }) {
  if (!data || Object.keys(data).length === 0) return null;

  if (node === "agent_reason") {
    const p = data.llm_proposed;
    return (
      <div className="mt-2 space-y-2 text-xs">
        <div className="flex flex-wrap gap-1">
          {(data.tool_calls || []).map((t, i) => (
            <span key={i} className="rounded bg-blue-50 px-1.5 py-0.5 font-mono text-blue-700">
              {t}()
            </span>
          ))}
        </div>
        {p && (
          <div className="rounded bg-blue-50 p-2 text-blue-800">
            <span className="font-semibold">Model proposed:</span> {p.decision_type}
            {p.qty ? ` · qty ${p.qty}` : ""}
            {p.vendor_id ? ` · ${p.vendor_id}` : ""}
          </div>
        )}
        {data.retrieved_rules?.length > 0 && (
          <details className="text-gray-600">
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

  if (node === "guardrail") {
    const s = data.analysis_summary || {};
    const checks = data.constraints?.checks || [];
    return (
      <div className="mt-2 space-y-2 text-xs">
        {data.overridden && (
          <div className="rounded bg-rose-50 px-2 py-1 font-medium text-rose-700">
            ⚠ Guardrail overrode the model's proposal
          </div>
        )}
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono text-gray-700 sm:grid-cols-3">
          {Object.entries(s).map(([k, v]) => (
            <div key={k}>
              <span className="text-gray-400">{k}:</span> {String(v)}
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {checks.map((c) => (
            <Badge key={c.name} ok={c.passed}>
              {c.name}
            </Badge>
          ))}
        </div>
      </div>
    );
  }

  if (node === "analyze") {
    const s = data.analysis_summary || {};
    const checks = data.constraints?.checks || [];
    return (
      <div className="mt-2 space-y-2 text-xs">
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono text-gray-700 sm:grid-cols-3">
          {Object.entries(s).map(([k, v]) => (
            <div key={k}>
              <span className="text-gray-400">{k}:</span> {String(v)}
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {checks.map((c) => (
            <Badge key={c.name} ok={c.passed}>
              {c.name}
            </Badge>
          ))}
        </div>
      </div>
    );
  }

  return (
    <details className="mt-1 text-xs text-gray-500">
      <summary className="cursor-pointer">details</summary>
      <pre className="mt-1 overflow-x-auto rounded bg-gray-50 p-2 text-[11px]">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
}

export function Timeline({ trace }) {
  if (!trace?.length) return null;
  return (
    <ol className="relative space-y-1">
      {trace.map((ev, i) => {
        const meta = NODE_META[ev.node] || { icon: "•", color: "bg-gray-400" };
        return (
          <li key={i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-sm ${meta.color} text-white`}
              >
                {meta.icon}
              </div>
              {i < trace.length - 1 && <div className="w-px flex-1 bg-gray-200" />}
            </div>
            <div className="flex-1 pb-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">{ev.title}</span>
                <span className="font-mono text-[10px] uppercase tracking-wide text-gray-400">
                  {ev.node}
                </span>
              </div>
              <p className="text-sm text-gray-600">{ev.summary}</p>
              <DataDetails node={ev.node} data={ev.data} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
