import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { CSSProperties } from "react";
import { Icon } from "@/components/icons";
import { GlanceButton } from "@/components/settings-shell/button";
import { SelectControl } from "@/components/settings-shell/form-controls";
import { StatusBadge, type StatusTone } from "@/components/settings-shell/status-badge";
import { cn } from "@/lib/utils";

import { type SettingsTabProps, settingValue } from "./shared";

type DeviceTone = "ready" | "fallback" | "missing" | "testing";
type TimingTone = "responsive" | "patient" | "custom";

const PATIENCE_LABELS: Record<string, string> = {
  fast: "Fast",
  balanced: "Balanced",
  patient: "Patient",
};

const PATIENCE_COPY: Record<string, string> = {
  fast: "Replies sooner.",
  balanced: "Waits through short pauses.",
  patient: "Waits longer.",
};

function clarityLabel(value: number) {
  if (value < 0.4) return "Softer";
  if (value > 0.65) return "Clearer";
  return "Balanced";
}

function mapStatusTone(tone: DeviceTone | TimingTone): StatusTone {
  if (tone === "ready" || tone === "responsive") return "accent";
  if (tone === "missing") return "danger";
  if (tone === "testing") return "warning";
  return "neutral";
}

function computeDeviceStatus(state: SettingsTabProps["state"]): {
  tone: DeviceTone;
  label: string;
} {
  if (state.speakerTestActive) {
    return { tone: "testing", label: "Testing speakers" };
  }
  const inputCount = state.audioInputDeviceOptions?.length ?? 0;
  const outputCount = state.audioOutputDeviceOptions?.length ?? 0;
  if (inputCount === 0 || outputCount === 0) {
    return { tone: "missing", label: "No devices detected" };
  }
  const inputValue = settingValue(state, "audio_input_device");
  const outputValue = settingValue(state, "audio_output_device");
  const usingFallback =
    !inputValue || inputValue === "default" || !outputValue || outputValue === "default";
  if (usingFallback) {
    return { tone: "fallback", label: "System defaults" };
  }
  return { tone: "ready", label: "Ready" };
}

function parseTiming(raw: string): number {
  const value = Number.parseFloat(raw);
  return Number.isFinite(value) ? value : 0;
}

function settingBoolean(
  state: SettingsTabProps["state"],
  fieldName: string,
  fallback = true,
): boolean {
  const value = state.settings[fieldName];
  if (value === undefined || value === null) return fallback;
  if (typeof value === "boolean") return value;
  return String(value).toLowerCase() === "true";
}

function computeTimingStatus(values: {
  wait: number;
  maxRecord: number;
  preroll: number;
  enabledCount: number;
}): { tone: TimingTone; label: string } | null {
  const { wait, maxRecord, preroll, enabledCount } = values;
  if (enabledCount === 0) {
    return { tone: "custom", label: "Manual stop" };
  }
  if (enabledCount < 3) {
    return { tone: "custom", label: "Custom profile" };
  }
  if (wait <= 20 && maxRecord <= 60 && preroll <= 0.6) {
    return { tone: "responsive", label: "Fast turns" };
  }
  if (wait >= 40 || maxRecord >= 180) {
    return { tone: "patient", label: "Patient mode" };
  }
  return { tone: "custom", label: "Balanced" };
}

function levelTone(level: number) {
  if (level >= 0.08) return "Speech likely";
  if (level >= 0.025) return "Hearing activity";
  return "Quiet";
}

function percent(value: number) {
  return `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%`;
}

