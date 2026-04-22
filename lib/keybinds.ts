function normalizeKey(key: string): string | null {
  if (!key) {
    return null;
  }

  const specialKeys: Record<string, string> = {
    ArrowUp: "UP",
    ArrowDown: "DOWN",
    ArrowLeft: "LEFT",
    ArrowRight: "RIGHT",
    Escape: "ESC",
    Enter: "ENTER",
    Backspace: "BACKSPACE",
    Tab: "TAB",
    Delete: "DELETE",
    " ": "SPACE",
  };

  if (specialKeys[key]) {
    return specialKeys[key];
  }

  if (key.length === 1) {
    return key.toUpperCase();
  }

  if (key.startsWith("F") && Number.isFinite(Number(key.slice(1)))) {
    return key.toUpperCase();
  }

  return key.toUpperCase();
}

export function eventToKeybind(event: KeyboardEvent): string | null {
  const normalizedKey = normalizeKey(event.key);
  if (
    !normalizedKey ||
    ["SHIFT", "CONTROL", "ALT", "META"].includes(normalizedKey)
  ) {
    return null;
  }

  const parts: string[] = [];
  if (event.ctrlKey) {
    parts.push("CTRL");
  }
  if (event.altKey) {
    parts.push("ALT");
  }
  if (event.shiftKey) {
    parts.push("SHIFT");
  }
  if (event.metaKey) {
    parts.push("CMD");
  }
  parts.push(normalizedKey);
  return parts.join("+");
}
