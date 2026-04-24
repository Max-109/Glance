import { cn } from "@/lib/utils";

const KEY_LABELS: Record<string, string> = {
  CMD: "⌘",
  COMMAND: "⌘",
  META: "⌘",
  SUPER: "⌘",
  CTRL: "⌃",
  CONTROL: "⌃",
  ALT: "⌥",
  OPTION: "⌥",
  SHIFT: "⇧",
  ENTER: "↵",
  RETURN: "↵",
  TAB: "⇥",
  ESC: "⎋",
  ESCAPE: "⎋",
  SPACE: "␣",
  BACKSPACE: "⌫",
  DELETE: "⌦",
  UP: "↑",
  DOWN: "↓",
  LEFT: "←",
  RIGHT: "→",
};

function prettyKey(part: string): string {
  const upper = part.trim().toUpperCase();
  return KEY_LABELS[upper] ?? upper;
}

export function KeyCap({ value, active = false }: { value: string; active?: boolean }) {
  const parts = value
    .replace(/\s+/g, "")
    .split(/[+\-]/)
    .filter(Boolean);
  const keys = parts.length > 0 ? parts : ["-"];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground",
        active && "text-[var(--accent-strong)]",
      )}
      translate="no"
    >
      {keys.map((part, index) => (
        <span key={`${part}-${index}`} className="inline-flex items-center gap-1.5">
          {index > 0 ? <span className="opacity-45">+</span> : null}
          <span
            className={cn(
              "grid min-w-8 place-items-center rounded-xl border border-border bg-background px-2.5 py-1.5 text-sm font-semibold text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]",
              active &&
                "border-[color-mix(in_srgb,var(--accent)_48%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--accent-strong)]",
            )}
          >
            {prettyKey(part)}
          </span>
        </span>
      ))}
    </span>
  );
}
