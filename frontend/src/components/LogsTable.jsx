import { Fragment, useState } from "react";
import { Badge, Pill } from "./Badge.jsx";
import { Icon } from "./Icon.jsx";
import { Timeline } from "./Timeline.jsx";

const DECISION_TONE = {
  accept: "green",
  modify: "amber",
  reject: "gray",
  investigate: "blue",
  escalate: "coral",
  source_alternate: "amber",
  confirm_existing: "blue",
};

function LogDetail({ result, trace }) {
  if (!result || Object.keys(result).length === 0) {
    return (
      <p className="text-body-sm font-body-sm text-on-surface-variant">
        No detail recorded for this run.
      </p>
    );
  }
  const d = result.decision || {};
  const action = result.action_result;
  const summary = result.analysis_summary || {};
  const checks = result.validation?.checks || [];

  return (
    <div className="flex flex-col gap-4">
      {/* Decision */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={DECISION_TONE[d.type] || "gray"}>{d.type?.toUpperCase()}</Pill>
          {d.qty > 0 && (
            <span className="rounded-full border border-outline-variant bg-surface-container-low px-2.5 py-1 text-code-sm font-code-sm text-on-surface">
              qty: <strong className="font-semibold">{d.qty}</strong>
            </span>
          )}
          {d.confidence && (
            <span className="rounded-full border border-outline-variant bg-surface-container-low px-2.5 py-1 text-code-sm font-code-sm text-on-surface">
              confidence: <strong className="font-semibold text-tertiary">{d.confidence}</strong>
            </span>
          )}
          {result.iteration > 0 && (
            <Pill tone="orange" icon="sync">
              re-planned ×{result.iteration}
            </Pill>
          )}
        </div>
        {d.rationale && (
          <p className="text-body-sm font-body-sm text-on-surface">{d.rationale}</p>
        )}
        {d.factors?.length > 0 && (
          <ul className="space-y-1 text-body-sm font-body-sm text-on-surface-variant">
            {d.factors.map((f, i) => (
              <li key={i} className="flex items-start gap-2">
                <Icon name="chevron_right" className="mt-0.5 text-[16px] text-primary" />
                <span>{f}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Analysis summary */}
      {Object.keys(summary).length > 0 && (
        <div>
          <span className="text-label-xs font-label-xs uppercase tracking-wide text-on-surface-variant">
            Analysis
          </span>
          <div className="mt-1.5 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {Object.entries(summary).map(([k, v]) => (
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
        </div>
      )}

      {/* Action taken */}
      {action?.po_id && (
        <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-3 text-code-sm font-code-sm text-on-surface-variant">
          <span className="font-title-md text-body-sm text-on-surface">Action taken</span>
          <div className="mt-1">
            PO <strong className="text-primary">{action.po_id}</strong> — {action.qty} ×{" "}
            {action.sku} from {action.vendor_id} @ {action.unit_price} (value{" "}
            {Math.round(action.order_value)})
          </div>
        </div>
      )}

      {/* Validation */}
      {checks.length > 0 && (
        <div>
          <span className="text-label-xs font-label-xs uppercase tracking-wide text-on-surface-variant">
            Validation {result.validation?.acceptable ? "(passed)" : "(discrepancy)"}
          </span>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {checks.map((c) => (
              <Badge key={c.name} ok={c.passed}>
                {c.name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Feedback */}
      {result.feedback?.length > 0 && (
        <div>
          <span className="text-label-xs font-label-xs uppercase tracking-wide text-on-surface-variant">
            Feedback
          </span>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-body-sm font-body-sm text-on-surface-variant">
            {result.feedback.map((f, i) => (
              <li key={i}>{typeof f === "string" ? f : JSON.stringify(f)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Full reasoning trace */}
      {trace?.length > 0 && (
        <details className="rounded-lg border border-outline-variant bg-surface-container-lowest p-3">
          <summary className="flex cursor-pointer items-center gap-1.5 text-title-md font-title-md text-on-surface">
            <Icon name="timeline" className="text-[18px] text-primary" />
            Reasoning trace ({trace.length} steps)
          </summary>
          <div className="mt-4">
            <Timeline trace={trace} />
          </div>
        </details>
      )}
    </div>
  );
}

export function LogsTable({ rows }) {
  const [open, setOpen] = useState(null);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-display-lg font-headline-lg font-bold tracking-tight text-on-surface">
          Reorder Logs
        </h1>
        <p className="mt-1 text-body-sm font-body-sm text-on-surface-variant">
          Audit trail of every autonomous agent run — expand a row to see the full record.
        </p>
      </div>

      {!rows?.length ? (
        <p className="rounded-xl border border-dashed border-outline-variant bg-surface-container-lowest p-6 text-center text-body-sm text-on-surface-variant">
          No agent runs logged yet — run a scenario on the Agent tab.
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm">
          <div className="w-full overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-low text-label-xs font-label-xs uppercase tracking-wider text-on-surface-variant">
                  <th className="w-8 px-4 py-3" />
                  <th className="px-4 py-3 font-semibold">When</th>
                  <th className="px-4 py-3 font-semibold">Scenario</th>
                  <th className="px-4 py-3 font-semibold">SKU</th>
                  <th className="px-4 py-3 font-semibold">Trigger</th>
                  <th className="px-4 py-3 font-semibold">Decision</th>
                  <th className="px-4 py-3 text-center font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-body-md text-body-md">
                {rows.map((r, i) => {
                  const isOpen = open === i;
                  return (
                    <Fragment key={r.run_id}>
                      <tr
                        onClick={() => setOpen(isOpen ? null : i)}
                        className="group cursor-pointer transition-colors hover:bg-surface-container-low/60"
                      >
                        <td className="px-4 py-3.5 text-on-surface-variant">
                          <Icon
                            name={isOpen ? "expand_more" : "chevron_right"}
                            className="text-[18px]"
                          />
                        </td>
                        <td className="px-4 py-3.5 text-on-surface">
                          {new Date(r.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3.5 text-on-surface">{r.scenario}</td>
                        <td className="px-4 py-3.5 font-code-md text-code-md font-semibold text-secondary">
                          {r.sku}
                        </td>
                        <td className="px-4 py-3.5 text-on-surface">{r.trigger}</td>
                        <td className="px-4 py-3.5 text-on-surface">{r.decision_type}</td>
                        <td className="px-4 py-3.5 text-center">
                          <Pill tone={r.status === "escalated" ? "coral" : "green"}>
                            {r.status}
                          </Pill>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="bg-surface-container-low/30">
                          <td colSpan={7} className="px-6 py-4">
                            <div className="mb-2 font-code-sm text-code-sm text-on-surface-variant">
                              run: {r.run_id}
                            </div>
                            <LogDetail result={r.result} trace={r.trace} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
