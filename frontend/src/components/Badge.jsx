import { Icon } from "./Icon.jsx";

/** Criteria check pill — pass = green (tertiary), fail = red (error). */
export function Badge({ ok, children }) {
  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded-md px-2 py-1 text-label-xs font-label-xs font-medium " +
        (ok
          ? "bg-tertiary-fixed text-on-tertiary-fixed"
          : "bg-error-container text-on-error-container")
      }
    >
      <Icon name={ok ? "check" : "close"} className="text-[14px]" />
      {children}
    </span>
  );
}

/**
 * Status pill. Tone keys are kept stable so existing callers don't change.
 * Optional `icon` renders a leading Material Symbol.
 */
export function Pill({ tone = "gray", icon, children }) {
  const tones = {
    gray: "bg-surface-container text-on-surface-variant border border-outline-variant",
    coral: "bg-[#FEF2F2] text-[#991B1B] border border-[#FECACA]",
    blue: "bg-[#F0F9FF] text-[#075985] border border-[#BAE6FD]",
    amber: "bg-[#FFFBEB] text-[#92400E] border border-[#FDE68A]",
    orange: "bg-[#FFFBEB] text-[#92400E] border border-[#FDE68A]",
    green: "bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0]",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-label-xs font-label-xs font-semibold ${
        tones[tone] || tones.gray
      }`}
    >
      {icon && <Icon name={icon} className="text-[14px]" />}
      {children}
    </span>
  );
}
