import { Icon } from "../icons";

import { KeyCap } from "./keycap";

export function Keybinds({
  rows,
  onActivate,
}: {
  rows: Array<{
    id: string;
    title: string;
    value: string;
    active: boolean;
    icon?: string;
  }>;
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
          <span className="shortcut-row__icon">
            <Icon name={row.icon ?? "key"} />
          </span>
          <span className="shortcut-row__label">{row.title}</span>
          {row.active ? (
            <span className="shortcut-row__capturing" translate="no">
              <span className="shortcut-row__capturing-dot" />
              Press keys
            </span>
          ) : (
            <KeyCap value={row.value} />
          )}
        </button>
      ))}
    </div>
  );
}
