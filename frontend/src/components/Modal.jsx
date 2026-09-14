import { Icon } from "./Icon.jsx";

/** Centered modal dialog with an overlay. */
export function Modal({ title, subtitle, icon, onClose, children }) {
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-inverse-surface/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-outline-variant bg-surface-container-lowest shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-outline-variant px-5 py-4">
          <div className="flex items-start gap-3">
            {icon && (
              <div className="rounded-lg bg-primary/10 p-2 text-primary">
                <Icon name={icon} className="text-[20px]" />
              </div>
            )}
            <div>
              <h3 className="text-headline-sm font-headline-sm text-on-surface">{title}</h3>
              {subtitle && (
                <p className="mt-0.5 text-body-sm font-body-sm text-on-surface-variant">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container-low"
            aria-label="Close"
          >
            <Icon name="close" className="text-[20px]" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}
