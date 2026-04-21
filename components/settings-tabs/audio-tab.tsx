import { Button } from "../ui/button";
import { MicThreshold } from "../ui/mic-threshold";
import { NumberInput } from "../ui/number-input";
import { SelectInput } from "../ui/select-input";

import { type SettingsTabProps, settingValue } from "./shared";

type DeviceTone = "ready" | "fallback" | "missing" | "testing";
type TimingTone = "responsive" | "patient" | "custom";

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
    return { tone: "fallback", label: "Using system defaults" };
  }
  return { tone: "ready", label: "Ready" };
}

function parseTiming(raw: string): number {
  const value = Number.parseFloat(raw);
  return Number.isFinite(value) ? value : 0;
}

function computeTimingStatus(values: {
  silence: number;
  wait: number;
  maxRecord: number;
  preroll: number;
}): { tone: TimingTone; label: string } | null {
  const { silence, wait, maxRecord, preroll } = values;
  if (silence <= 1 && wait <= 20 && maxRecord <= 60 && preroll <= 0.6) {
    return { tone: "responsive", label: "Tuned for fast turns" };
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
  | "onThresholdPointerDown"
  | "onThresholdNudge"
  | "getDraftValue"
>) {
  const deviceStatus = computeDeviceStatus(state);

  const silence = parseTiming(getDraftValue("audio_silence_seconds"));
  const wait = parseTiming(getDraftValue("audio_max_wait_seconds"));
  const maxRecord = parseTiming(getDraftValue("audio_max_record_seconds"));
  const preroll = parseTiming(getDraftValue("audio_preroll_seconds"));
  const timingStatus = computeTimingStatus({ silence, wait, maxRecord, preroll });

  return (
    <div className="stack">
      <section className={`audio-panel audio-panel--devices`}>
        <div className={`audio-panel__status audio-panel__status--${deviceStatus.tone}`}>
          <span className="audio-panel__status-dot" />
          <span>{deviceStatus.label}</span>
        </div>

        <div className="audio-panel__toolbar audio-panel__toolbar--solo">
          <div className="audio-panel__toolbar-heading">
            <span className="audio-panel__toolbar-title">Devices</span>
            <p className="audio-panel__toolbar-copy">Choose input and output devices.</p>
          </div>
        </div>

        <div className="audio-panel__body">
          <div className="field-grid field-grid--two-column">
            <SelectInput
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

            <SelectInput
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
        </div>

        <div className="audio-panel__chips">
          <Button
            label="Refresh"
            icon="refresh"
            variant="secondary"
            onClick={() => onRunAction("refreshAudioDevices")}
          />
          <Button
            label={state.speakerTestActive ? "Stop Speaker Test" : "Test Speakers"}
            icon={state.speakerTestActive ? "stop" : "play"}
            variant={state.speakerTestActive ? "signal" : "secondary"}
            active={state.speakerTestActive}
            onClick={() =>
              onRunAction(
                state.speakerTestActive ? "stopSpeakerTest" : "playSpeakerTest",
              )
            }
          />
          <div className="inline-note inline-note--end">{state.audioDeviceStatusMessage}</div>
        </div>
      </section>

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

      <section className={`audio-panel audio-panel--timing`}>
        {timingStatus ? (
          <div className={`audio-panel__status audio-panel__status--${timingStatus.tone}`}>
            <span className="audio-panel__status-dot" />
            <span>{timingStatus.label}</span>
          </div>
        ) : null}

        <div className="audio-panel__toolbar audio-panel__toolbar--solo">
          <div className="audio-panel__toolbar-heading">
            <span className="audio-panel__toolbar-title">Timing</span>
            <p className="audio-panel__toolbar-copy">
              Set how long Glance waits, listens, and keeps pre-roll.
            </p>
          </div>
        </div>

        <div className="audio-panel__body">
          <div className="field-grid field-grid--two-column">
            <NumberInput
              fieldName="audio_silence_seconds"
              label="Silence Timeout"
              icon="timer"
              suffix="s"
              inputMode="decimal"
              step={0.1}
              min={0.1}
              value={getDraftValue("audio_silence_seconds")}
              errorText={state.errors.audio_silence_seconds}
              helperText="How much silence ends the current turn."
              onChange={(value) => onDraftChange("audio_silence_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_silence_seconds", value)}
              onFocus={() => onDraftFocus("audio_silence_seconds")}
            />

            <NumberInput
              fieldName="audio_max_wait_seconds"
              label="Wait for Speech"
              icon="timer"
              suffix="s"
              inputMode="decimal"
              step={0.5}
              min={0.5}
              value={getDraftValue("audio_max_wait_seconds")}
              errorText={state.errors.audio_max_wait_seconds}
              helperText="How long live mode waits before it goes idle."
              onChange={(value) => onDraftChange("audio_max_wait_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_max_wait_seconds", value)}
              onFocus={() => onDraftFocus("audio_max_wait_seconds")}
            />

            <NumberInput
              fieldName="audio_max_record_seconds"
              label="Max Turn Length"
              icon="timer"
              suffix="s"
              inputMode="decimal"
              step={1}
              min={1}
              value={getDraftValue("audio_max_record_seconds")}
              errorText={state.errors.audio_max_record_seconds}
              helperText="Hard limit for one spoken turn."
              onChange={(value) => onDraftChange("audio_max_record_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_max_record_seconds", value)}
              onFocus={() => onDraftFocus("audio_max_record_seconds")}
            />

            <NumberInput
              fieldName="audio_preroll_seconds"
              label="Pre-Roll"
              icon="rewind"
              suffix="s"
              inputMode="decimal"
              step={0.05}
              min={0}
              value={getDraftValue("audio_preroll_seconds")}
              errorText={state.errors.audio_preroll_seconds}
              helperText="Audio kept right before speech starts."
              onChange={(value) => onDraftChange("audio_preroll_seconds", value)}
              onCommit={(value) => onDraftCommit("audio_preroll_seconds", value)}
              onFocus={() => onDraftFocus("audio_preroll_seconds")}
            />
          </div>
        </div>

        <div className="audio-panel__chips audio-panel__chips--end">
          <Button
            label="Reset audio settings"
            icon="undo"
            variant="ghost"
            onClick={() => onRunAction("resetAudioDefaults")}
          />
        </div>
      </section>
    </div>
  );
}
