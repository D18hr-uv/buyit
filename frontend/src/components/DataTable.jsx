/**
 * Stitch-styled data table.
 *   columns = [{ key, label, fmt?, align?, mono? }]
 *   title/badge/subtitle = optional header region
 *   stats = optional array of { label, value, tone?, hint? } summary cards
 */
export function DataTable({
  columns,
  rows,
  empty = "No records.",
  title,
  subtitle,
  badge,
  stats,
  headerAction,
}) {
  return (
    <div className="flex flex-col gap-6">
      {(title || stats) && (
        <div className="flex flex-col gap-4">
          {title && (
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-display-lg font-headline-lg font-bold tracking-tight text-on-surface">
                    {title}
                  </h1>
                  {badge && (
                    <span className="rounded-full border border-tertiary-fixed-dim bg-tertiary-fixed px-2.5 py-0.5 text-label-xs font-label-xs text-on-tertiary-fixed">
                      {badge}
                    </span>
                  )}
                </div>
                {subtitle && (
                  <p className="mt-1 text-body-sm font-body-sm text-on-surface-variant">
                    {subtitle}
                  </p>
                )}
              </div>
              {headerAction}
            </div>
          )}
          {stats?.length > 0 && (
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {stats.map((s) => (
                <div
                  key={s.label}
                  className="relative overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest p-4 shadow-sm"
                >
                  {s.tone === "primary" && (
                    <div className="absolute bottom-0 left-0 top-0 w-1 bg-primary" />
                  )}
                  <div className="flex items-center justify-between">
                    <span
                      className={
                        "text-label-xs font-label-xs uppercase " +
                        (s.tone === "primary"
                          ? "font-semibold text-primary"
                          : "text-on-surface-variant")
                      }
                    >
                      {s.label}
                    </span>
                    {s.icon && (
                      <div className="rounded-lg bg-surface-container p-1.5 text-secondary">
                        <span className="material-symbols-outlined text-[18px]">
                          {s.icon}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span
                      className={
                        "text-display-lg font-headline-lg font-bold " +
                        (s.tone === "primary" ? "text-primary" : "text-on-surface")
                      }
                    >
                      {s.value}
                    </span>
                    {s.hint && (
                      <span className="text-label-xs font-label-xs text-on-surface-variant">
                        {s.hint}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </section>
          )}
        </div>
      )}

      {!rows?.length ? (
        <p className="rounded-xl border border-dashed border-outline-variant bg-surface-container-lowest p-6 text-center text-body-sm text-on-surface-variant">
          {empty}
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm">
          <div className="w-full overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="sticky top-0 z-10 border-b border-outline-variant bg-surface-container-low text-label-xs font-label-xs uppercase tracking-wider text-on-surface-variant">
                  {columns.map((c) => (
                    <th
                      key={c.key}
                      scope="col"
                      className={
                        "px-4 py-3 font-semibold " +
                        (c.align === "right"
                          ? "text-right"
                          : c.align === "center"
                          ? "text-center"
                          : "")
                      }
                    >
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-body-md text-body-md">
                {rows.map((row, i) => (
                  <tr
                    key={i}
                    className="group transition-colors hover:bg-surface-container-low/60"
                  >
                    {columns.map((c) => (
                      <td
                        key={c.key}
                        className={
                          "px-4 py-3.5 " +
                          (c.align === "right"
                            ? "text-right "
                            : c.align === "center"
                            ? "text-center "
                            : "") +
                          (c.mono
                            ? "font-code-md text-code-md text-on-surface"
                            : "text-on-surface")
                        }
                      >
                        {c.fmt ? c.fmt(row[c.key], row) : String(row[c.key] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
