export function Keybinds({
  rows,
  onActivate,
}: {
  rows: Array<{ id: string; title: string; value: string; active: boolean }>;
  onActivate: (fieldName: string) => void;
}) {
  return (
    <div className="shortcut-list" aria-label="Keybinds">
      {rows.map((row) => (
        <button
          key={row.id}
          type="button"
          className={`shortcut-row${row.active ? " is-capturing" : ""}`}
          onClick={() => onActivate(row.id)}
        >
          <span className="shortcut-row__label">{row.title}</span>
          <span className="shortcut-row__value" translate="no">
            {row.active ? "PRESS KEYS" : row.value}
          </span>
        </button>
      ))}
    </div>
  );
}
