import { type PointerEvent as ReactPointerEvent } from "react";

import type { BridgeState, SectionId } from "@/lib/glance-bridge";

import { Button, GlassCard, SelectField, SegmentedTabs, TextField, AudioMeter } from "./ui";

type ProviderTab = "llm" | "speech" | "transcription";

const PROVIDER_TABS: Array<{ id: ProviderTab; label: string }> = [
  { id: "llm", label: "LLM" },
  { id: "speech", label: "Speech Engine" },
  { id: "transcription", label: "Transcription" },
];

const REASONING_LABELS: Record<string, string> = {
  minimal: "minimal",
  low: "low",
  medium: "medium",
  high: "high",
};

const REASONING_ICONS: Record<string, string> = {
  minimal: "clock",
  low: "zap",
  medium: "brain",
  high: "brain-circuit",
};

const TRANSCRIPTION_REASONING_ICONS: Record<string, string> = {
  minimal: "zap",
  low: "zap",
  medium: "brain",
  high: "brain-circuit",
};

const THEME_LABELS: Record<string, string> = {
  dark: "dark",
  light: "light",
  system: "system",
};

function settingValue(state: BridgeState, fieldName: string): string {
  const value = state.settings[fieldName];
  return value === null || value === undefined ? "" : String(value);
}

interface SettingsSectionsProps {
  state: BridgeState;
  providerTab: ProviderTab;
  openSelect: string | null;
  thresholdValue: number;
  audioLevel: number;
  revealedFields: Record<string, boolean>;
  onChangeProviderTab: (tab: ProviderTab) => void;
  onToggleSelect: (fieldName: string) => void;
  onSelectValue: (fieldName: string, value: string) => void;
  onDraftChange: (fieldName: string, value: string) => void;
  onDraftCommit: (fieldName: string, value: string) => void;
  onDraftFocus: (fieldName: string) => void;
  onToggleReveal: (fieldName: string) => void;
  onRunAction: (
    action: string,
    payload?: Record<string, string | number | boolean>,
  ) => void;
  onThresholdPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  getDraftValue: (fieldName: string) => string;
}

export function SettingsSections({
  state,
  providerTab,
  openSelect,
  thresholdValue,
  audioLevel,
  revealedFields,
  onChangeProviderTab,
  onToggleSelect,
  onSelectValue,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onToggleReveal,
  onRunAction,
  onThresholdPointerDown,
  getDraftValue,
}: SettingsSectionsProps) {
  if (state.currentSection === "api") {
    return (
      <ApiSection
        state={state}
        providerTab={providerTab}
        openSelect={openSelect}
        revealedFields={revealedFields}
        onChangeProviderTab={onChangeProviderTab}
        onToggleSelect={onToggleSelect}
        onSelectValue={onSelectValue}
        onDraftChange={onDraftChange}
        onDraftCommit={onDraftCommit}
        onDraftFocus={onDraftFocus}
        onToggleReveal={onToggleReveal}
        getDraftValue={getDraftValue}
      />
    );
  }

  if (state.currentSection === "voice") {
    return (
      <VoiceSection
        state={state}
        openSelect={openSelect}
        onToggleSelect={onToggleSelect}
        onSelectValue={onSelectValue}
        onRunAction={onRunAction}
      />
    );
  }

  if (state.currentSection === "capture") {
    return (
      <CaptureSection
        state={state}
        onDraftChange={onDraftChange}
        onDraftCommit={onDraftCommit}
        onDraftFocus={onDraftFocus}
        getDraftValue={getDraftValue}
      />
    );
  }

  if (state.currentSection === "audio") {
    return (
      <AudioSection
        state={state}
        openSelect={openSelect}
        thresholdValue={thresholdValue}
        audioLevel={audioLevel}
        onToggleSelect={onToggleSelect}
        onSelectValue={onSelectValue}
        onDraftChange={onDraftChange}
        onDraftCommit={onDraftCommit}
        onDraftFocus={onDraftFocus}
        onRunAction={onRunAction}
        onThresholdPointerDown={onThresholdPointerDown}
        getDraftValue={getDraftValue}
      />
    );
  }

  if (state.currentSection === "history") {
    return (
      <HistorySection
        state={state}
        onDraftChange={onDraftChange}
        onDraftCommit={onDraftCommit}
        onDraftFocus={onDraftFocus}
        onRunAction={onRunAction}
        getDraftValue={getDraftValue}
      />
    );
  }

  return (
    <GeneralSection
      state={state}
      openSelect={openSelect}
      onToggleSelect={onToggleSelect}
      onSelectValue={onSelectValue}
      onDraftChange={onDraftChange}
      onDraftCommit={onDraftCommit}
      onDraftFocus={onDraftFocus}
      getDraftValue={getDraftValue}
    />
  );
}

