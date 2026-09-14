import { useState } from "react";
import { api } from "../api.js";
import { Modal } from "./Modal.jsx";
import { Icon } from "./Icon.jsx";

const field =
  "w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 font-code-md text-on-surface font-semibold outline-none focus:border-[#F0503C] focus:ring-2 focus:ring-[#F0503C]";
const label = "text-label-xs font-label-xs font-semibold uppercase text-on-surface-variant";

export function ReceivePOForm({ po, onClose, onCreated }) {
  const [confirmedQty, setConfirmedQty] = useState(po.qty); // default to fully receiving
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const confNum = parseInt(confirmedQty, 10) || 0;
  const delta = confNum - po.confirmed_qty;
  const nextStatus = confNum >= po.qty ? "confirmed" : confNum > 0 ? "partial" : "open";

  async function submit(e) {
    e.preventDefault();
    if (confNum < po.confirmed_qty) {
      setError(`Confirmed qty can't drop below already-received (${po.confirmed_qty}).`);
      return;
    }
    if (confNum > po.qty) {
      setError(`Confirmed qty can't exceed ordered qty (${po.qty}).`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.receivePurchaseOrder(po.po_id, confNum);
      onCreated();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="Receive Purchase Order"
      subtitle={`${po.po_id} · ${po.sku}`}
      icon="inventory"
      onClose={onClose}
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3 rounded-lg border border-outline-variant bg-surface-container-low/60 p-3 font-code-sm text-code-sm text-on-surface-variant">
          <div>Ordered: <strong className="text-on-surface">{po.qty}</strong></div>
          <div>Already received: <strong className="text-on-surface">{po.confirmed_qty}</strong></div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className={label}>Confirmed qty (total received)</label>
          <input
            className={field}
            type="number"
            min={po.confirmed_qty}
            max={po.qty}
            value={confirmedQty}
            onChange={(e) => setConfirmedQty(e.target.value)}
            required
          />
        </div>
        <p className="text-body-sm font-body-sm text-on-surface-variant">
          {delta > 0 ? (
            <>
              <strong className="text-tertiary">+{delta}</strong> unit
              {delta === 1 ? "" : "s"} will move into on-hand inventory. New status:{" "}
              <strong className="text-on-surface">{nextStatus}</strong>.
            </>
          ) : (
            <>No new stock will move (delta 0).</>
          )}
        </p>
        {error && (
          <div className="rounded-lg border border-error-container bg-error-container px-3 py-2 text-body-sm text-on-error-container">
            {error}
          </div>
        )}
        <div className="flex items-center justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-2 text-body-sm font-title-md text-on-surface transition-colors hover:bg-surface-container-low"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-body-sm font-title-md text-on-primary shadow-sm transition-all hover:bg-primary-container active:scale-[0.98] disabled:opacity-50"
          >
            <Icon name="check" className="text-[16px]" />
            {busy ? "Receiving…" : "Receive"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
