import { useState } from "react";
import { api } from "../api.js";
import { Modal } from "./Modal.jsx";
import { Icon } from "./Icon.jsx";

const field =
  "w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-body-sm font-body-sm text-on-surface outline-none focus:border-[#F0503C] focus:ring-2 focus:ring-[#F0503C]";
const label = "text-label-xs font-label-xs font-semibold uppercase text-on-surface-variant";

export function CreateOrderForm({ skus = [], onClose, onCreated }) {
  const [sku, setSku] = useState(skus[0]?.sku || "");
  const [qty, setQty] = useState(50);
  const [status, setStatus] = useState("open");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createClientOrder({ sku, qty: parseInt(qty, 10), status });
      onCreated();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="New Client Order"
      subtitle="Record incoming customer demand."
      icon="shopping_cart"
      onClose={onClose}
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className={label}>SKU</label>
          <select className={field} value={sku} onChange={(e) => setSku(e.target.value)} required>
            {skus.map((s) => (
              <option key={s.sku} value={s.sku}>
                {s.sku} — {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className={label}>Quantity</label>
            <input
              className={field}
              type="number"
              min="1"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className={label}>Status</label>
            <select className={field} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="open">open</option>
              <option value="fulfilled">fulfilled</option>
            </select>
          </div>
        </div>
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
            <Icon name="add" className="text-[16px]" />
            {busy ? "Creating…" : "Create order"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
