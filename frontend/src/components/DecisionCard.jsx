import { Badge, Pill } from "./Badge.jsx";

const DECISION_TONE = {
  accept: "green",
  modify: "amber",
  reject: "gray",
  investigate: "blue",
  escalate: "coral",
  source_alternate: "amber",
  confirm_existing: "blue",
};

export function DecisionCard({ run }) {
  const d = run.decision;
  if (!d) return null;
  const v = run.validation;
  const action = run.action_result;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Pill tone={DECISION_TONE[d.type] || "gray"}>{d.type?.toUpperCase()}</Pill>
          {d.qty > 0 && <span className="text-sm font-semibold">qty: {d.qty}</span>}
          <span className="text-xs text-gray-500">confidence: {d.confidence}</span>
        </div>
        <div className="flex items-center gap-2">
          {d.overridden && <Pill tone="coral">guardrail override</Pill>}
          {run.iteration > 0 && <Pill tone="orange">re-planned ×{run.iteration}</Pill>}
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-gray-800">{d.rationale}</p>

      {d.factors?.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-gray-600">
          {d.factors.map((f, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="text-[#f0503c]">▸</span>
              {f}
            </li>
          ))}
        </ul>
      )}

      {action?.po_id && (
        <div className="mt-3 rounded-lg bg-gray-50 p-3 text-xs">
          <div className="font-semibold text-gray-700">Action taken</div>
          <div className="mt-1 font-mono text-gray-600">
            PO {action.po_id} — {action.qty} × {action.sku} from {action.supplier_id} @{" "}
            {action.unit_price} (value {Math.round(action.order_value)})
          </div>
        </div>
      )}

      {v?.checks?.length > 0 && (
        <div className="mt-3">
          <div className="mb-1 text-xs font-semibold text-gray-700">
            Validation {v.acceptable ? "(passed)" : "(discrepancy detected)"}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {v.checks.map((c) => (
              <Badge key={c.name} ok={c.passed}>
                {c.name}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
