import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { MicThreshold } from "../ui/mic-threshold";
import { NumberInput } from "../ui/number-input";
import { SelectInput } from "../ui/select-input";

import { type SettingsTabProps, settingValue } from "./shared";

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
  return (
    <div className="stack">
      <Card
        title="Devices"
        description="Choose input and output devices."
        footer={
          <div className="card-actions">
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
              onClick={() =>
                onRunAction(
                  state.speakerTestActive ? "stopSpeakerTest" : "playSpeakerTest",
                )
              }
            />
            <div className="inline-note inline-note--end">{state.audioDeviceStatusMessage}</div>
          </div>
        }
      >
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
      </Card>

      <Card
        title="Mic Threshold"
        footer={
          <div className="card-actions">
            <Button
              label={state.audioInputTestActive ? "Stop Mic Test" : "Start Mic Test"}
              icon={state.audioInputTestActive ? "stop" : "mic"}
              variant="signal"
              onClick={() =>
                onRunAction(
                  state.audioInputTestActive
                    ? "stopAudioInputTest"
                    : "startAudioInputTest",
                )
              }
            />
          </div>
        }
      >
        <MicThreshold
          level={audioLevel}
          threshold={thresholdValue}
          active={state.audioInputTestActive}
          onPointerDown={onThresholdPointerDown}
          onNudge={onThresholdNudge}
        />
      </Card>

      <Card
        title="Timing"
        description="Set how long Glance waits, listens, and keeps pre-roll."
        footer={
          <div className="card-actions card-actions--end">
            <Button
              label="Reset audio settings"
              icon="undo"
              variant="ghost"
              onClick={() => onRunAction("resetAudioDefaults")}
            />
          </div>
        }
      >
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
      </Card>
    </div>
  );
}
