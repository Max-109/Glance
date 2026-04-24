import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type StatusTone = "accent" | "neutral" | "warning" | "danger" | "disabled";

const toneClass: Record<StatusTone, string> = {
  accent:
    "border-[color-mix(in_srgb,var(--accent)_42%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--accent-strong)]",
  neutral:
    "border-white/10 bg-white/[0.045] text-[color-mix(in_srgb,var(--text-muted)_88%,white)]",
  warning:
    "border-amber-400/30 bg-amber-400/10 text-amber-200",
  danger:
    "border-red-400/30 bg-red-400/10 text-red-200",
  disabled:
    "border-white/8 bg-white/[0.035] text-[var(--text-faint)]",
};

export function StatusBadge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: StatusTone;
  children: string;
  className?: string;
}) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "h-6 gap-1.5 rounded-full px-2.5 font-mono text-[0.68rem] font-bold tracking-[0.16em] uppercase",
        toneClass[tone],
        className,
      )}
    >
      <span className="size-1.5 rounded-full bg-current opacity-75" />
      {children}
    </Badge>
  );
}
