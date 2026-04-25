import { useEffect, useRef, useState } from "react";

import type { BridgeState } from "@/lib/glance-bridge";

import { Icon } from "../icons";

const NOTICE_VISIBLE_MS = 5000;
const NOTICE_EXIT_MS = 180;

type VisibleNotice = {
  message: string;
  kind: string;
};

export function Notice({ state }: { state: BridgeState }) {
  const [notice, setNotice] = useState<VisibleNotice | null>(null);
  const [exiting, setExiting] = useState(false);
  const noticeRef = useRef<VisibleNotice | null>(null);
  const dismissTimerRef = useRef<number | null>(null);
  const removeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    noticeRef.current = notice;
  }, [notice]);

  useEffect(() => {
    const clearTimers = () => {
      if (dismissTimerRef.current !== null) {
        window.clearTimeout(dismissTimerRef.current);
        dismissTimerRef.current = null;
      }
      if (removeTimerRef.current !== null) {
        window.clearTimeout(removeTimerRef.current);
        removeTimerRef.current = null;
      }
    };

    const dismissNotice = () => {
      if (!noticeRef.current) {
        return;
      }
      setExiting(true);
      removeTimerRef.current = window.setTimeout(() => {
        setNotice(null);
        setExiting(false);
        removeTimerRef.current = null;
      }, NOTICE_EXIT_MS);
    };

    clearTimers();

    if (!state.statusMessage) {
      dismissNotice();
      return clearTimers;
    }

    const nextNotice = {
      message: state.statusMessage,
      kind: state.statusKind || "neutral",
    };
    noticeRef.current = nextNotice;
    setNotice(nextNotice);
    setExiting(false);
    dismissTimerRef.current = window.setTimeout(dismissNotice, NOTICE_VISIBLE_MS);

    return clearTimers;
  }, [state.statusMessage, state.statusKind, state.stateRevision]);

  if (!notice) {
    return null;
  }

  const normalizedMessage = notice.message.trim().toLowerCase();

  const iconName =
    notice.kind === "error"
      ? "alert-circle"
      : notice.kind === "success"
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
      className={`status-banner status-banner--${notice.kind}`}
      data-exiting={exiting ? "true" : undefined}
      role="status"
      aria-live="polite"
    >
      <span className="status-banner__icon">
        <Icon name={iconName} />
      </span>
      <span className="status-banner__text">{notice.message}</span>
    </div>
  );
}
