import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NumberField } from "@/components/settings-shell/form-controls";
import { StatusBadge, type StatusTone } from "@/components/settings-shell/status-badge";

import type { SettingsTabProps } from "./shared";

function parseCapture(raw: string): number {
  const value = Number.parseFloat(raw);
  return Number.isFinite(value) ? value : 0;
}

function computeCaptureStatus(values: {
  interval: number;
  batch: number;
  threshold: number;
}): { tone: StatusTone; label: string } | null {
  const { interval, batch, threshold } = values;
  if (interval > 0 && interval <= 1 && batch <= 3 && threshold <= 0.1) {
    return { tone: "accent", label: "Real-time capture" };
  }
  if (interval >= 4 || batch >= 8) {
    return { tone: "neutral", label: "Easy on CPU" };
  }
  if (threshold >= 0.35) {
    return { tone: "neutral", label: "Large changes" };
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
    <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
      <CardHeader className="border-b border-border px-5 py-4">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base font-semibold">Capture</CardTitle>
            <CardDescription>
              Pick how often Glance looks at the screen and groups quick changes.
            </CardDescription>
          </div>
          {status ? <StatusBadge tone={status.tone}>{status.label}</StatusBadge> : null}
        </div>
      </CardHeader>

      <CardContent className="grid gap-4 px-5 py-5">
        <div className="grid gap-4 lg:grid-cols-2">
          <NumberField
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

          <NumberField
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

        <NumberField
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
      </CardContent>
    </Card>
  );
}