function ApiSection({
  state,
  providerTab,
  openSelect,
  revealedFields,
  onChangeProviderTab,
  onToggleSelect,
  onSelectValue,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onToggleReveal,
  getDraftValue,
}: Omit<
  SettingsSectionsProps,
  | "onRunAction"
  | "thresholdValue"
  | "audioLevel"
  | "onThresholdPointerDown"
>) {
  return (
    <GlassCard
      title="Providers"
      description="Different settings for different parts of pipeline."
    >
      <SegmentedTabs
        tabs={PROVIDER_TABS}
        activeTab={providerTab}
        onChange={(tab) => onChangeProviderTab(tab as ProviderTab)}
      />

      {providerTab === "llm" ? (
        <div className="stack">
          <TextField
            fieldName="llm_base_url"
            label="Base URL"
            icon="api"
            inputMode="url"
            value={getDraftValue("llm_base_url")}
            errorText={state.errors.llm_base_url}
            helperText="Full URL for your LLM API endpoint."
            onChange={(value) => onDraftChange("llm_base_url", value)}
            onCommit={(value) => onDraftCommit("llm_base_url", value)}
            onFocus={() => onDraftFocus("llm_base_url")}
          />

          <TextField
            fieldName="llm_api_key"
            label="Key for the API"
            icon="key"
            value={getDraftValue("llm_api_key")}
            helperText="Saved locally on this device."
            secret
            revealed={Boolean(revealedFields.llm_api_key)}
            onChange={(value) => onDraftChange("llm_api_key", value)}
            onCommit={(value) => onDraftCommit("llm_api_key", value)}
            onFocus={() => onDraftFocus("llm_api_key")}
            onToggleReveal={() => onToggleReveal("llm_api_key")}
          />

          <div className="field-grid field-grid--two-column">
            <TextField
              fieldName="llm_model_name"
              label="Model"
              icon="bot"
              value={getDraftValue("llm_model_name")}
              errorText={state.errors.llm_model_name}
              helperText="Model name to use for responses."
              onChange={(value) => onDraftChange("llm_model_name", value)}
              onCommit={(value) => onDraftCommit("llm_model_name", value)}
              onFocus={() => onDraftFocus("llm_model_name")}
            />

            <SelectField
              fieldName="llm_reasoning"
              label="Reasoning"
              icon="brain"
              value={settingValue(state, "llm_reasoning") || "medium"}
              options={state.reasoningOptions}
              labels={REASONING_LABELS}
              optionIcons={REASONING_ICONS}
              helperText="Reasoning effort for replies."
              open={openSelect === "llm_reasoning"}
              onToggle={() => onToggleSelect("llm_reasoning")}
              onSelect={(value) => onSelectValue("llm_reasoning", value)}
            />
          </div>
        </div>
      ) : null}

      {providerTab === "speech" ? (
        <div className="stack">
          <TextField
            fieldName="tts_base_url"
            label="Base URL"
            icon="api"
            inputMode="url"
            value={getDraftValue("tts_base_url")}
            errorText={state.errors.tts_base_url}
            helperText="Full URL for your speech API endpoint."
            onChange={(value) => onDraftChange("tts_base_url", value)}
            onCommit={(value) => onDraftCommit("tts_base_url", value)}
            onFocus={() => onDraftFocus("tts_base_url")}
          />

          <div className="field-grid field-grid--two-column">
            <TextField
              fieldName="tts_api_key"
              label="Key for the API"
              icon="key"
              value={getDraftValue("tts_api_key")}
              helperText="Saved locally on this device."
              secret
              revealed={Boolean(revealedFields.tts_api_key)}
              onChange={(value) => onDraftChange("tts_api_key", value)}
              onCommit={(value) => onDraftCommit("tts_api_key", value)}
              onFocus={() => onDraftFocus("tts_api_key")}
              onToggleReveal={() => onToggleReveal("tts_api_key")}
            />

            <SelectField
              fieldName="tts_model"
              label="Model"
              icon="speech"
              value={settingValue(state, "tts_model") || "eleven-v3"}
              options={state.ttsModelOptions}
              helperText="Speech generation model."
              open={openSelect === "tts_model"}
              onToggle={() => onToggleSelect("tts_model")}
              onSelect={(value) => onSelectValue("tts_model", value)}
            />
          </div>
        </div>
      ) : null}

      {providerTab === "transcription" ? (
        <div className="stack">
          <TextField
            fieldName="transcription_base_url"
            label="Base URL"
            icon="api"
            inputMode="url"
            value={getDraftValue("transcription_base_url")}
            errorText={state.errors.transcription_base_url}
            helperText="Full URL for your transcription API endpoint."
            onChange={(value) => onDraftChange("transcription_base_url", value)}
            onCommit={(value) => onDraftCommit("transcription_base_url", value)}
            onFocus={() => onDraftFocus("transcription_base_url")}
          />

          <TextField
            fieldName="transcription_api_key"
            label="Key for the API"
            icon="key"
            value={getDraftValue("transcription_api_key")}
            helperText="Saved locally on this device."
            secret
            revealed={Boolean(revealedFields.transcription_api_key)}
            onChange={(value) => onDraftChange("transcription_api_key", value)}
            onCommit={(value) => onDraftCommit("transcription_api_key", value)}
            onFocus={() => onDraftFocus("transcription_api_key")}
            onToggleReveal={() => onToggleReveal("transcription_api_key")}
          />

          <div className="field-grid field-grid--two-column">
            <TextField
              fieldName="transcription_model_name"
              label="Model"
              icon="wave"
              value={getDraftValue("transcription_model_name")}
              errorText={state.errors.transcription_model_name}
              helperText="A model which is used for transcribing."
              onChange={(value) => onDraftChange("transcription_model_name", value)}
              onCommit={(value) => onDraftCommit("transcription_model_name", value)}
              onFocus={() => onDraftFocus("transcription_model_name")}
            />

            <SelectField
              fieldName="transcription_reasoning"
              label="Reasoning"
              icon="zap"
              value={settingValue(state, "transcription_reasoning") || "medium"}
              options={state.transcriptionReasoningOptions}
              labels={REASONING_LABELS}
              optionIcons={TRANSCRIPTION_REASONING_ICONS}
              helperText="Reasoning effort per turn."
              open={openSelect === "transcription_reasoning"}
              onToggle={() => onToggleSelect("transcription_reasoning")}
              onSelect={(value) => onSelectValue("transcription_reasoning", value)}
            />
          </div>
        </div>
      ) : null}
    </GlassCard>
  );
}

