import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Icon } from "@/components/icons";
import { cn } from "@/lib/utils";

function formatStepValue(nextValue: number, step: number) {
  const precision = `${step}`.includes(".")
    ? `${step}`.split(".")[1]?.length ?? 0
    : 0;
  return nextValue.toFixed(precision).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

function getFillWidth(value: string, min: number | undefined, visualMax: number) {
  const parsedValue = Number.parseFloat(value);
  if (!Number.isFinite(parsedValue)) return "8%";
  const start = min ?? 0;
  const percent = ((parsedValue - start) / Math.max(visualMax - start, 1)) * 100;
  return `${Math.min(100, Math.max(0, percent))}%`;
}

function clampValue(value: number, min: number | undefined, max: number) {
  return Math.min(max, Math.max(min ?? 0, value));
}

export function TimingControl({
  fieldName,
  label,
  value,
  helperText,
  errorText,
  icon,
  suffix,
  step,
  min,
  max,
  visualMax,
  enabled,
  onToggleEnabled,
  onFocus,
  onChange,
  onCommit,
}: {
  fieldName: string;
  label: string;
  value: string;
  helperText: string;
  errorText?: string;
  icon: string;
  suffix: string;
  step: number;
  min?: number;
  max?: number;
  visualMax: number;
  enabled: boolean;
  onToggleEnabled?: () => void;
  onFocus?: () => void;
  onChange: (value: string) => void;
  onCommit: (value: string) => void;
}) {
  const [flash, setFlash] = useState(false);
  const previousValue = useRef(value);
  const flashTimer = useRef<number | null>(null);
  const describedBy = errorText ? `${fieldName}-error` : `${fieldName}-helper`;
  const rangeMin = min ?? 0;
  const rangeMax = max ?? visualMax;
  const parsedValue = Number.parseFloat(value);
  const canToggle = typeof onToggleEnabled === "function";
  const rangeValue = clampValue(
    Number.isFinite(parsedValue) ? parsedValue : rangeMin,
    rangeMin,
    rangeMax,
  );

  useEffect(() => {
    if (previousValue.current !== value) {
      previousValue.current = value;
      setFlash(true);
      if (flashTimer.current) window.clearTimeout(flashTimer.current);
      flashTimer.current = window.setTimeout(() => setFlash(false), 260);
    }
    return () => {
      if (flashTimer.current) window.clearTimeout(flashTimer.current);
    };
  }, [value]);

  const adjustValue = (direction: -1 | 1) => {
    if (!enabled) return;
    const parsedValue = Number.parseFloat(value);
    const baseValue = Number.isFinite(parsedValue)
      ? parsedValue
      : typeof min === "number"
        ? min
        : 0;
    let nextValue = baseValue + direction * step;
    if (typeof min === "number") nextValue = Math.max(min, nextValue);
    if (typeof max === "number") nextValue = Math.min(max, nextValue);
    const nextDraft = formatStepValue(nextValue, step);
    onChange(nextDraft);
    onCommit(nextDraft);
  };

  const setRangeValue = (nextValue: number, commit = false) => {
    if (!enabled) return;
    const nextDraft = formatStepValue(clampValue(nextValue, rangeMin, rangeMax), step);
    onChange(nextDraft);
    if (commit) onCommit(nextDraft);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      adjustValue(1);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      adjustValue(-1);
    }
  };

  return (
    <div className="grid min-w-0 gap-2" role="group" aria-labelledby={`${fieldName}-label`}>
      <div
        className={cn(
          "grid min-h-[8.25rem] grid-cols-[3.25rem_minmax(0,1fr)] gap-3 rounded-2xl border bg-card p-3 transition-[background-color,border-color,box-shadow,opacity]",
          enabled
            ? "border-[color-mix(in_srgb,var(--accent)_34%,rgba(255,255,255,0.1))] shadow-[0_0_0_1px_color-mix(in_srgb,var(--accent)_8%,transparent)]"
            : "border-white/10 opacity-75",
          errorText && "border-red-400/45",
          flash && enabled && "border-[color-mix(in_srgb,var(--accent)_52%,transparent)]",
        )}
      >
        {canToggle ? (
          <button
            type="button"
            className={cn(
              "grid size-13 place-items-center rounded-2xl border transition-[background-color,border-color,color,transform] active:scale-95 focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_12%,transparent)]",
              enabled
                ? "border-[color-mix(in_srgb,var(--accent)_46%,transparent)] bg-[color-mix(in_srgb,var(--accent)_17%,transparent)] text-[var(--accent-strong)]"
                : "border-white/10 bg-white/[0.035] text-[var(--text-muted)] hover:bg-white/[0.055]",
            )}
            aria-label={`${enabled ? "Disable" : "Enable"} ${label}`}
            aria-pressed={enabled}
            onClick={onToggleEnabled}
          >
            <Icon name={icon} className="size-6" />
          </button>
        ) : (
          <div
            className="grid size-13 place-items-center rounded-2xl border border-[color-mix(in_srgb,var(--accent)_46%,transparent)] bg-[color-mix(in_srgb,var(--accent)_17%,transparent)] text-[var(--accent-strong)]"
            aria-hidden="true"
          >
            <Icon name={icon} className="size-6" />
          </div>
        )}

        <div className="min-w-0">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0">
              <div
                id={`${fieldName}-label`}
                className="truncate text-sm font-semibold text-[var(--text-strong)]"
              >
                {label}
              </div>
              <p id={`${fieldName}-helper`} className="mt-1 text-xs text-[var(--text-muted)]">
                {helperText}
              </p>
            </div>
            {canToggle ? (
              <span
                className={cn(
                  "shrink-0 rounded-full border px-2 py-1 font-mono text-[0.62rem] font-bold uppercase tracking-[0.14em]",
                  enabled
                    ? "border-[color-mix(in_srgb,var(--accent)_40%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--accent-strong)]"
                    : "border-white/10 bg-white/[0.025] text-[var(--text-muted)]",
                )}
              >
                {enabled ? "On" : "Off"}
              </span>
            ) : null}
          </div>

          <div className="mt-3 flex items-center gap-2">
            <div
              className={cn(
                "relative min-w-0 flex-1 rounded-xl border border-white/8 bg-[var(--timing-input-bg,#28282b)] shadow-[inset_0_1px_0_rgba(255,255,255,0.035)] transition-[border-color,box-shadow,opacity] focus-within:border-[color-mix(in_srgb,var(--accent)_42%,transparent)] focus-within:shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_10%,transparent),inset_0_1px_0_rgba(255,255,255,0.035)]",
                !enabled && "opacity-55",
              )}
            >
              <Input
                className="h-10 w-full border-0 bg-transparent px-3 pr-9 font-mono text-2xl font-semibold tabular-nums text-[var(--text-strong)] shadow-none outline-none ring-0 disabled:cursor-not-allowed disabled:text-[var(--text-muted)] focus-visible:ring-0"
                value={enabled ? value : "Off"}
                type="text"
                name={fieldName}
                inputMode="decimal"
                autoComplete="off"
                spellCheck={false}
                disabled={!enabled}
                aria-describedby={describedBy}
                aria-invalid={errorText ? true : undefined}
                onChange={(event) => onChange(event.currentTarget.value)}
                onBlur={(event) => onCommit(event.currentTarget.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => onFocus?.()}
              />
              {enabled ? (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-[var(--text-muted)]">
                  {suffix}
                </span>
              ) : null}
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                className="rounded-xl"
                disabled={!enabled}
                aria-label={`Decrease ${label}`}
                onClick={() => adjustValue(-1)}
              >
                <Icon name="minus" className="size-3.5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                className="rounded-xl"
                disabled={!enabled}
                aria-label={`Increase ${label}`}
                onClick={() => adjustValue(1)}
              >
                <Icon name="plus" className="size-3.5" />
              </Button>
            </div>
          </div>

          <div className="relative mt-3 h-5">
            <div className="absolute left-0 right-0 top-1/2 h-1.5 -translate-y-1/2 overflow-hidden rounded-full bg-white/[0.055]">
              <div
                className={cn(
                  "h-full rounded-full transition-[width,background-color]",
                  enabled ? "bg-[var(--accent)]" : "bg-white/15",
                )}
                style={{ width: enabled ? getFillWidth(value, min, rangeMax) : "0%" }}
              />
            </div>
            <span
              className={cn(
                "absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[color-mix(in_srgb,var(--accent)_70%,black)] bg-[var(--accent)] shadow-[0_0_0_4px_color-mix(in_srgb,var(--accent)_12%,transparent)] transition-[left,opacity]",
                enabled ? "opacity-100" : "opacity-0",
              )}
              style={{ left: getFillWidth(value, min, rangeMax) }}
            />
            <input
              className="absolute inset-x-0 top-1/2 h-8 -translate-y-1/2 cursor-pointer opacity-0 disabled:cursor-not-allowed"
              type="range"
              name={`${fieldName}_slider`}
              min={rangeMin}
              max={rangeMax}
              step={step}
              value={rangeValue}
              disabled={!enabled}
              aria-label={`${label} slider`}
              aria-describedby={describedBy}
              onChange={(event) => setRangeValue(event.currentTarget.valueAsNumber)}
              onPointerUp={(event) => setRangeValue(event.currentTarget.valueAsNumber, true)}
              onTouchEnd={(event) => setRangeValue(event.currentTarget.valueAsNumber, true)}
              onKeyUp={(event) => setRangeValue(event.currentTarget.valueAsNumber, true)}
              onBlur={(event) => setRangeValue(event.currentTarget.valueAsNumber, true)}
            />
          </div>
        </div>
      </div>
      {errorText ? (
        <span id={`${fieldName}-error`} className="text-xs text-red-300">
          {errorText}
        </span>
      ) : null}
    </div>
  );
}
