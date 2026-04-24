import { Icon } from "@/components/icons";
import { cn } from "@/lib/utils";

export function VoicePreviewButton({
  active,
  disabled,
  onClick,
}: {
  active: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        "flex h-12 shrink-0 items-center gap-3 rounded-2xl border px-4 text-sm font-semibold transition-[background-color,border-color,color,opacity,transform] active:scale-95 focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_12%,transparent)]",
        active
          ? "border-[color-mix(in_srgb,var(--accent)_46%,transparent)] bg-[color-mix(in_srgb,var(--accent)_14%,transparent)] text-[var(--accent-strong)]"
          : "border-white/10 bg-card text-[var(--text-strong)] hover:bg-white/[0.04]",
        disabled && "cursor-not-allowed opacity-45 active:scale-100",
      )}
      disabled={disabled}
      aria-label={active ? "Stop voice preview" : "Preview current voice"}
      onClick={onClick}
    >
      <span
        className={cn(
          "grid size-8 place-items-center rounded-xl border transition-colors",
          active
            ? "border-[color-mix(in_srgb,var(--accent)_40%,transparent)] bg-[color-mix(in_srgb,var(--accent)_16%,transparent)]"
            : "border-white/10 bg-white/[0.035] text-[var(--text-muted)]",
        )}
      >
        <Icon name={active ? "stop" : "play"} className="size-4" />
      </span>
      <span>{active ? "Stop" : "Preview"}</span>
    </button>
  );
}
