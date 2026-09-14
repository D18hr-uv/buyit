import { useState } from "react";
import { Icon } from "./Icon.jsx";

export function ApprovalPanel({ run, onApprove, onReject, busy }) {
  const [qty, setQty] = useState(run.decision?.qty ?? 0);
  const reasons = run.decision?.hitl_reasons || [];

  return (
    <article className="flex flex-col gap-4 rounded-xl border border-[#FDE68A] border-l-4 border-l-[#F59E0B] bg-[#FFFBEB] p-5 shadow-sm">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div className="flex items-start gap-3">
          <div className="shrink-0 rounded-lg bg-[#FEF3C7] p-2 text-[#92400E]">
            <Icon name="warning" className="text-[24px]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-headline-sm font-headline-sm text-[#92400E]">
                Human-in-the-Loop Gate Triggered
              </h3>
              <span className="rounded-full bg-[#FDE68A] px-2 py-0.5 text-label-xs font-label-xs font-semibold text-[#78350F]">
                Action Required
              </span>
            </div>
            <p className="mt-0.5 text-body-md font-body-md text-[#92400E]/90">
              Autonomous execution halted pending explicit authorization.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 items-center gap-4 pt-2 md:grid-cols-12">
        <div className="space-y-2 md:col-span-7">
          <span className="text-label-xs font-label-xs font-semibold uppercase tracking-wider text-[#92400E]">
            Audit Exception Reasons
          </span>
          <ul className="space-y-1.5 text-body-sm font-body-sm text-[#92400E]">
            {reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#D97706]" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-[#FDE68A] bg-white p-3.5 shadow-sm md:col-span-5">
          <div className="flex items-center justify-between">
            <label
              htmlFor="order-qty"
              className="text-label-xs font-label-xs font-semibold text-on-surface-variant"
            >
              AUTHORIZED QUANTITY
            </label>
            <span className="text-code-sm font-code-sm text-on-surface-variant">
              Recommended: {run.decision?.qty ?? 0}
            </span>
          </div>
          <div className="relative">
            <input
              id="order-qty"
              type="number"
              value={qty}
              onChange={(e) => setQty(parseInt(e.target.value || "0", 10))}
              className="w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 font-code-md font-semibold text-on-surface outline-none focus:border-[#F0503C] focus:ring-2 focus:ring-[#F0503C]"
            />
            <span className="absolute right-3 top-2.5 text-code-sm text-on-surface-variant">
              units
            </span>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <button
              disabled={busy}
              onClick={() => onApprove(qty === run.decision?.qty ? undefined : qty)}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#006947] px-3 py-2 text-body-sm font-title-md text-white shadow-sm transition-colors hover:bg-[#005236] active:scale-[0.98] disabled:opacity-50"
            >
              <Icon name="check" className="text-[16px]" />
              Approve &amp; execute
            </button>
            <button
              disabled={busy}
              onClick={onReject}
              className="flex items-center justify-center gap-1 rounded-lg border border-[#EF4444] bg-surface-container-lowest px-3 py-2 text-body-sm font-title-md text-[#EF4444] transition-colors hover:bg-[#FEF2F2] active:scale-[0.98] disabled:opacity-50"
            >
              <Icon name="close" className="text-[16px]" />
              Reject
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
