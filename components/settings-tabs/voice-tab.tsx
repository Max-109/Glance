import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { SelectInput } from "../ui/select-input";

import {
  LANGUAGE_LABELS,
  type SettingsTabProps,
  settingValue,
} from "./shared";

export function VoiceTab({
  state,
  openSelect,
  onToggleSelect,
  onSelectValue,
  onRunAction,
}: Pick<
  SettingsTabProps,
  "state" | "openSelect" | "onToggleSelect" | "onSelectValue" | "onRunAction"
>) {
  const selectedVoice = settingValue(state, "tts_voice_id") || state.voiceOptions[0] || "";
  const previewActiveForVoice =
    state.previewActive && state.previewingVoice === selectedVoice;

  return (
    <Card
      title="Voice"
      description="Choose a voice and set a default language."
    >
      <SelectInput
        fieldName="tts_voice_id"
        label="Voice"
        icon="speaker"
        value={selectedVoice}
        options={state.voiceOptions}
        labels={state.voiceOptionLabels}
        helperText="Auto chooses a voice for each reply. Preview only works for fixed voices."
        open={openSelect === "tts_voice_id"}
        onToggle={() => onToggleSelect("tts_voice_id")}
        onSelect={(value) => onSelectValue("tts_voice_id", value)}
        actionSlot={
          <Button
            label={previewActiveForVoice ? "Stop" : "Preview"}
            icon={previewActiveForVoice ? "stop" : "play"}
            variant={previewActiveForVoice ? "ghost" : "secondary"}
            disabled={selectedVoice === "auto"}
            ariaLabel="Preview current voice"
            onClick={() => onRunAction("previewVoice", { voiceName: selectedVoice })}
          />
        }
      />

      <SelectInput
        fieldName="fallback_language"
        label="Default Language"
        icon="languages"
        value={settingValue(state, "fallback_language") || "en"}
        options={state.languageOptions}
        labels={LANGUAGE_LABELS}
        helperText="Used when Glance needs a default language."
        open={openSelect === "fallback_language"}
        onToggle={() => onToggleSelect("fallback_language")}
        onSelect={(value) => onSelectValue("fallback_language", value)}
      />
    </Card>
  );
}
