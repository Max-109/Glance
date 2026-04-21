import { NumberInput } from "../ui/number-input";
import { Panel } from "../ui/panel";

import type { SettingsTabProps } from "./shared";

type CaptureTone = "accent" | "soft" | "neutral";

function parseCapture(raw: string): number {
  const value = Number.parseFloat(raw);
  return Number.isFinite(value) ? value : 0;
}

function computeCaptureStatus(values: {
  interval: number;
  batch: number;
  threshold: number;
}): { tone: CaptureTone; label: string } | null {
  const { interval, batch, threshold } = values;
  if (interval > 0 && interval <= 1 && batch <= 3 && threshold <= 0.1) {
    return { tone: "accent", label: "Real-time capture" };
  }
  if (interval >= 4 || batch >= 8) {
    return { tone: "soft", label: "Easy on the CPU" };
  }
  if (threshold >= 0.35) {
    return { tone: "neutral", label: "Only big changes" };
  }
  return null;
}

export function CaptureTab({
  state,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  getDraftValue,
}: Pick<
  SettingsTabProps,
  "state" | "onDraftChange" | "onDraftCommit" | "onDraftFocus" | "getDraftValue"
>) {
  const interval = parseCapture(getDraftValue("screenshot_interval"));
  const batch = parseCapture(getDraftValue("batch_window_duration"));
  const threshold = parseCapture(getDraftValue("screen_change_threshold"));
  const status = computeCaptureStatus({ interval, batch, threshold });

  return (
    <div className="stack">
      <Panel
        title="Capture"
        description="Pick how often Glance looks at the screen and how it groups quick changes."
        status={status}
      >
        <div className="field-grid field-grid--two-column">
          <NumberInput
            fieldName="screenshot_interval"
            label="Capture Interval"
            icon="timer"
            suffix="s"
            inputMode="decimal"
            step={0.1}
            min={0.1}
            value={getDraftValue("screenshot_interval")}
            errorText={state.errors.screenshot_interval}
            helperText="Time between screenshots."
            onChange={(value) => onDraftChange("screenshot_interval", value)}
            onCommit={(value) => onDraftCommit("screenshot_interval", value)}
            onFocus={() => onDraftFocus("screenshot_interval")}
          />

          <NumberInput
            fieldName="batch_window_duration"
            label="Batch Window"
            icon="timer"
            suffix="s"
            inputMode="decimal"
            step={0.5}
            min={0.5}
            value={getDraftValue("batch_window_duration")}
            errorText={state.errors.batch_window_duration}
            helperText="How long to wait before grouping changes."
            onChange={(value) => onDraftChange("batch_window_duration", value)}
            onCommit={(value) => onDraftCommit("batch_window_duration", value)}
            onFocus={() => onDraftFocus("batch_window_duration")}
          />
        </div>

        <NumberInput
          fieldName="screen_change_threshold"
          label="Change Threshold"
          icon="gauge"
          inputMode="decimal"
          step={0.01}
          min={0.01}
          max={1}
          value={getDraftValue("screen_change_threshold")}
          errorText={state.errors.screen_change_threshold}
          helperText="How much of the screen needs to change before Glance reacts."
          onChange={(value) => onDraftChange("screen_change_threshold", value)}
          onCommit={(value) => onDraftCommit("screen_change_threshold", value)}
          onFocus={() => onDraftFocus("screen_change_threshold")}
        />
      </Panel>
    </div>
  );
}
