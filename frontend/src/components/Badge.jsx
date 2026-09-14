export function Badge({ ok, children }) {
  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium " +
        (ok
          ? "bg-emerald-100 text-emerald-700"
          : "bg-rose-100 text-rose-700")
      }
    >
      <span className={ok ? "text-emerald-600" : "text-rose-600"}>{ok ? "✓" : "✕"}</span>
      {children}
    </span>
  );
}

export function Pill({ tone = "gray", children }) {
  const tones = {
    gray: "bg-gray-100 text-gray-700",
    coral: "bg-[#fde7e3] text-[#c23b28]",
    blue: "bg-blue-100 text-blue-700",
    amber: "bg-amber-100 text-amber-800",
    green: "bg-emerald-100 text-emerald-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}
