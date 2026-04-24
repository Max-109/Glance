import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlanceButton } from "@/components/settings-shell/button";
import { SelectControl } from "@/components/settings-shell/form-controls";
import { StatusBadge, type StatusTone } from "@/components/settings-shell/status-badge";
import { TimingControl } from "@/components/settings-shell/timing-control";
import { MicThreshold } from "@/components/ui/mic-threshold";

import { type SettingsTabProps, settingValue } from "./shared";

type DeviceTone = "ready" | "fallback" | "missing" | "testing";
type TimingTone = "responsive" | "patient" | "custom";

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
  silence: number;
  wait: number;
  maxRecord: number;
  preroll: number;
  enabledCount: number;
}): { tone: TimingTone; label: string } | null {
  const { silence, wait, maxRecord, preroll, enabledCount } = values;
  if (enabledCount === 0) {
    return { tone: "custom", label: "Manual stop" };
  }
  if (enabledCount < 4) {
    return { tone: "custom", label: "Custom profile" };
  }
  if (silence <= 1 && wait <= 20 && maxRecord <= 60 && preroll <= 0.6) {
    return { tone: "responsive", label: "Fast turns" };
  }
  if (silence >= 2.5 || wait >= 40 || maxRecord >= 180) {
    return { tone: "patient", label: "Patient mode" };
  }
  if (preroll >= 1.2 || maxRecord >= 120) {
    return { tone: "custom", label: "Custom profile" };
  }
  return null;
}

export function AudioTab({
  state,
  openSelect,
  thresholdValue,
  audioLevel,
  onToggleSelect,
  onSelectValue,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onRunAction,
  onSetField,
  onThresholdPointerDown,
  onThresholdNudge,
  getDraftValue,
}: Pick<
  SettingsTabProps,
  | "state"
  | "openSelect"
  | "thresholdValue"
  | "audioLevel"
  | "onToggleSelect"
  | "onSelectValue"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onRunAction"
  | "onSetField"
  | "onThresholdPointerDown"
  | "onThresholdNudge"
  | "getDraftValue"
>) {
  const deviceStatus = computeDeviceStatus(state);
  const silence = parseTiming(getDraftValue("audio_silence_seconds"));
  const wait = parseTiming(getDraftValue("audio_max_wait_seconds"));
  const maxRecord = parseTiming(getDraftValue("audio_max_record_seconds"));
  const preroll = parseTiming(getDraftValue("audio_preroll_seconds"));
  const silenceEnabled = true;
  const waitEnabled = settingBoolean(state, "audio_wait_for_speech_enabled");
  const maxRecordEnabled = settingBoolean(state, "audio_max_turn_length_enabled");
  const prerollEnabled = settingBoolean(state, "audio_preroll_enabled");
  const enabledCount = [
    silenceEnabled,
    waitEnabled,
    maxRecordEnabled,
    prerollEnabled,
  ].filter(Boolean).length;
  const timingStatus = computeTimingStatus({
    silence,
    wait,
    maxRecord,
    preroll,
    enabledCount,
  });

  return (
    <div className="grid gap-4">
      <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base font-semibold">Devices</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Choose input and output devices.
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
              label="Input Device"
              icon="mic"
              value={settingValue(state, "audio_input_device") || "default"}
              options={state.audioInputDeviceOptions}
              labels={state.audioInputDeviceLabels}
              helperText="Used for Live and mic test."
              open={openSelect === "audio_input_device"}
              onToggle={() => onToggleSelect("audio_input_device")}
              onSelect={(value) => onSelectValue("audio_input_device", value)}
            />

            <SelectControl
              fieldName="audio_output_device"
              label="Output Device"
              icon="headphones"
              value={settingValue(state, "audio_output_device") || "default"}
              options={state.audioOutputDeviceOptions}
              labels={state.audioOutputDeviceLabels}
              helperText="Used for replies and previews."
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

      <MicThreshold
        level={audioLevel}
        threshold={thresholdValue}
        active={state.audioInputTestActive}
        onPointerDown={onThresholdPointerDown}
        onNudge={onThresholdNudge}
        onToggleTest={() =>
          onRunAction(
            state.audioInputTestActive
              ? "stopAudioInputTest"
              : "startAudioInputTest",
          )
        }
      />

      <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base font-semibold">Timing</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Choose what stops a live turn and how much audio Glance keeps.
              </p>
            </div>
            {timingStatus ? (
              <StatusBadge tone={mapStatusTone(timingStatus.tone)}>
                {timingStatus.label}
              </StatusBadge>
            ) : null}
          </div>
        </CardHeader>

        <CardContent className="grid gap-4 px-5 py-5">
          <div className="grid gap-4 lg:grid-cols-2">
            <TimingControl
              fieldName="audio_silence_seconds"
              label="Silence Timeout"
              icon="timer"
              suffix="s"
              step={0.1}
              min={0.1}
              visualMax={3}
              enabled={silenceEnabled}
              value={getDraftValue("audio_silence_seconds")}
              errorText={state.errors.audio_silence_seconds}
              helperText="Ends a turn after the speaker goes quiet."
              onChange={(value) => onDraftChange("audio_silence_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_silence_seconds", value)}
              onFocus={() => onDraftFocus("audio_silence_seconds")}
            />

            <TimingControl
              fieldName="audio_max_wait_seconds"
              label="Wait for Speech"
              icon="timer"
              suffix="s"
              step={0.5}
              min={0.5}
              visualMax={60}
              enabled={waitEnabled}
              value={getDraftValue("audio_max_wait_seconds")}
              errorText={state.errors.audio_max_wait_seconds}
              helperText="Gives Live a window to hear the first word."
              onToggleEnabled={() =>
                onSetField("audio_wait_for_speech_enabled", !waitEnabled)
              }
              onChange={(value) => onDraftChange("audio_max_wait_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_max_wait_seconds", value)}
              onFocus={() => onDraftFocus("audio_max_wait_seconds")}
            />

            <TimingControl
              fieldName="audio_max_record_seconds"
              label="Max Turn Length"
              icon="gauge"
              suffix="s"
              step={1}
              min={1}
              visualMax={180}
              enabled={maxRecordEnabled}
              value={getDraftValue("audio_max_record_seconds")}
              errorText={state.errors.audio_max_record_seconds}
              helperText="Stops a recording that runs too long."
              onToggleEnabled={() =>
                onSetField("audio_max_turn_length_enabled", !maxRecordEnabled)
              }
              onChange={(value) => onDraftChange("audio_max_record_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_max_record_seconds", value)}
              onFocus={() => onDraftFocus("audio_max_record_seconds")}
            />

            <TimingControl
              fieldName="audio_preroll_seconds"
              label="Pre-Roll"
              icon="rewind"
              suffix="s"
              step={0.05}
              min={0}
              visualMax={1.5}
              enabled={prerollEnabled}
              value={getDraftValue("audio_preroll_seconds")}
              errorText={state.errors.audio_preroll_seconds}
              helperText="Keeps a little audio from right before speech starts."
              onToggleEnabled={() => onSetField("audio_preroll_enabled", !prerollEnabled)}
              onChange={(value) => onDraftChange("audio_preroll_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_preroll_seconds", value)}
              onFocus={() => onDraftFocus("audio_preroll_seconds")}
            />
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
