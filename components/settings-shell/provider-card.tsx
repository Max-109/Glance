import { Icon } from "@/components/icons";
import { cn } from "@/lib/utils";

import { StatusBadge, type StatusTone } from "./status-badge";

export function ProviderCard({
  eyebrow,
  title,
  icon,
  status,
  detail,
  selected,
  disabled,
  tooltip,
  onClick,
}: {
  eyebrow: string;
  title: string;
  icon: string;
  status: { tone: StatusTone; label: string };
  detail: string;
  selected: boolean;
  disabled?: boolean;
  tooltip?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={selected}
      aria-disabled={disabled || undefined}
      title={tooltip}
      className={cn(
        "group relative grid min-h-28 min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 rounded-2xl border bg-card p-4 text-left transition-[background-color,border-color,box-shadow,opacity]",
        selected
          ? "border-[color-mix(in_srgb,var(--accent)_50%,rgba(255,255,255,0.12))] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--accent)_9%,transparent),rgba(0,0,0,0.10))] shadow-[inset_0_1px_0_color-mix(in_srgb,var(--accent)_18%,transparent),0_18px_45px_-38px_var(--accent-glow)]"
          : "border-border hover:border-white/16 hover:bg-white/[0.035]",
        disabled && "opacity-45",
      )}
      onClick={() => {
        if (!disabled) onClick();
      }}
    >
      <span
        className={cn(
          "grid size-10 place-items-center rounded-2xl border border-border bg-muted/30 text-[var(--text-muted)] transition-colors",
          selected && "border-[color-mix(in_srgb,var(--accent)_45%,transparent)] bg-[color-mix(in_srgb,var(--accent)_18%,transparent)] text-[var(--accent-strong)]",
        )}
      >
        <Icon name={icon} className="size-5" />
      </span>
      <span className="min-w-0">
        <span className="block font-mono text-[0.72rem] font-bold tracking-[0.2em] text-[var(--text-muted)] uppercase">
          {eyebrow}
        </span>
        <span className="mt-1 block truncate text-base font-semibold leading-none text-[var(--text-strong)]">
          {title}
        </span>
      </span>
      <StatusBadge tone={status.tone} className="col-span-2">
        {status.label}
      </StatusBadge>
      <span className="col-span-2 truncate font-mono text-sm text-[var(--text-muted)]">
        {detail}
      </span>
    </button>
  );
}