function VoiceSection({
  state,
  openSelect,
  onToggleSelect,
  onSelectValue,
  onRunAction,
}: Pick<
  SettingsSectionsProps,
  "state" | "openSelect" | "onToggleSelect" | "onSelectValue" | "onRunAction"
>) {
  const selectedVoice = settingValue(state, "tts_voice_id") || state.voiceOptions[0] || "";
  const previewActiveForVoice =
    state.previewActive && state.previewingVoice === selectedVoice;

  return (
    <GlassCard
      title="Speech"
      description="Choose how Glance should sound when it speaks back."
    >
      <SelectField
        fieldName="tts_voice_id"
        label="Voice"
        icon="mic"
        value={selectedVoice}
        options={state.voiceOptions}
        labels={state.voiceOptionLabels}
        helperText="Auto picks the best curated Eleven v3 voice for each reply. Use the play button to preview a fixed voice."
        open={openSelect === "tts_voice_id"}
        onToggle={() => onToggleSelect("tts_voice_id")}
        onSelect={(value) => onSelectValue("tts_voice_id", value)}
        actionSlot={
          <Button
            label={previewActiveForVoice ? "Stop" : "Preview"}
            icon={previewActiveForVoice ? "close" : "play"}
            variant="ghost"
            disabled={selectedVoice === "auto"}
            ariaLabel="Preview current voice"
            onClick={() => onRunAction("previewVoice", { voiceName: selectedVoice })}
          />
        }
      />

      <SelectField
        fieldName="fallback_language"
        label="Fallback language"
        icon="languages"
        value={settingValue(state, "fallback_language") || "en"}
        options={state.languageOptions}
        helperText="Used when the reply should be spoken in a default language."
        open={openSelect === "fallback_language"}
        onToggle={() => onToggleSelect("fallback_language")}
        onSelect={(value) => onSelectValue("fallback_language", value)}
      />
    </GlassCard>
  );
}

