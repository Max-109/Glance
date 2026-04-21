import { Card } from "../ui/card";
import { NumberInput } from "../ui/number-input";

import type { SettingsTabProps } from "./shared";

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
  return (
    <Card
      title="Capture"
      description="Set how often Glance captures the screen and how long it waits before grouping changes."
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
          helperText="How long Glance waits before grouping changes."
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
        helperText="How much the screen must change before Glance reacts."
        onChange={(value) => onDraftChange("screen_change_threshold", value)}
        onCommit={(value) => onDraftCommit("screen_change_threshold", value)}
        onFocus={() => onDraftFocus("screen_change_threshold")}
      />
    </Card>
  );
}
