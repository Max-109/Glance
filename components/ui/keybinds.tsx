import { cn } from "@/lib/utils";

import { Icon } from "../icons";

import { KeyCap } from "./keycap";

export function Keybinds({
  rows,
  onActivate,
}: {
  rows: Array<{
    id: string;
    title: string;
    description?: string;
    value: string;
    active: boolean;
    icon?: string;
  }>;
  onActivate: (fieldName: string) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3" aria-label="Keyboard shortcuts">
      {rows.map((row) => (
        <button
          key={row.id}
          type="button"
          aria-label={`Change ${row.title} shortcut`}
          className={cn(
            "group relative min-w-0 overflow-hidden rounded-2xl border bg-card p-5 text-left transition-[background-color,border-color,box-shadow,color] focus-visible:border-[color-mix(in_srgb,var(--accent)_56%,transparent)] focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_14%,transparent)]",
            row.active
              ? "border-[color-mix(in_srgb,var(--accent)_48%,rgba(255,255,255,0.1))] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--accent)_8%,transparent),rgba(0,0,0,0.12)),var(--card)] shadow-[inset_0_1px_0_color-mix(in_srgb,var(--accent)_18%,transparent),0_18px_46px_-38px_var(--accent-glow)]"
              : "border-border hover:border-[color-mix(in_srgb,var(--accent)_34%,transparent)] hover:bg-white/[0.035]",
          )}
          onClick={() => onActivate(row.id)}
        >
          <span className="flex min-w-0 items-start justify-between gap-3">
            <span
              className={cn(
                "grid size-11 shrink-0 place-items-center rounded-2xl border border-border bg-white/[0.035] text-muted-foreground transition-colors group-hover:text-[var(--accent-strong)]",
                row.active &&
                  "border-[color-mix(in_srgb,var(--accent)_42%,transparent)] bg-[color-mix(in_srgb,var(--accent)_14%,transparent)] text-[var(--accent-strong)]",
              )}
            >
              <Icon name={row.icon ?? "key"} className="size-5" aria-hidden="true" />
            </span>
            {row.active ? (
              <span className="inline-flex h-6 shrink-0 items-center gap-1.5 rounded-full border border-[color-mix(in_srgb,var(--accent)_42%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] px-2.5 font-mono text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
                <span className="size-1.5 rounded-full bg-current" />
                Recording
              </span>
            ) : null}
          </span>

          <span className="mt-5 block min-w-0">
            <span className="block truncate text-base font-semibold text-foreground">
              {row.title}
            </span>
            {row.description ? (
              <span className="mt-1.5 block truncate text-sm text-[var(--text-muted)]">
                {row.description}
              </span>
            ) : null}
          </span>

          <span className="mt-5 flex min-h-12 min-w-0 items-center">
            <KeyCap value={row.value} active={row.active} size="lg" />
          </span>

          <span className="mt-5 flex items-center justify-between gap-3 border-t border-white/10 pt-4">
            <span className="truncate font-mono text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--text-faint)]">
              Shortcut
            </span>
            <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.035] px-2.5 py-1 text-xs font-semibold text-[var(--text-muted)] transition-[background-color,border-color,color] group-hover:border-[color-mix(in_srgb,var(--accent)_30%,transparent)] group-hover:text-[var(--accent-strong)]">
              Change
            </span>
          </span>
        </button>
      ))}
    </div>
  );
}
