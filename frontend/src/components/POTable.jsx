import { Pill } from "./Badge.jsx";

const STATUS_TONE = {
  open: "blue",
  confirmed: "green",
  partial: "amber",
  closed: "gray",
  cancelled: "gray",
};

export function POTable({ pos }) {
  if (!pos?.length) return <p className="text-sm text-gray-500">No purchase orders yet.</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-3 py-2">PO</th>
            <th className="px-3 py-2">SKU</th>
            <th className="px-3 py-2">Vendor</th>
            <th className="px-3 py-2">Qty</th>
            <th className="px-3 py-2">Confirmed</th>
            <th className="px-3 py-2">Value</th>
            <th className="px-3 py-2">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {pos.map((p) => (
            <tr key={p.po_id} className="hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs">{p.po_id}</td>
              <td className="px-3 py-2">{p.sku}</td>
              <td className="px-3 py-2">{p.vendor_id}</td>
              <td className="px-3 py-2">{p.qty}</td>
              <td className="px-3 py-2">{p.confirmed_qty}</td>
              <td className="px-3 py-2">{Math.round(p.order_value)}</td>
              <td className="px-3 py-2">
                <Pill tone={STATUS_TONE[p.status] || "gray"}>{p.status}</Pill>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
