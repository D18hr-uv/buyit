import { DecisionCard } from "./DecisionCard.jsx";
import { ApprovalPanel } from "./ApprovalPanel.jsx";
import { Timeline } from "./Timeline.jsx";
import { Icon } from "./Icon.jsx";

/** Slide-over panel that runs a scenario in-context over any dashboard. */
export function AgentDrawer({ run, busy, subtitle, onApprove, onReject, onClose }) {
  return (
    <div className="fixed inset-0 z-[100] flex justify-end bg-inverse-surface/40" onClick={onClose}>
      <div
        className="flex h-full w-full max-w-2xl flex-col bg-background shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-outline-variant bg-surface px-5 py-3">
          <div className="flex items-center gap-2.5">
            <Icon name="smart_toy" className="text-[22px] text-primary" />
            <div>
              <h3 className="text-headline-sm font-headline-sm text-on-surface">Agent Run</h3>
              {subtitle && (
                <p className="font-code-sm text-code-sm text-on-surface-variant">{subtitle}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container-low"
            aria-label="Close"
          >
            <Icon name="close" className="text-[20px]" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {busy && !run && (
            <div className="flex items-center justify-center gap-2 rounded-xl border border-outline-variant bg-surface-container-lowest p-6 text-body-sm text-on-surface-variant shadow-sm">
              <Icon name="progress_activity" className="animate-spin text-[18px] text-primary" />
              Agent is investigating…
            </div>
          )}
          {run && (
            <>
              <DecisionCard run={run} />
              {run.status === "awaiting_approval" && (
                <ApprovalPanel run={run} busy={busy} onApprove={onApprove} onReject={onReject} />
              )}
              <article className="flex flex-col gap-6 rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm">
                <div className="flex items-center gap-2.5 border-b border-outline-variant/60 pb-3">
                  <Icon name="timeline" className="text-[22px] text-primary" />
                  <h3 className="text-headline-sm font-headline-sm text-on-surface">
                    Reasoning &amp; Execution Trace
                  </h3>
                </div>
                <Timeline trace={run.trace} />
              </article>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
