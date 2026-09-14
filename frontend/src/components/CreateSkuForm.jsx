import { useState } from "react";
import { api } from "../api.js";
import { Modal } from "./Modal.jsx";
import { Icon } from "./Icon.jsx";

const field =
  "w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-body-sm font-body-sm text-on-surface outline-none focus:border-[#F0503C] focus:ring-2 focus:ring-[#F0503C]";
const label = "text-label-xs font-label-xs font-semibold uppercase text-on-surface-variant";

export function CreateSkuForm({ categories = [], onClose, onCreated }) {
  const [form, setForm] = useState({
    sku: "",
    name: "",
    category: categories[0] || "",
    unit_cost: "",
    on_hand: 0,
    safety_stock: 0,
    reorder_point: 0,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createInventoryItem({
        sku: form.sku.trim(),
        name: form.name.trim(),
        category: form.category.trim(),
        unit_cost: parseFloat(form.unit_cost),
        on_hand: parseInt(form.on_hand, 10) || 0,
        safety_stock: parseInt(form.safety_stock, 10) || 0,
        reorder_point: parseInt(form.reorder_point, 10) || 0,
      });
      onCreated();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="New SKU"
      subtitle="Add a product to the catalog and inventory."
      icon="inventory_2"
      onClose={onClose}
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className={label}>SKU code</label>
            <input
              className={field + " font-code-md"}
              placeholder="SKU-XXXX"
              value={form.sku}
              onChange={set("sku")}
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className={label}>Category</label>
            <input
              className={field}
              list="sku-categories"
              placeholder="e.g. Pantry"
              value={form.category}
              onChange={set("category")}
              required
            />
            <datalist id="sku-categories">
              {categories.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className={label}>Product name</label>
          <input
            className={field}
            placeholder="e.g. Organic Almonds 500g"
            value={form.name}
            onChange={set("name")}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className={label}>Unit cost</label>
            <input
              className={field}
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={form.unit_cost}
              onChange={set("unit_cost")}
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className={label}>On hand</label>
            <input
              className={field}
              type="number"
              min="0"
              value={form.on_hand}
              onChange={set("on_hand")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className={label}>Safety stock</label>
            <input
              className={field}
              type="number"
              min="0"
              value={form.safety_stock}
              onChange={set("safety_stock")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className={label}>Reorder point</label>
            <input
              className={field}
              type="number"
              min="0"
              value={form.reorder_point}
              onChange={set("reorder_point")}
            />
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
            {busy ? "Creating…" : "Create SKU"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