function formatStepValue(nextValue: number, step: number) {
  const precision = `${step}`.includes(".")
    ? `${step}`.split(".")[1]?.length ?? 0
    : 0;
  return nextValue.toFixed(precision).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

function clampValue(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function sliderPercent(value: string, min: number, max: number) {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) return "0%";
  return `${((clampValue(parsed, min, max) - min) / Math.max(max - min, 1)) * 100}%`;
}

function CompactTimingControl({
  fieldName,
  label,
  value,
  suffix,
  step,
  min,
  max,
  visualMax,
  enabled,
  errorText,
  onToggleEnabled,
  onChange,
  onCommit,
  onFocus,
}: {
  fieldName: string;
  label: string;
  value: string;
  suffix: string;
  step: number;
  min: number;
  max?: number;
  visualMax: number;
  enabled: boolean;
  errorText?: string;
  onToggleEnabled?: () => void;
  onChange: (value: string) => void;
  onCommit: (value: string) => void;
  onFocus: () => void;
}) {
  const rangeMax = max ?? visualMax;
  const parsed = Number.parseFloat(value);
  const rangeValue = Number.isFinite(parsed) ? clampValue(parsed, min, rangeMax) : min;
  const fill = sliderPercent(value, min, visualMax);

  const adjustValue = (direction: -1 | 1) => {
    if (!enabled) return;
    const base = Number.isFinite(parsed) ? parsed : min;
    const nextValue = clampValue(base + direction * step, min, rangeMax);
    const nextDraft = formatStepValue(nextValue, step);
    onChange(nextDraft);
    onCommit(nextDraft);
  };

  return (
    <div className="grid min-w-0 gap-2">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <button
          type="button"
          className="min-w-0 truncate text-left text-sm font-semibold text-[var(--text-strong)] transition-colors hover:text-[var(--accent-strong)] disabled:pointer-events-none"
          disabled={!onToggleEnabled}
          aria-pressed={enabled}
          onClick={onToggleEnabled}
        >
          {label}
        </button>
        {onToggleEnabled ? (
          <span
            className={cn(
              "shrink-0 rounded-full border px-2 py-0.5 font-mono text-[0.62rem] font-bold uppercase tracking-[0.14em]",
              enabled
                ? "border-[var(--accent-border)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                : "border-[var(--panel-border)] bg-[var(--chip-bg-soft)] text-[var(--text-muted)]",
            )}
          >
            {enabled ? "On" : "Off"}
          </span>
        ) : null}
      </div>

      <div
        className={cn(
          "grid gap-2 transition-opacity",
          !enabled && "opacity-55",
        )}
      >
        <div
          className={cn(
            "flex h-11 min-w-0 items-center rounded-xl border border-[var(--control-border)] bg-[var(--control-bg)] px-3 focus-within:border-[var(--accent-border)]",
            errorText && "border-red-400/45",
          )}
        >
          <input
            className="min-w-0 flex-1 border-0 bg-transparent font-mono text-base font-semibold text-[var(--text-strong)] outline-none disabled:cursor-not-allowed disabled:text-[var(--text-muted)]"
            value={enabled ? value : "Off"}
            name={fieldName}
            inputMode="decimal"
            disabled={!enabled}
            aria-invalid={errorText ? true : undefined}
            onChange={(event) => onChange(event.currentTarget.value)}
            onBlur={(event) => onCommit(event.currentTarget.value)}
            onFocus={onFocus}
          />
          {enabled ? (
            <span className="ml-2 text-sm font-semibold text-[var(--text-muted)]">
              {suffix}
            </span>
          ) : null}
          <div className="ml-3 flex items-center gap-1">
            <button
              type="button"
              className="grid size-8 place-items-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--item-hover)] hover:text-[var(--text-strong)] disabled:opacity-45"
              disabled={!enabled}
              aria-label={`Decrease ${label}`}
              onClick={() => adjustValue(-1)}
            >
              <Icon name="minus" className="size-3.5" />
            </button>
            <button
              type="button"
              className="grid size-8 place-items-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--item-hover)] hover:text-[var(--text-strong)] disabled:opacity-45"
              disabled={!enabled}
              aria-label={`Increase ${label}`}
              onClick={() => adjustValue(1)}
            >
              <Icon name="plus" className="size-3.5" />
            </button>
          </div>
        </div>

        <input
          className="audio-range h-4 w-full"
          type="range"
          min={min}
          max={visualMax}
          step={step}
          value={rangeValue}
          disabled={!enabled}
          style={{ "--range-fill": fill } as CSSProperties}
          aria-label={label}
          onChange={(event) => onChange(event.currentTarget.value)}
          onMouseUp={(event) => onCommit(event.currentTarget.value)}
          onTouchEnd={(event) => onCommit(event.currentTarget.value)}
        />
      </div>

      {errorText ? <p className="text-xs text-red-300">{errorText}</p> : null}
    </div>
  );
}

export function AudioTab({
  state,
  openSelect,
  audioLevel,
  onToggleSelect,
  onSelectValue,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onRunAction,
  onSetField,
  getDraftValue,
}: Pick<
  SettingsTabProps,
  | "state"
  | "openSelect"
  | "audioLevel"
  | "onToggleSelect"
  | "onSelectValue"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onRunAction"
  | "onSetField"
  | "getDraftValue"
>) {
  const deviceStatus = computeDeviceStatus(state);
  const wait = parseTiming(getDraftValue("audio_max_wait_seconds"));
  const maxRecord = parseTiming(getDraftValue("audio_max_record_seconds"));
  const preroll = parseTiming(getDraftValue("audio_preroll_seconds"));
  const waitEnabled = settingBoolean(state, "audio_wait_for_speech_enabled");
  const maxRecordEnabled = settingBoolean(state, "audio_max_turn_length_enabled");
  const prerollEnabled = settingBoolean(state, "audio_preroll_enabled");
  const enabledCount = [waitEnabled, maxRecordEnabled, prerollEnabled].filter(Boolean).length;
  const timingStatus = computeTimingStatus({
    wait,
    maxRecord,
    preroll,
    enabledCount,
  });
  const patience = settingValue(state, "audio_endpoint_patience") || "balanced";
  const inputLabel =
    state.audioInputDeviceLabels[settingValue(state, "audio_input_device") || "default"] ||
    "System Default Input";
  const clarityValue = clampValue(
    Number.parseFloat(getDraftValue("audio_vad_threshold")) || 0.5,
    0.05,
    0.95,
  );
  const levelSegments = 18;
  const filledSegments = Math.round(Math.min(1, audioLevel * 8) * levelSegments);

  return (
    <div className="grid gap-4">
      <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base font-semibold">Devices</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Choose mic and speaker.
              </p>
            </div>
            <StatusBadge tone={mapStatusTone(deviceStatus.tone)}>
              {deviceStatus.label}
            </StatusBadge>
          </div>
        </CardHeader>

        <CardContent className="grid gap-4 px-5 py-5">
          <div className="grid gap-4 lg:grid-cols-2">
            <SelectControl
              fieldName="audio_input_device"
              label="Mic"
              icon="mic"
              value={settingValue(state, "audio_input_device") || "default"}
              options={state.audioInputDeviceOptions}
              labels={state.audioInputDeviceLabels}
              helperText="Live."
              open={openSelect === "audio_input_device"}
              onToggle={() => onToggleSelect("audio_input_device")}
              onSelect={(value) => onSelectValue("audio_input_device", value)}
            />

            <SelectControl
              fieldName="audio_output_device"
              label="Speaker"
              icon="headphones"
              value={settingValue(state, "audio_output_device") || "default"}
              options={state.audioOutputDeviceOptions}
              labels={state.audioOutputDeviceLabels}
              helperText="Replies."
              open={openSelect === "audio_output_device"}
              onToggle={() => onToggleSelect("audio_output_device")}
              onSelect={(value) => onSelectValue("audio_output_device", value)}
            />
          </div>
        </CardContent>

        <CardFooter className="flex-wrap gap-3 border-t border-border px-5 py-4">
          <GlanceButton
            icon="refresh"
            variant="secondary"
            onClick={() => onRunAction("refreshAudioDevices")}
          >
            Refresh
          </GlanceButton>
          <GlanceButton
            icon={state.speakerTestActive ? "stop" : "play"}
            variant={state.speakerTestActive ? "primary" : "secondary"}
            onClick={() =>
              onRunAction(
                state.speakerTestActive ? "stopSpeakerTest" : "playSpeakerTest",
              )
            }
          >
            {state.speakerTestActive ? "Stop Speaker Test" : "Test Speakers"}
          </GlanceButton>
          <div className="min-w-0 flex-1 text-sm text-muted-foreground">
            {state.audioDeviceStatusMessage}
          </div>
        </CardFooter>
      </Card>

      <Card className="shell-surface gap-0 overflow-hidden rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <div>
            <CardTitle className="text-base font-semibold">Listening</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Mic, pauses, reply.
            </p>
          </div>
        </CardHeader>

        <CardContent className="grid gap-5 px-5 py-5">
          <div className="grid gap-4 xl:grid-cols-[minmax(19rem,1.5fr)_minmax(15rem,0.9fr)_minmax(15rem,0.9fr)]">
            <div className="audio-listening-panel audio-listening-panel--mic">
              <div className="flex min-w-0 items-start gap-4">
                <span className="audio-listening-icon">
                  <Icon name="mic" className="size-8" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-[var(--text-muted)]">Microphone</div>
                  <div className="mt-1 truncate text-base font-semibold text-[var(--text-strong)]">
                    {inputLabel}
                  </div>
                  <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                    <span className="audio-listening-status">
                      <span className="audio-listening-status__dot" />
                      {state.audioInputTestActive ? levelTone(audioLevel) : "Ready"}
                    </span>
                    <GlanceButton
                      icon={state.audioInputTestActive ? "stop" : "mic"}
                      variant={state.audioInputTestActive ? "primary" : "secondary"}
                      onClick={() =>
                        onRunAction(
                          state.audioInputTestActive
                            ? "stopAudioInputTest"
                            : "startAudioInputTest",
                        )
                      }
                    >
                      {state.audioInputTestActive ? "Stop test" : "Start mic test"}
                    </GlanceButton>
                  </div>
                </div>
              </div>

              <div className="border-t border-[var(--panel-divider)] pt-4">
                <div className="mb-2 flex items-center justify-between gap-3 text-sm text-[var(--text-muted)]">
                  <span>Live level</span>
                  <span className="audio-listening-pill">
                    {state.audioInputTestActive ? percent(audioLevel) : "Mic test off"}
                  </span>
                </div>
                <div className="flex h-9 items-center gap-1.5">
                  {Array.from({ length: levelSegments }).map((_, index) => (
                    <span
                      key={index}
                      className={cn(
                        "audio-level-bar",
                        index < filledSegments && "is-active",
                      )}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="audio-listening-panel audio-listening-panel--choice">
              <div className="text-base font-semibold text-[var(--text-strong)]">
                Patience
              </div>
              <div className="audio-segmented" role="radiogroup" aria-label="Patience">
                {(["fast", "balanced", "patient"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={cn(
                      "audio-segmented__item",
                      patience === option && "is-selected",
                    )}
                    role="radio"
                    aria-checked={patience === option}
                    onClick={() => onSelectValue("audio_endpoint_patience", option)}
                  >
                    {PATIENCE_LABELS[option]}
                  </button>
                ))}
              </div>
              <div className="flex items-start gap-2 text-sm leading-6 text-[var(--text-muted)]">
                <Icon name="timer" className="mt-0.5 size-4 shrink-0 text-[var(--accent-strong)]" />
                <span>{PATIENCE_COPY[patience] ?? PATIENCE_COPY.balanced}</span>
              </div>
            </div>

            <div className="audio-listening-panel audio-listening-panel--clarity">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-base font-semibold text-[var(--text-strong)]">
                    Speech strictness
                  </div>
                  <div className="mt-1 text-sm text-[var(--text-muted)]">
                    {clarityLabel(clarityValue)}
                  </div>
                </div>
                <span className="audio-listening-pill">
                  {Math.round(clarityValue * 100)}%
                </span>
              </div>
              <p className="audio-clarity-copy">
                Softer catches quiet speech. Clearer ignores more background sound.
              </p>
              <div className="audio-clarity-control">
                <input
                  className="audio-range h-5 w-full"
                  type="range"
                  min={0.05}
                  max={0.95}
                  step={0.05}
                  value={clarityValue}
                  style={{
                    "--range-fill": sliderPercent(
                      getDraftValue("audio_vad_threshold"),
                      0.05,
                      0.95,
                    ),
                  } as CSSProperties}
                  aria-label="Speech strictness"
                  onChange={(event) =>
                    onDraftChange("audio_vad_threshold", event.currentTarget.value)
                  }
                  onMouseUp={(event) =>
                    onDraftCommit("audio_vad_threshold", event.currentTarget.value)
                  }
                  onTouchEnd={(event) =>
                    onDraftCommit("audio_vad_threshold", event.currentTarget.value)
                  }
                  onFocus={() => onDraftFocus("audio_vad_threshold")}
                />
                <div className="flex items-center justify-between text-sm text-[var(--text-muted)]">
                  <span>Softer</span>
                  <span>Clearer</span>
                </div>
                {state.errors.audio_vad_threshold ? (
                  <p className="text-xs text-red-300">{state.errors.audio_vad_threshold}</p>
                ) : null}
              </div>
            </div>
          </div>

          <div className="border-t border-[var(--panel-divider)] pt-5">
            <div className="mb-4 flex items-center gap-2">
              <div className="text-base font-semibold text-[var(--text-strong)]">
                Advanced
              </div>
              {timingStatus ? (
                <span className="audio-listening-pill">
                  {timingStatus.label}
                </span>
              ) : null}
            </div>
            <div className="grid gap-5 lg:grid-cols-3">
              <CompactTimingControl
                fieldName="audio_max_wait_seconds"
                label="Start window"
                suffix="s"
                step={0.5}
                min={0.5}
                visualMax={60}
                enabled={waitEnabled}
                value={getDraftValue("audio_max_wait_seconds")}
                errorText={state.errors.audio_max_wait_seconds}
                onToggleEnabled={() =>
                  onSetField("audio_wait_for_speech_enabled", !waitEnabled)
                }
                onChange={(value) => onDraftChange("audio_max_wait_seconds", value)}
                onCommit={(value) => onDraftCommit("audio_max_wait_seconds", value)}
                onFocus={() => onDraftFocus("audio_max_wait_seconds")}
              />

              <CompactTimingControl
                fieldName="audio_max_record_seconds"
                label="Max turn"
                suffix="s"
                step={1}
                min={1}
                visualMax={180}
                enabled={maxRecordEnabled}
                value={getDraftValue("audio_max_record_seconds")}
                errorText={state.errors.audio_max_record_seconds}
                onToggleEnabled={() =>
                  onSetField("audio_max_turn_length_enabled", !maxRecordEnabled)
                }
                onChange={(value) => onDraftChange("audio_max_record_seconds", value)}
                onCommit={(value) => onDraftCommit("audio_max_record_seconds", value)}
                onFocus={() => onDraftFocus("audio_max_record_seconds")}
              />

              <CompactTimingControl
                fieldName="audio_preroll_seconds"
                label="Pre-roll"
                suffix="s"
                step={0.05}
                min={0}
                visualMax={1.5}
                enabled={prerollEnabled}
                value={getDraftValue("audio_preroll_seconds")}
                errorText={state.errors.audio_preroll_seconds}
                onToggleEnabled={() => onSetField("audio_preroll_enabled", !prerollEnabled)}
                onChange={(value) => onDraftChange("audio_preroll_seconds", value)}
                onCommit={(value) => onDraftCommit("audio_preroll_seconds", value)}
                onFocus={() => onDraftFocus("audio_preroll_seconds")}
              />
            </div>
          </div>
        </CardContent>

        <CardFooter className="justify-end border-t border-border px-5 py-4">
          <GlanceButton
            icon="undo"
            variant="ghost"
            onClick={() => onRunAction("resetAudioDefaults")}
          >
            Reset audio settings
          </GlanceButton>
        </CardFooter>
      </Card>
    </div>
  );
}
