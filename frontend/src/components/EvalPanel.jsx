import { useState } from "react";
import { api } from "../api.js";
import { Badge, Pill } from "./Badge.jsx";

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

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={run}
          disabled={busy}
          className="rounded-lg bg-[#f0503c] px-4 py-2 text-sm font-semibold text-white hover:bg-[#d8442f] disabled:opacity-50"
        >
          {busy ? "Running evaluation…" : "Run evaluation suite"}
        </button>
        {report && (
          <Pill tone={report.summary.passed === report.summary.total ? "green" : "amber"}>
            {report.summary.passed}/{report.summary.total} scenarios passed
          </Pill>
        )}
      </div>

      {report && (
        <div className="space-y-3">
          {report.results.map((r) => (
            <div key={r.id} className="rounded-xl border border-gray-200 bg-white p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-semibold">{r.id}</span>
                  <span className="text-xs text-gray-500">
                    → {r.decision} {r.qty ? `(${r.qty})` : ""}
                  </span>
                </div>
                <Pill tone={r.passed ? "green" : "coral"}>{r.passed ? "PASS" : "FAIL"}</Pill>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {Object.entries(r.checks).map(([k, ok]) => (
                  <Badge key={k} ok={ok}>
                    {CHECK_LABELS[k] || k}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
