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
    <div className="grid gap-3 lg:grid-cols-3" aria-label="Keybinds">
      {rows.map((row) => (
        <button
          key={row.id}
          type="button"
          className="group min-w-0 rounded-2xl border border-border bg-card p-4 text-left transition-[background-color,border-color,box-shadow] hover:border-[color-mix(in_srgb,var(--accent)_36%,transparent)] hover:bg-white/[0.035] focus-visible:border-[color-mix(in_srgb,var(--accent)_52%,transparent)] focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_12%,transparent)]"
          onClick={() => onActivate(row.id)}
        >
          <span className="flex items-start justify-between gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-2xl border border-border bg-muted/30 text-muted-foreground transition-colors group-hover:text-[var(--accent-strong)]">
              <Icon name={row.icon ?? "key"} className="size-5" />
            </span>
            {row.active ? (
              <span className="inline-flex h-6 items-center gap-1.5 rounded-full border border-[color-mix(in_srgb,var(--accent)_42%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] px-2.5 font-mono text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
                <span className="size-1.5 rounded-full bg-current" />
                Recording
              </span>
            ) : null}
          </span>
          <span className="mt-4 block text-sm font-semibold text-foreground">
            {row.title}
          </span>
          <span className="mt-3 block">
            <KeyCap value={row.value} active={row.active} />
          </span>
        </button>
      ))}
    </div>
  );
}
