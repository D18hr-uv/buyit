import { useState } from "react";
import { api } from "../api.js";
import { Badge, Pill } from "./Badge.jsx";
import { Icon } from "./Icon.jsx";

const CHECK_LABELS = {
  decision_correct: "Decision correct",
  obtained_info: "Obtained info",
  respected_constraints: "Respected constraints",
  appropriate_action: "Right action",
  validated_result: "Validated result",
  paused_for_human: "Paused for human",
  recovered_from_failure: "Recovered on failure",
};

export function EvalPanel() {
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      setReport(await api.runEval());
    } finally {
      setBusy(false);
    }
  }

  const allPassed = report && report.summary.passed === report.summary.total;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 border-b border-outline-variant pb-2 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-headline-lg font-headline-lg tracking-tight text-on-surface">
              Agent Evaluation Suite
            </h1>
            <span className="rounded-full bg-tertiary-fixed px-2 py-0.5 text-code-sm font-code-sm font-semibold text-on-tertiary-fixed">
              Live Sandbox
            </span>
          </div>
          <p className="mt-1 max-w-2xl text-body-md font-body-md text-on-surface-variant">
            Automated test scenarios benchmarked against business rules and procurement
            guardrails.
          </p>
        </div>
        <button
          onClick={run}
          disabled={busy}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary-container px-4 py-2 text-title-md font-title-md text-on-primary shadow transition-all hover:bg-primary active:scale-[0.98] disabled:opacity-50"
        >
          <Icon name="play_arrow" className="text-[18px]" />
          {busy ? "Running evaluation…" : "Run evaluation suite"}
        </button>
      </div>

      {/* Summary banner */}
      {report && (
        <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <Pill tone={allPassed ? "green" : "amber"} icon={allPassed ? "verified" : "warning"}>
              {report.summary.passed}/{report.summary.total} scenarios passed
            </Pill>
            <span className="text-label-xs font-label-xs uppercase tracking-wider text-on-surface-variant">
              {allPassed ? "Benchmark suite verified" : "Review failing scenarios"}
            </span>
          </div>
        </section>
      )}

      {/* Per-scenario cards */}
      {report && (
        <div className="space-y-4">
          <h2 className="flex items-center gap-2 text-headline-sm font-headline-sm tracking-tight text-on-surface">
            Executed Test Scenarios
            <span className="text-body-sm font-body-sm font-normal text-on-surface-variant">
              (Deterministic verification)
            </span>
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {report.results.map((r) => (
              <div
                key={r.id}
                className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm transition-shadow hover:shadow"
              >
                <div className="flex flex-col justify-between gap-3 border-b border-outline-variant pb-4 md:flex-row md:items-start">
                  <div className="flex items-center gap-3">
                    <span className="font-code-md text-code-md font-bold text-primary">
                      {r.id}
                    </span>
                    <span className="text-on-surface-variant">•</span>
                    <span className="font-code-sm text-code-sm text-on-surface-variant">
                      Decision Target:{" "}
                      <strong className="font-semibold text-on-surface">
                        {r.decision?.toUpperCase()}
                        {r.qty ? ` (${r.qty} units)` : ""}
                      </strong>
                    </span>
                  </div>
                  <Pill tone={r.passed ? "green" : "coral"} icon={r.passed ? "check" : "close"}>
                    {r.passed ? "STATUS: PASS" : "STATUS: FAIL"}
                  </Pill>
                </div>
                <div className="flex flex-wrap gap-2 pt-3.5">
                  {Object.entries(r.checks).map(([k, ok]) => (
                    <Badge key={k} ok={ok}>
                      {CHECK_LABELS[k] || k}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
