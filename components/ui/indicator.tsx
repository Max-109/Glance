import { useEffect, useState } from "react";

type ActivityMarkState =
  | "idle"
  | "listening"
  | "transcribing"
  | "generating"
  | "speaking"
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
  transcribing: 560,
  generating: 560,
  speaking: 420,
};

function normalizeActivityMarkState(state: string): ActivityMarkState {
  if (
    state === "listening" ||
    state === "transcribing" ||
    state === "generating" ||
    state === "speaking" ||
    state === "error"
  ) {
    return state;
  }
  if (state === "processing") {
    return "transcribing";
  }
  return "idle";
}

function resolveBlinkIntervalMs(
  state: ActivityMarkState,
  blinkIntervalMs: number,
): number {
  if (blinkIntervalMs > 0) {
    return blinkIntervalMs;
  }
  return ACTIVITY_MARK_ANIMATION_INTERVAL_MS[state] ?? 0;
}

function getActivityMarkFrame(
  phaseStartedAtMs: number,
  blinkIntervalMs: number,
  nowMs: number,
): number {
  if (phaseStartedAtMs <= 0 || blinkIntervalMs <= 0) {
    return 0;
  }
  const elapsedMs = Math.max(0, nowMs - phaseStartedAtMs);
  return Math.floor(elapsedMs / blinkIntervalMs) % 2;
}

function getNextActivityMarkUpdateAtMs(
  phaseStartedAtMs: number,
  blinkIntervalMs: number,
  errorFlashUntilMs: number,
  nowMs: number,
): number | null {
  if (errorFlashUntilMs > nowMs) {
    return errorFlashUntilMs;
  }
  if (phaseStartedAtMs <= 0 || blinkIntervalMs <= 0) {
    return null;
  }
  const elapsedMs = Math.max(0, nowMs - phaseStartedAtMs);
  const completedSteps = Math.floor(elapsedMs / blinkIntervalMs);
  return phaseStartedAtMs + (completedSteps + 1) * blinkIntervalMs;
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
  if (state === "transcribing") {
    return [completedOpacity, pulseOpacity, inactiveOpacity, inactiveOpacity];
  }
  if (state === "generating") {
    return [completedOpacity, completedOpacity, pulseOpacity, inactiveOpacity];
  }
  if (state === "speaking") {
    return [completedOpacity, completedOpacity, completedOpacity, pulseOpacity];
  }
  if (state === "error") {
    return [1, 1, 1, 1];
  }
  return [idleOpacity, idleOpacity, idleOpacity, idleOpacity];
}

export function Indicator({
  state,
  size = "compact",
  label,
  phaseStartedAtMs = 0,
  blinkIntervalMs = 0,
  errorFlashUntilMs = 0,
}: {
  state: string;
  size?: "compact" | "large";
  label?: string;
  phaseStartedAtMs?: number;
  blinkIntervalMs?: number;
  errorFlashUntilMs?: number;
}) {
  const normalizedState = normalizeActivityMarkState(state);
  const [renderTick, setRenderTick] = useState(0);
  const nowMs = Date.now();
  const effectiveState = errorFlashUntilMs > nowMs ? "error" : normalizedState;
  const resolvedBlinkInterval = resolveBlinkIntervalMs(normalizedState, blinkIntervalMs);
  const frame =
    effectiveState === "error"
      ? 0
      : getActivityMarkFrame(phaseStartedAtMs, resolvedBlinkInterval, nowMs);
  const segmentOpacities = getActivityMarkSegmentOpacities(effectiveState, frame);

  useEffect(() => {
    const syncPhase = () => {
      setRenderTick((current) => current + 1);
    };

    window.addEventListener("focus", syncPhase);
    document.addEventListener("visibilitychange", syncPhase);
    return () => {
      window.removeEventListener("focus", syncPhase);
      document.removeEventListener("visibilitychange", syncPhase);
    };
  }, []);

  useEffect(() => {
    const nextUpdateAtMs = getNextActivityMarkUpdateAtMs(
      phaseStartedAtMs,
      resolvedBlinkInterval,
      errorFlashUntilMs,
      nowMs,
    );
    if (nextUpdateAtMs === null) {
      return;
    }

    const timer = window.setTimeout(() => {
      setRenderTick((current) => current + 1);
    }, Math.max(1, nextUpdateAtMs - Date.now()));

    return () => window.clearTimeout(timer);
  }, [errorFlashUntilMs, nowMs, phaseStartedAtMs, renderTick, resolvedBlinkInterval]);

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
