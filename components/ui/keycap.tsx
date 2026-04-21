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

  if (parts.length === 0) {
    return (
      <span className={`keycap-row${active ? " is-active" : ""}`}>
        <span className="keycap">—</span>
      </span>
    );
  }

  return (
    <span className={`keycap-row${active ? " is-active" : ""}`}>
      {parts.map((part, index) => (
        <span key={`${part}-${index}`} className="keycap-row__group">
          {index > 0 ? <span className="keycap-row__sep">+</span> : null}
          <span className="keycap">{prettyKey(part)}</span>
        </span>
      ))}
    </span>
  );
}
