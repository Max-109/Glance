import type {
  KeyboardEvent,
  PointerEvent as ReactPointerEvent,
} from "react";
import { useEffect, useRef, useState } from "react";

import { Button } from "./button";

const MIC_GATE_HISTORY_SECONDS = 6;
const MIC_GATE_SAMPLE_HZ = 30;
const MIC_GATE_HISTORY_LENGTH = MIC_GATE_HISTORY_SECONDS * MIC_GATE_SAMPLE_HZ;
const MIC_GATE_PEAK_DECAY = 0.94;
const MIC_GATE_GLOW_LAYER_SCALE = 0.6;

type MicGateStatus = "idle" | "quiet" | "speech" | "noisy";

function percentile(values: number[], p: number) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.max(
    0,
    Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p)),
  );
  return sorted[idx];
}

export function MicThreshold({
  level,
  threshold,
  active,
  onPointerDown,
  onNudge,
  onToggleTest,
}: {
  level: number;
  threshold: number;
  active: boolean;
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onNudge: (delta: number) => void;
  onToggleTest: () => void;
}) {
  const vizRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const glowCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const historyRef = useRef<Float32Array>(
    new Float32Array(MIC_GATE_HISTORY_LENGTH),
  );
  const peakRef = useRef<Float32Array>(
    new Float32Array(MIC_GATE_HISTORY_LENGTH),
  );
  const headRef = useRef(0);
  const latestLevelRef = useRef(0);
  const thresholdRef = useRef(0);
  const activeRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const lastSampleRef = useRef(0);
  const lastStatsAtRef = useRef(0);
  const aboveSinceRef = useRef<number | null>(null);
  const traceXRef = useRef<Float32Array>(
    new Float32Array(MIC_GATE_HISTORY_LENGTH),
  );
  const traceYRef = useRef<Float32Array>(
    new Float32Array(MIC_GATE_HISTORY_LENGTH),
  );
  const traceAboveRef = useRef<Uint8Array>(
    new Uint8Array(MIC_GATE_HISTORY_LENGTH),
  );

  const [status, setStatus] = useState<MicGateStatus>("idle");
  const [liveLevel, setLiveLevel] = useState(level);

  const effectiveLevel = active ? liveLevel : level;
  const normalizedLevel = Math.max(0, Math.min(1, effectiveLevel || 0));
  const normalizedThreshold = Math.max(0, Math.min(1, threshold || 0));

  latestLevelRef.current = normalizedLevel;
  thresholdRef.current = normalizedThreshold;
  activeRef.current = active;

  useEffect(() => {
    if (!active) {
      setLiveLevel(level);
      return;
    }

    let cancelled = false;

    const refreshAudioLevel = async () => {
      if (typeof window === "undefined") {
        return;
      }
      const bridge = window.glanceBridge ?? null;
      if (!bridge?.getAudioState) {
        return;
      }

      try {
        const snapshot = await bridge.getAudioState();
        if (cancelled) {
          return;
        }
        setLiveLevel((current) =>
          Math.abs(current - snapshot.audioInputLevel) < 0.001
            ? current
            : snapshot.audioInputLevel,
        );
      } catch {
        // The canvas meter should fail quietly if the bridge is unavailable.
      }
    };

    void refreshAudioLevel();
    const interval = window.setInterval(() => {
      void refreshAudioLevel();
    }, 150);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [active, level]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const glowCanvas = glowCanvasRef.current;
    const host = vizRef.current;
    if (!canvas || !glowCanvas || !host) return;

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const ctx = canvas.getContext("2d");
    const glowCtx = glowCanvas.getContext("2d");
    if (!ctx || !glowCtx) return;

    type Colors = {
      accent: string;
      accentStrong: string;
      accentGlow: string;
      muted: string;
      line: string;
      ripple: string;
    };

    const fallbackColors: Colors = {
      accent: "#a7ffde",
      accentStrong: "#d3fff0",
      accentGlow: "rgba(167, 255, 222, 0.38)",
      muted: "rgba(255, 255, 255, 0.22)",
      line: "rgba(167, 255, 222, 0.14)",
      ripple: "rgba(167, 255, 222, 0.65)",
    };

    let cachedColors: Colors = fallbackColors;

    const readColors = (): Colors => {
      if (typeof window === "undefined") return fallbackColors;
      const styles = getComputedStyle(host);
      const accent = styles.getPropertyValue("--accent").trim() || fallbackColors.accent;
      const accentStrong =
        styles.getPropertyValue("--accent-strong").trim() || fallbackColors.accentStrong;
      const accentGlow =
        styles.getPropertyValue("--accent-glow").trim() || fallbackColors.accentGlow;
      const line =
        styles.getPropertyValue("--mic-gate-line").trim() || fallbackColors.line;
      const ripple =
        styles.getPropertyValue("--mic-gate-ripple").trim() || fallbackColors.ripple;
      return {
        accent,
        accentStrong,
        accentGlow,
        muted: "rgba(255, 255, 255, 0.22)",
        line,
        ripple,
      };
    };

    cachedColors = readColors();

    let handleInset = 96;

    const resizeCanvas = (
      target: HTMLCanvasElement,
      targetCtx: CanvasRenderingContext2D,
      rect: DOMRect,
      dpr: number,
      scale = 1,
    ) => {
      const targetDpr = Math.max(1, dpr * scale);
      target.width = Math.max(1, Math.round(rect.width * targetDpr));
      target.height = Math.max(1, Math.round(rect.height * targetDpr));
      target.style.width = `${rect.width}px`;
      target.style.height = `${rect.height}px`;
      targetCtx.setTransform(targetDpr, 0, 0, targetDpr, 0, 0);
    };

    const resize = () => {
      const rect = host.getBoundingClientRect();
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      resizeCanvas(canvas, ctx, rect, dpr);
      resizeCanvas(glowCanvas, glowCtx, rect, dpr, MIC_GATE_GLOW_LAYER_SCALE);

      const pill = host.querySelector<HTMLElement>(".mic-gate__tick");
      if (pill) {
        const hostRect = host.getBoundingClientRect();
        const pillRect = pill.getBoundingClientRect();
        handleInset = Math.max(24, Math.round(hostRect.right - pillRect.left + 6));
      }
    };
    resize();

    const observer =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(resize)
        : null;
    observer?.observe(host);

    const sampleInterval = 1000 / MIC_GATE_SAMPLE_HZ;
    let colorRefreshAt = 0;

    const pushSample = (value: number) => {
      const history = historyRef.current;
      const peak = peakRef.current;
      const idx = headRef.current;
      history[idx] = value;
      const prevPeakIdx =
        (idx - 1 + MIC_GATE_HISTORY_LENGTH) % MIC_GATE_HISTORY_LENGTH;
      const prevPeak = peak[prevPeakIdx] * MIC_GATE_PEAK_DECAY;
      peak[idx] = Math.max(value, prevPeak);
      headRef.current = (idx + 1) % MIC_GATE_HISTORY_LENGTH;
    };

    const draw = (_now: number) => {
      const width = host.clientWidth;
      const height = host.clientHeight;
      if (width <= 0 || height <= 0) return;

      const colors = cachedColors;
      const history = historyRef.current;
      const peak = peakRef.current;
      const head = headRef.current;
      const thr = thresholdRef.current;

      ctx.clearRect(0, 0, width, height);
      glowCtx.clearRect(0, 0, width, height);

      ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (const p of [0.25, 0.5, 0.75]) {
        const y = Math.round((1 - p) * height) + 0.5;
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();

      ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
      ctx.setLineDash([3, 5]);
      ctx.beginPath();
      const headroomY = Math.round(height * 0.05) + 0.5;
      ctx.moveTo(0, headroomY);
      ctx.lineTo(width, headroomY);
      ctx.stroke();
      ctx.setLineDash([]);

      const visibleCount = MIC_GATE_HISTORY_LENGTH;
      const step = width / visibleCount;
      const gap = Math.min(1.25, step * 0.22);
      const barWidth = step > 1 ? Math.max(1, step - gap) : 1;
      const slotOffset = Math.max(0, (step - barWidth) / 2);
      const startReadIdx =
        (head - visibleCount + MIC_GATE_HISTORY_LENGTH) % MIC_GATE_HISTORY_LENGTH;

      const traceX = traceXRef.current;
      const traceY = traceYRef.current;
      const traceAbove = traceAboveRef.current;
      let hasAboveTrace = false;

      ctx.fillStyle = colors.muted;
      for (let i = 0; i < visibleCount; i++) {
        const srcIdx = (startReadIdx + i) % MIC_GATE_HISTORY_LENGTH;
        const v = history[srcIdx];
        const p = peak[srcIdx];
        const x = i * step + slotOffset;
        const barH = Math.max(1, v * height);
        ctx.fillRect(x, height - barH, barWidth, barH);

        traceX[i] = x + barWidth / 2;
        traceY[i] = height - Math.max(1, p * height);
        const above = thr > 0 && p >= thr ? 1 : 0;
        traceAbove[i] = above;
        hasAboveTrace ||= above === 1;
      }

      const thresholdY = (1 - thr) * height;
      const thrY = Math.round(thresholdY) + 0.5;
      const lineEnd = Math.max(0, width - handleInset);
      ctx.strokeStyle = colors.line;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, thrY);
      ctx.lineTo(lineEnd, thrY);
      ctx.stroke();

      const tracePath = new Path2D();
      if (visibleCount > 0) {
        tracePath.moveTo(traceX[0], traceY[0]);
        for (let i = 1; i < visibleCount; i++) {
          tracePath.lineTo(traceX[i], traceY[i]);
        }
      }

      ctx.strokeStyle = "rgba(255, 255, 255, 0.28)";
      ctx.lineWidth = 1;
      ctx.stroke(tracePath);

      if (thr > 0 && hasAboveTrace) {
        const accentPath = new Path2D();

        let prevX = traceX[0];
        let prevY = traceY[0];
        let prevAbove = traceAbove[0] === 1;
        let segmentOpen = false;

        for (let i = 1; i < visibleCount; i++) {
          const x = traceX[i];
          const y = traceY[i];
          const above = traceAbove[i] === 1;

          if (prevAbove && above) {
            if (!segmentOpen) {
              accentPath.moveTo(prevX, prevY);
              segmentOpen = true;
            }
            accentPath.lineTo(x, y);
          } else if (prevAbove !== above) {
            const dy = y - prevY;
            const t = dy === 0 ? 0 : (thresholdY - prevY) / dy;
            const clampedT = Math.max(0, Math.min(1, t));
            const crossX = prevX + (x - prevX) * clampedT;

            if (prevAbove) {
              if (!segmentOpen) accentPath.moveTo(prevX, prevY);
              accentPath.lineTo(crossX, thresholdY);
              segmentOpen = false;
            } else {
              accentPath.moveTo(crossX, thresholdY);
              accentPath.lineTo(x, y);
              segmentOpen = true;
            }
          } else {
            segmentOpen = false;
          }

          prevX = x;
          prevY = y;
          prevAbove = above;
        }

        ctx.strokeStyle = colors.accent;
        ctx.lineWidth = 1.6;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.stroke(accentPath);
        ctx.lineCap = "butt";
        ctx.lineJoin = "miter";

        glowCtx.strokeStyle = colors.accent;
        glowCtx.lineWidth = 1.6;
        glowCtx.lineCap = "round";
        glowCtx.lineJoin = "round";
        glowCtx.shadowColor = colors.accentGlow;
        glowCtx.shadowBlur = 6;
        glowCtx.stroke(accentPath);
        glowCtx.shadowBlur = 0;
        glowCtx.lineCap = "butt";
        glowCtx.lineJoin = "miter";
      }

      ctx.strokeStyle = "rgba(255, 255, 255, 0.14)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(width - 0.5, 0);
      ctx.lineTo(width - 0.5, height);
      ctx.stroke();
    };

    const tick = (now: number) => {
      if (!lastSampleRef.current) lastSampleRef.current = now;

      if (now - colorRefreshAt > 500) {
        cachedColors = readColors();
        colorRefreshAt = now;
      }

      let sampled = false;
      while (now - lastSampleRef.current >= sampleInterval) {
        pushSample(activeRef.current ? latestLevelRef.current : 0);
        lastSampleRef.current += sampleInterval;
        sampled = true;
      }

      if (sampled) {
        draw(now);
      }

      if (now - lastStatsAtRef.current >= 200) {
        lastStatsAtRef.current = now;
        const arr = Array.from(historyRef.current);
        const nf = percentile(arr, 0.1);
        const thr = thresholdRef.current;
        const lvl = latestLevelRef.current;
        let next: MicGateStatus = "idle";
        if (!activeRef.current) {
          next = "idle";
          aboveSinceRef.current = null;
        } else if (nf > thr) {
          next = "noisy";
        } else if (lvl >= thr) {
          if (aboveSinceRef.current == null) aboveSinceRef.current = now;
          if (now - aboveSinceRef.current > 100) next = "speech";
          else next = "quiet";
        } else {
          aboveSinceRef.current = null;
          next = "quiet";
        }
        setStatus((prev) => (prev === next ? prev : next));
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    if (prefersReducedMotion) {
      draw(performance.now());
    } else {
      rafRef.current = requestAnimationFrame(tick);
    }

    return () => {
      observer?.disconnect();
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastSampleRef.current = 0;
      lastStatsAtRef.current = 0;
    };
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    let delta = 0;
    const step = event.shiftKey ? 0.05 : 0.01;
    if (event.key === "ArrowUp" || event.key === "ArrowRight") delta = step;
    else if (event.key === "ArrowDown" || event.key === "ArrowLeft") delta = -step;
    else if (event.key === "PageUp") delta = 0.1;
    else if (event.key === "PageDown") delta = -0.1;
    else if (event.key === "Home") {
      event.preventDefault();
      onNudge(-1);
      return;
    } else if (event.key === "End") {
      event.preventDefault();
      onNudge(1);
      return;
    }
    if (delta !== 0) {
      event.preventDefault();
      onNudge(delta);
    }
  };

  const thresholdPct = Math.round(normalizedThreshold * 100);
  const levelPct = Math.round(normalizedLevel * 100);
  const statusLabel =
    status === "speech"
      ? "Speech detected"
      : status === "noisy"
        ? "Noise crossing line - raise threshold"
        : status === "quiet"
          ? "Quiet"
          : "Mic test off";

  const levelSegments = 18;
  const filledLevelSegments = Math.round(normalizedLevel * levelSegments);
  const thresholdSegment = Math.min(
    levelSegments - 1,
    Math.max(0, Math.round(normalizedThreshold * (levelSegments - 1))),
  );
  const hotLevelWidth = Math.max(0, normalizedLevel - normalizedThreshold);

  return (
    <div className="mic-gate">
      <div className={`mic-gate__status mic-gate__status--${status}`}>
        <span className="mic-gate__status-dot" aria-hidden="true" />
        <span>{statusLabel}</span>
      </div>

      <div className="mic-gate__toolbar">
        <p className="mic-gate__toolbar-copy">
          Set the mic threshold so speech triggers Glance, not room noise.
        </p>
        <div className="mic-gate__toolbar-controls">
          <button
            type="button"
            className="mic-gate__chip-btn"
            aria-label="Lower threshold by 1%"
            onClick={() => onNudge(-0.01)}
          >
            -
          </button>
          <span className="mic-gate__toolbar-value">{thresholdPct}%</span>
          <button
            type="button"
            className="mic-gate__chip-btn"
            aria-label="Raise threshold by 1%"
            onClick={() => onNudge(0.01)}
          >
            +
          </button>
        </div>
      </div>

      <div
        ref={vizRef}
        className={`mic-gate__viz${active ? " is-active" : ""}`}
        data-scroll-host="false"
        role="slider"
        tabIndex={0}
        aria-label="Mic sensitivity threshold"
        aria-orientation="vertical"
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuenow={Number(normalizedThreshold.toFixed(3))}
        aria-valuetext={`Threshold ${thresholdPct}%`}
        title={`Threshold ${thresholdPct}% - drag to adjust`}
        onPointerDown={onPointerDown}
        onKeyDown={handleKeyDown}
      >
        <canvas ref={canvasRef} className="mic-gate__canvas" aria-hidden="true" />
        <canvas
          ref={glowCanvasRef}
          className="mic-gate__canvas mic-gate__canvas--glow"
          aria-hidden="true"
        />

        <div
          className="mic-gate__tick"
          style={{ bottom: `${normalizedThreshold * 100}%` }}
          aria-hidden="true"
        >
          <span className="mic-gate__tick-mark" />
          <span className="mic-gate__tick-value">{thresholdPct}%</span>
        </div>
      </div>

      <div className="mic-gate__chips">
        <div className="mic-gate__chip mic-gate__chip--level">
          <span className="mic-gate__chip-label">Live level</span>
          <span className="mic-gate__chip-value">
            <span className="mic-gate__level-number">{levelPct}%</span>
            <span className="mic-gate__level-meter" aria-hidden="true">
              {hotLevelWidth > 0 ? (
                <span
                  className="mic-gate__level-glow"
                  style={{
                    left: `${normalizedThreshold * 100}%`,
                    width: `${hotLevelWidth * 100}%`,
                  }}
                />
              ) : null}
              {Array.from({ length: levelSegments }).map((_, i) => (
                <span
                  key={i}
                  className={`mic-gate__level-seg${
                    i < filledLevelSegments ? " is-on" : ""
                  }${
                    i === thresholdSegment ? " is-threshold" : ""
                  }${
                    i < filledLevelSegments && i >= thresholdSegment
                      ? " is-hot"
                      : ""
                  }`}
                />
              ))}
            </span>
          </span>
        </div>

        <Button
          label={active ? "Stop Mic Test" : "Start Mic Test"}
          icon={active ? "stop" : "mic"}
          variant="signal"
          className="mic-gate__test-button"
          onClick={onToggleTest}
        />
      </div>
    </div>
  );
}