function CaptureSection({
  state,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  getDraftValue,
}: Pick<
  SettingsSectionsProps,
  "state" | "onDraftChange" | "onDraftCommit" | "onDraftFocus" | "getDraftValue"
>) {
  return (
    <GlassCard
      title="Capture"
      description="Control how often Glance checks the screen and groups updates."
    >
      <TextField
        fieldName="screenshot_interval"
        label="Capture interval"
        icon="clock"
        suffix="s"
        inputMode="decimal"
        value={getDraftValue("screenshot_interval")}
        errorText={state.errors.screenshot_interval}
        helperText="How often Glance checks the screen, in seconds."
        onChange={(value) => onDraftChange("screenshot_interval", value)}
        onCommit={(value) => onDraftCommit("screenshot_interval", value)}
        onFocus={() => onDraftFocus("screenshot_interval")}
      />

      <TextField
        fieldName="screen_change_threshold"
        label="Change threshold"
        icon="gauge"
        inputMode="decimal"
        value={getDraftValue("screen_change_threshold")}
        errorText={state.errors.screen_change_threshold}
        helperText="How much the screen must change before Glance reacts."
        onChange={(value) => onDraftChange("screen_change_threshold", value)}
        onCommit={(value) => onDraftCommit("screen_change_threshold", value)}
        onFocus={() => onDraftFocus("screen_change_threshold")}
      />

      <TextField
        fieldName="batch_window_duration"
        label="Batch window"
        icon="history"
        suffix="s"
        inputMode="decimal"
        value={getDraftValue("batch_window_duration")}
        errorText={state.errors.batch_window_duration}
        helperText="How long to group updates into one reply, in seconds."
        onChange={(value) => onDraftChange("batch_window_duration", value)}
        onCommit={(value) => onDraftCommit("batch_window_duration", value)}
        onFocus={() => onDraftFocus("batch_window_duration")}
      />
    </GlassCard>
  );
}

