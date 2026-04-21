import type { BridgeState } from "@/lib/glance-bridge";

import { Icon } from "../icons";

export function Notice({ state }: { state: BridgeState }) {
  if (!state.statusMessage) {
    return null;
  }

  const normalizedMessage = state.statusMessage.trim().toLowerCase();

  const iconName =
    state.statusKind === "error"
      ? "alert-circle"
      : state.statusKind === "success"
        ? "check"
        : normalizedMessage.includes("mic") || normalizedMessage.includes("listening")
          ? "mic"
          : normalizedMessage.includes("speaker") ||
              normalizedMessage.includes("voice") ||
              normalizedMessage.includes("playing") ||
              normalizedMessage.includes("preview")
            ? "speaker"
            : normalizedMessage.includes("audio")
              ? "audio"
              : normalizedMessage.includes("keybind") || normalizedMessage.includes("press")
                ? "key"
                : "info";

  return (
    <div
      className={`status-banner status-banner--${state.statusKind || "neutral"}`}
      role="status"
      aria-live="polite"
    >
      <span className="status-banner__icon">
        <Icon name={iconName} />
      </span>
      <span className="status-banner__text">{state.statusMessage}</span>
    </div>
  );
}
