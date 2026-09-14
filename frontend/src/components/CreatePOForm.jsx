import { useState } from "react";
import { api } from "../api.js";
import { Modal } from "./Modal.jsx";
import { Icon } from "./Icon.jsx";

const field =
  "w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-body-sm font-body-sm text-on-surface outline-none focus:border-[#F0503C] focus:ring-2 focus:ring-[#F0503C]";
const label = "text-label-xs font-label-xs font-semibold uppercase text-on-surface-variant";

export function CreatePOForm({ skus = [], vendors = [], onClose, onCreated }) {
  const [sku, setSku] = useState(skus[0]?.sku || "");
  const [vendorId, setVendorId] = useState(vendors[0]?.vendor_id || "");
  const [qty, setQty] = useState(100);
  const [unitPrice, setUnitPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = { sku, vendor_id: vendorId, qty: parseInt(qty, 10) };
      if (unitPrice !== "") body.unit_price = parseFloat(unitPrice);
      await api.createPurchaseOrder(body);
      onCreated();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="New Purchase Order"
      subtitle="Manually raise a PO to a vendor."
      icon="local_shipping"
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
        <div className="flex flex-col gap-1.5">
          <label className={label}>Vendor</label>
          <select
            className={field}
            value={vendorId}
            onChange={(e) => setVendorId(e.target.value)}
            required
          >
            {vendors.map((v) => (
              <option key={v.vendor_id} value={v.vendor_id}>
                {v.vendor_id} — {v.name}
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
            <label className={label}>Unit price</label>
            <input
              className={field}
              type="number"
              step="0.01"
              min="0"
              placeholder="auto"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
            />
          </div>
        </div>
        <p className="text-body-sm font-body-sm text-on-surface-variant">
          Leave unit price blank to use the vendor's contracted price.
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
            <Icon name="add" className="text-[16px]" />
            {busy ? "Creating…" : "Create PO"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