function AudioSection({
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
  getDraftValue,
}: Pick<
  SettingsSectionsProps,
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
  | "getDraftValue"
>) {
  return (
    <div className="stack">
      <GlassCard
        title="Devices"
        description="Choose the hardware Glance should use for listening and playback."
        footer={
          <div className="card-actions">
            <Button
              label="Refresh devices"
              icon="refresh"
              variant="secondary"
              onClick={() => onRunAction("refreshAudioDevices")}
            />
            <Button
              label={state.speakerTestActive ? "Stop speaker test" : "Play speaker test"}
              icon={state.speakerTestActive ? "close" : "play"}
              variant="secondary"
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
        <SelectField
          fieldName="audio_input_device"
          label="Input device"
          icon="mic"
          value={settingValue(state, "audio_input_device") || "default"}
          options={state.audioInputDeviceOptions}
          labels={state.audioInputDeviceLabels}
          helperText="Microphone used for live mode and the local mic test."
          open={openSelect === "audio_input_device"}
          onToggle={() => onToggleSelect("audio_input_device")}
          onSelect={(value) => onSelectValue("audio_input_device", value)}
        />

        <SelectField
          fieldName="audio_output_device"
          label="Output device"
          icon="headphones"
          value={settingValue(state, "audio_output_device") || "default"}
          options={state.audioOutputDeviceOptions}
          labels={state.audioOutputDeviceLabels}
          helperText="Speaker or headphones used for live replies, voice preview, and the speaker test."
          open={openSelect === "audio_output_device"}
          onToggle={() => onToggleSelect("audio_output_device")}
          onSelect={(value) => onSelectValue("audio_output_device", value)}
        />
      </GlassCard>

      <GlassCard
        title="Mic Calibration"
        description="Test the microphone and drag the trigger marker until normal speech crosses it without reacting to room noise."
        footer={
          <div className="card-actions">
            <div className="metric-chip">
              <span>Mic sensitivity</span>
              <strong>{thresholdValue.toFixed(3)}</strong>
            </div>
            <div className="metric-chip metric-chip--quiet">
              <span>Level</span>
              <strong>{audioLevel.toFixed(3)}</strong>
            </div>
            <Button
              label={state.audioInputTestActive ? "Stop mic test" : "Start mic test"}
              icon={state.audioInputTestActive ? "close" : "mic"}
              variant="secondary"
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
        <AudioMeter
          level={audioLevel}
          threshold={thresholdValue}
          active={state.audioInputTestActive}
          onPointerDown={onThresholdPointerDown}
        />

        <div className="inline-stats">
          <span>{state.audioInputTestActive ? "Meter is live while the mic test runs." : "Meter idle until the mic test starts."}</span>
          <span>Level {audioLevel.toFixed(3)} / Trigger {thresholdValue.toFixed(3)}</span>
        </div>
      </GlassCard>

      <GlassCard
        title="Turn Timing"
        description="Adjust how long Glance waits, listens, and keeps pre-speech context for each spoken turn."
        footer={
          <div className="card-actions card-actions--end">
            <Button
              label="Reset audio defaults"
              icon="refresh"
              variant="ghost"
              onClick={() => onRunAction("resetAudioDefaults")}
            />
          </div>
        }
      >
        <TextField
          fieldName="audio_silence_seconds"
          label="Silence timeout"
          icon="history"
          suffix="s"
          inputMode="decimal"
          value={getDraftValue("audio_silence_seconds")}
          errorText={state.errors.audio_silence_seconds}
          helperText="How long silence must last before Glance finishes the current spoken turn, in seconds."
          onChange={(value) => onDraftChange("audio_silence_seconds", value)}
          onCommit={(value) => onDraftCommit("audio_silence_seconds", value)}
          onFocus={() => onDraftFocus("audio_silence_seconds")}
        />

        <TextField
          fieldName="audio_max_wait_seconds"
          label="Wait for speech"
          icon="clock"
          suffix="s"
          inputMode="decimal"
          value={getDraftValue("audio_max_wait_seconds")}
          errorText={state.errors.audio_max_wait_seconds}
          helperText="Maximum time to wait for speech before live mode returns to listening, in seconds."
          onChange={(value) => onDraftChange("audio_max_wait_seconds", value)}
          onCommit={(value) => onDraftCommit("audio_max_wait_seconds", value)}
          onFocus={() => onDraftFocus("audio_max_wait_seconds")}
        />

        <TextField
          fieldName="audio_max_record_seconds"
          label="Max turn length"
          icon="wave"
          suffix="s"
          inputMode="decimal"
          value={getDraftValue("audio_max_record_seconds")}
          errorText={state.errors.audio_max_record_seconds}
          helperText="Hard limit for one captured spoken turn, in seconds."
          onChange={(value) => onDraftChange("audio_max_record_seconds", value)}
          onCommit={(value) => onDraftCommit("audio_max_record_seconds", value)}
          onFocus={() => onDraftFocus("audio_max_record_seconds")}
        />

        <TextField
          fieldName="audio_preroll_seconds"
          label="Pre-roll"
          icon="mic"
          suffix="s"
          inputMode="decimal"
          value={getDraftValue("audio_preroll_seconds")}
          errorText={state.errors.audio_preroll_seconds}
          helperText="Extra audio kept just before speech starts, in seconds."
          onChange={(value) => onDraftChange("audio_preroll_seconds", value)}
          onCommit={(value) => onDraftCommit("audio_preroll_seconds", value)}
          onFocus={() => onDraftFocus("audio_preroll_seconds")}
        />
      </GlassCard>
    </div>
  );
}

function HistorySection({
  state,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onRunAction,
  getDraftValue,
}: Pick<
  SettingsSectionsProps,
  | "state"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onRunAction"
  | "getDraftValue"
>) {
  return (
    <GlassCard
      title="History"
      description="Manage how much session history stays on this device."
      footer={
        <div className="card-actions">
          <div className="section-callout">
            <strong>Delete saved history</strong>
          </div>
          <Button
            label="Delete history"
            icon="trash"
            variant="danger"
            onClick={() => {
              if (!window.confirm("Delete all saved Glance history on this device?")) {
                return;
              }
              onRunAction("clearHistory");
            }}
          />
        </div>
      }
    >
      <TextField
        fieldName="history_length"
        label="History length"
        icon="history"
        inputMode="numeric"
        value={getDraftValue("history_length")}
        errorText={state.errors.history_length}
        helperText="Maximum number of saved sessions."
        onChange={(value) => onDraftChange("history_length", value)}
        onCommit={(value) => onDraftCommit("history_length", value)}
        onFocus={() => onDraftFocus("history_length")}
      />
    </GlassCard>
  );
}

function GeneralSection({
  state,
  openSelect,
  onToggleSelect,
  onSelectValue,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  getDraftValue,
}: Pick<
  SettingsSectionsProps,
  | "state"
  | "openSelect"
  | "onToggleSelect"
  | "onSelectValue"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "getDraftValue"
>) {
  return (
    <GlassCard
      title="General"
      description="Appearance and prompt settings for this device."
    >
      <SelectField
        fieldName="theme_preference"
        label="Theme"
        icon={settingValue(state, "theme_preference") === "light" ? "sun" : "moon"}
        value={settingValue(state, "theme_preference") || "dark"}
        options={state.themeOptions}
        labels={THEME_LABELS}
        helperText="Choose light, dark, or system."
        open={openSelect === "theme_preference"}
        onToggle={() => onToggleSelect("theme_preference")}
        onSelect={(value) => onSelectValue("theme_preference", value)}
      />

      <TextField
        fieldName="system_prompt_override"
        label="System prompt override"
        icon="quote"
        multiline
        value={getDraftValue("system_prompt_override")}
        helperText="Optional custom system prompt."
        placeholder="Keep Glance concise, context-aware, and proactive…"
        onChange={(value) => onDraftChange("system_prompt_override", value)}
        onCommit={(value) => onDraftCommit("system_prompt_override", value)}
        onFocus={() => onDraftFocus("system_prompt_override")}
      />
    </GlassCard>
  );
}
