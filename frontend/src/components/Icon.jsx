/** Material Symbols Outlined icon. `name` is the ligature, e.g. "check_circle". */
export function Icon({ name, className = "" }) {
  return (
    <span className={`material-symbols-outlined ${className}`} aria-hidden="true">
      {name}
    </span>
  );
}
