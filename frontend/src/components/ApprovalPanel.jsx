import { useState } from "react";

export function ApprovalPanel({ run, onApprove, onReject, busy }) {
  const [qty, setQty] = useState(run.decision?.qty ?? 0);
  const reasons = run.decision?.hitl_reasons || [];

  return (
    <div className="rounded-xl border-2 border-amber-300 bg-amber-50 p-4">
      <div className="flex items-center gap-2 text-amber-800">
        <span className="text-lg">🙋</span>
        <span className="font-semibold">Human approval required</span>
      </div>
      <ul className="mt-2 space-y-0.5 text-sm text-amber-900">
        {reasons.map((r, i) => (
          <li key={i}>• {r}</li>
        ))}
      </ul>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <label className="text-sm text-gray-700">
          Quantity:{" "}
          <input
            type="number"
            value={qty}
            onChange={(e) => setQty(parseInt(e.target.value || "0", 10))}
            className="w-24 rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </label>
        <button
          disabled={busy}
          onClick={() => onApprove(qty === run.decision?.qty ? undefined : qty)}
          className="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          Approve & execute
        </button>
        <button
          disabled={busy}
          onClick={onReject}
          className="rounded-lg bg-white px-4 py-1.5 text-sm font-semibold text-rose-600 ring-1 ring-rose-300 hover:bg-rose-50 disabled:opacity-50"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
