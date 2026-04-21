import { useEffect, useRef, useState } from "react";

type ActivityMarkState =
  | "idle"
  | "listening"
  | "processing"
  | "speaking"
  | "ready"
  | "error";

const ACTIVITY_MARK_SEGMENTS = [
  { key: "west", x: 4, y: 11, width: 5, height: 14 },
  { key: "north", x: 11, y: 4, width: 14, height: 5 },
  { key: "east", x: 27, y: 11, width: 5, height: 14 },
  { key: "south", x: 11, y: 27, width: 14, height: 5 },
] as const;

const ACTIVITY_MARK_ANIMATION_INTERVAL_MS: Partial<
  Record<ActivityMarkState, number>
> = {
  listening: 420,
  processing: 560,
  speaking: 420,
  ready: 420,
};

const ACTIVITY_MARK_READY_FLASH_MS = 520;
const ACTIVITY_MARK_ERROR_FLASH_MS = 1400;
const ACTIVITY_MARK_ERROR_TOKENS = ["failed", "unavailable", "error"];

function normalizeActivityMarkState(state: string): ActivityMarkState {
  if (
    state === "listening" ||
    state === "processing" ||
    state === "speaking" ||
    state === "ready" ||
    state === "error"
  ) {
    return state;
  }
  return "idle";
}

function messageNeedsErrorFlash(message?: string) {
  const normalizedMessage = message?.trim().toLowerCase() || "";
  return ACTIVITY_MARK_ERROR_TOKENS.some((token) => normalizedMessage.includes(token));
}

function getActivityMarkSegmentOpacities(
  state: ActivityMarkState,
  frame: number,
): [number, number, number, number] {
  const pulseOpacity = frame ? 1 : 0.38;
  const completedOpacity = 0.9;
  const idleOpacity = 0.56;
  const inactiveOpacity = 0.24;

  if (state === "listening") {
    return [pulseOpacity, inactiveOpacity, inactiveOpacity, inactiveOpacity];
  }
  if (state === "processing") {
    return [completedOpacity, pulseOpacity, inactiveOpacity, inactiveOpacity];
  }
  if (state === "speaking") {
    return [completedOpacity, completedOpacity, pulseOpacity, inactiveOpacity];
  }
  if (state === "ready") {
    return [completedOpacity, completedOpacity, completedOpacity, pulseOpacity];
  }
  if (state === "error") {
    return [1, 1, 1, 1];
  }
  return [idleOpacity, idleOpacity, idleOpacity, idleOpacity];
}

export function Indicator({
  state,
  message,
  size = "compact",
  label,
}: {
  state: string;
  message?: string;
  size?: "compact" | "large";
  label?: string;
}) {
  const normalizedState = normalizeActivityMarkState(state);
  const [overrideState, setOverrideState] = useState<ActivityMarkState | null>(null);
  const [frame, setFrame] = useState(0);
  const previousStateRef = useRef<ActivityMarkState>(normalizedState);
  const previousErrorFlashRef = useRef(messageNeedsErrorFlash(message));
  const readyTimerRef = useRef<number | null>(null);
  const errorTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (readyTimerRef.current !== null) {
        window.clearTimeout(readyTimerRef.current);
      }
      if (errorTimerRef.current !== null) {
        window.clearTimeout(errorTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const previousState = previousStateRef.current;
    previousStateRef.current = normalizedState;

    if (normalizedState !== "listening" && readyTimerRef.current !== null) {
      window.clearTimeout(readyTimerRef.current);
      readyTimerRef.current = null;
      setOverrideState((current) => (current === "ready" ? null : current));
    }

    if (previousState === "speaking" && normalizedState === "listening") {
      if (readyTimerRef.current !== null) {
        window.clearTimeout(readyTimerRef.current);
      }
      setOverrideState("ready");
      readyTimerRef.current = window.setTimeout(() => {
        readyTimerRef.current = null;
        setOverrideState((current) => (current === "ready" ? null : current));
      }, ACTIVITY_MARK_READY_FLASH_MS);
    }
  }, [normalizedState]);

  const shouldFlashError = messageNeedsErrorFlash(message);

  useEffect(() => {
    const wasFlashingError = previousErrorFlashRef.current;
    previousErrorFlashRef.current = shouldFlashError;

    if (!shouldFlashError || wasFlashingError) {
      return;
    }

    if (readyTimerRef.current !== null) {
      window.clearTimeout(readyTimerRef.current);
      readyTimerRef.current = null;
    }
    if (errorTimerRef.current !== null) {
      window.clearTimeout(errorTimerRef.current);
    }

    setOverrideState("error");
    errorTimerRef.current = window.setTimeout(() => {
      errorTimerRef.current = null;
      setOverrideState((current) => (current === "error" ? null : current));
    }, ACTIVITY_MARK_ERROR_FLASH_MS);
  }, [shouldFlashError]);

  const effectiveState = overrideState ?? normalizedState;
  const segmentOpacities = getActivityMarkSegmentOpacities(effectiveState, frame);

  useEffect(() => {
    setFrame(0);
    const interval = ACTIVITY_MARK_ANIMATION_INTERVAL_MS[effectiveState];
    if (!interval) {
      return;
    }

    const timer = window.setInterval(() => {
      setFrame((current) => 1 - current);
    }, interval);

    return () => window.clearInterval(timer);
  }, [effectiveState]);

  return (
    <div
      className={`activity-mark activity-mark--${size}`}
      data-state={effectiveState}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <svg
        className="activity-mark__svg"
        viewBox="0 0 36 36"
        shapeRendering="geometricPrecision"
        aria-hidden="true"
      >
        {ACTIVITY_MARK_SEGMENTS.map((segment, index) => (
          <rect
            key={segment.key}
            className={`activity-mark__segment activity-mark__segment--${segment.key}`}
            x={segment.x}
            y={segment.y}
            width={segment.width}
            height={segment.height}
            opacity={segmentOpacities[index]}
          />
        ))}
      </svg>
    </div>
  );
}
