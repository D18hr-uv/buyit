import { Badge, Pill } from "./Badge.jsx";
import { Icon } from "./Icon.jsx";

const DECISION_TONE = {
  accept: "green",
  modify: "amber",
  reject: "gray",
  investigate: "blue",
  escalate: "coral",
  source_alternate: "amber",
  confirm_existing: "blue",
};

const DECISION_ICON = {
  accept: "check_circle",
  modify: "tune",
  reject: "block",
  investigate: "search",
  escalate: "priority_high",
  source_alternate: "swap_horiz",
  confirm_existing: "verified",
};

export function DecisionCard({ run }) {
  const d = run.decision;
  if (!d) return null;
  const v = run.validation;
  const action = run.action_result;
  const tone = DECISION_TONE[d.type] || "gray";

  return (
    <article className="flex flex-col gap-5 rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm md:p-6">
      {/* Status badges row */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/60 pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={tone} icon={DECISION_ICON[d.type]}>
            {d.type?.toUpperCase()}
          </Pill>
          {d.qty > 0 && (
            <span className="rounded-full border border-outline-variant bg-surface-container-low px-2.5 py-1 text-code-sm font-code-sm text-on-surface">
              qty: <strong className="font-semibold">{d.qty}</strong>
            </span>
          )}
          <span className="rounded-full border border-outline-variant bg-surface-container-low px-2.5 py-1 text-code-sm font-code-sm text-on-surface">
            confidence:{" "}
            <strong className="font-semibold text-tertiary">{d.confidence}</strong>
          </span>
        </div>
        <div className="flex items-center gap-2">
          {d.overridden && (
            <Pill tone="coral" icon="gpp_maybe">
              guardrail override
            </Pill>
          )}
          <Pill tone="gray" icon="sync">
            re-planned ×{run.iteration || 0}
          </Pill>
        </div>
      </div>

      {/* Rationale */}
      <div className="flex flex-col gap-2">
        <h4 className="text-title-md font-title-md text-on-surface">
          Agent Decision Rationale
        </h4>
        <p className="text-body-md font-body-md leading-relaxed text-on-surface">
          {d.rationale}
        </p>
      </div>

      {/* Factors + action-taken box */}
      {(d.factors?.length > 0 || action?.po_id || v?.checks?.length > 0) && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="flex flex-col justify-between rounded-lg border border-outline-variant/60 bg-surface-container-low/60 p-4 md:col-span-2">
            {d.factors?.length > 0 && (
              <>
                <span className="mb-2 text-label-xs font-label-xs uppercase tracking-wider text-on-surface-variant">
                  Evaluated Decision Factors
                </span>
                <ul className="space-y-2 text-body-sm font-body-sm text-on-surface">
                  {d.factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <Icon name="done" className="mt-0.5 text-[18px] text-tertiary" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}

            {v?.checks?.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2 border-t border-outline-variant/50 pt-3">
                <span className="w-full text-label-xs font-label-xs uppercase tracking-wide text-on-surface-variant">
                  Validation {v.acceptable ? "(passed)" : "(discrepancy detected)"}
                </span>
                {v.checks.map((c) => (
                  <Badge key={c.name} ok={c.passed}>
                    {c.name}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {action?.po_id && (
            <div className="flex flex-col justify-between rounded-lg border-2 border-primary/20 bg-surface-container-lowest p-4">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-label-xs font-label-xs uppercase text-on-surface-variant">
                    Action Taken
                  </span>
                  <span className="h-2 w-2 rounded-full bg-primary" />
                </div>
                <p className="mb-1 text-body-sm font-body-sm text-on-surface-variant">
                  Generated Purchase Order
                </p>
                <div className="mb-3 rounded-lg border border-surface-container-highest bg-surface-container p-2.5 text-center">
                  <span className="text-headline-sm font-code-md font-bold tracking-wide text-on-surface">
                    {action.po_id}
                  </span>
                </div>
                <div className="space-y-1 text-code-sm font-code-sm text-on-surface-variant">
                  <div className="flex justify-between">
                    <span>SKU:</span>
                    <span className="font-medium text-on-surface">{action.sku}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Vendor:</span>
                    <span className="font-medium text-on-surface">{action.vendor_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Qty × Price:</span>
                    <span className="font-medium text-on-surface">
                      {action.qty} × {action.unit_price}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Value:</span>
                    <span className="font-semibold text-tertiary">
                      {Math.round(action.order_value)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
