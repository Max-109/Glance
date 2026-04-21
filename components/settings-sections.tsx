import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import type { BridgeState } from "@/lib/glance-bridge";

import { Icon } from "./icons";
import {
  ColorPicker,
  Button,
  Card,
  Input,
  Keybinds,
  MicThreshold,
  NumberInput,
  SelectInput,
  ToggleField,
} from "./ui";

type ProviderTab = "llm" | "speech" | "transcription";

const PROVIDER_CARDS: Array<{
  id: ProviderTab;
  label: string;
  eyebrow: string;
  icon: string;
}> = [
  {
    id: "llm",
    label: "Replies",
    eyebrow: "TEXT",
    icon: "bot",
  },
  {
    id: "speech",
    label: "Voice",
    eyebrow: "VOICE",
    icon: "speaker",
  },
  {
    id: "transcription",
    label: "Transcription",
    eyebrow: "INPUT",
    icon: "mic",
  },
];

const REASONING_LABELS: Record<string, string> = {
  minimal: "Minimal",
  low: "Low",
  medium: "Medium",
  high: "High",
};

const REASONING_ICONS: Record<string, string> = {
  minimal: "level-1",
  low: "level-2",
  medium: "level-3",
  high: "level-4",
};

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English · EN",
  lt: "Lietuvių · LT",
  fr: "Français · FR",
  de: "Deutsch · DE",
  es: "Español · ES",
};

const THEME_LABELS: Record<string, string> = {
  dark: "Dark",
  light: "Light",
  system: "System",
};

const ACCENT_PRESETS = [
  { label: "Signal", value: "#a7ffde" },
  { label: "Clay", value: "#b58f70" },
  { label: "Violet", value: "#b7a6ff" },
];

function settingValue(state: BridgeState, fieldName: string): string {
  const value = state.settings[fieldName];
  return value === null || value === undefined ? "" : String(value);
}

function providerStatus(
  state: BridgeState,
  providerTab: ProviderTab,
): { label: string; detail: string } {
  if (providerTab === "llm") {
    const configured =
      Boolean(settingValue(state, "llm_base_url")) &&
      Boolean(settingValue(state, "llm_model_name")) &&
      Boolean(settingValue(state, "llm_api_key"));
    return configured
      ? {
          label: "Configured",
          detail: settingValue(state, "llm_model_name"),
        }
      : {
          label: "Needs setup",
          detail: "Add the URL, key, and model.",
        };
  }

  if (providerTab === "speech") {
    const configured =
      Boolean(settingValue(state, "tts_base_url")) &&
      Boolean(settingValue(state, "tts_model")) &&
      Boolean(settingValue(state, "tts_api_key"));
    return configured
      ? {
          label: "Configured",
          detail: settingValue(state, "tts_model"),
        }
      : {
          label: "Needs setup",
          detail: "Add the URL, key, and model.",
        };
  }

  const configured =
    Boolean(settingValue(state, "transcription_base_url")) &&
    Boolean(settingValue(state, "transcription_model_name")) &&
    Boolean(settingValue(state, "transcription_api_key"));
  return configured
    ? {
        label: "Configured",
        detail: settingValue(state, "transcription_model_name"),
      }
    : {
        label: "Needs setup",
        detail: "Add the URL, key, and model.",
      };
}

function formatHistoryDate(value: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function HistoryPreviewCard({
  item,
}: {
  item: BridgeState["historyPreview"][number];
}) {
  const [expanded, setExpanded] = useState(false);
  const [canExpand, setCanExpand] = useState(false);
  const excerptRef = useRef<HTMLParagraphElement | null>(null);

  useEffect(() => {
    const element = excerptRef.current;
    if (!element) {
      return;
    }

    const measureOverflow = () => {
      const nextOverflow = element.scrollHeight > element.clientHeight + 1;
      setCanExpand((current) => (expanded ? current || nextOverflow : nextOverflow));
    };

    measureOverflow();
    window.addEventListener("resize", measureOverflow);
    return () => window.removeEventListener("resize", measureOverflow);
  }, [item.excerpt, expanded]);

  return (
    <article className="session-card">
      <div className="session-card__meta">
        <span>{formatHistoryDate(item.createdAt)}</span>
        <span>{item.mode.toUpperCase()}</span>
        <span>{item.interactionCount} turns</span>
      </div>
      <strong>{item.title}</strong>
      <p
        ref={excerptRef}
        className={`session-card__excerpt${expanded ? " is-expanded" : ""}`}
      >
        {item.excerpt}
      </p>
      {canExpand ? (
        <button
          type="button"
          className="session-card__toggle"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Read less" : "Read more"}
        </button>
      ) : null}
    </article>
  );
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
  onSetField: (
    fieldName: string,
    value: string | number | boolean,
  ) => void;
  onDraftChange: (fieldName: string, value: string) => void;
  onDraftCommit: (fieldName: string, value: string) => void;
  onDraftFocus: (fieldName: string) => void;
  onToggleReveal: (fieldName: string) => void;
  onRunAction: (
    action: string,
    payload?: Record<string, string | number | boolean>,
  ) => void;
  onThresholdPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onThresholdNudge: (delta: number) => void;
  onStartKeybindCapture: (fieldName: string) => void;
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
  onSetField,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onToggleReveal,
  onRunAction,
  onThresholdPointerDown,
  onThresholdNudge,
  onStartKeybindCapture,
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
        onSetField={onSetField}
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
        onThresholdNudge={onThresholdNudge}
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
    <MiscSection
      state={state}
      openSelect={openSelect}
      onToggleSelect={onToggleSelect}
      onSelectValue={onSelectValue}
      onSetField={onSetField}
      onDraftChange={onDraftChange}
      onDraftCommit={onDraftCommit}
      onDraftFocus={onDraftFocus}
      onStartKeybindCapture={onStartKeybindCapture}
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
  onSetField,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onToggleReveal,
  getDraftValue,
}: Pick<
  SettingsSectionsProps,
  | "state"
  | "providerTab"
  | "openSelect"
  | "revealedFields"
  | "onChangeProviderTab"
  | "onToggleSelect"
  | "onSelectValue"
  | "onSetField"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onToggleReveal"
  | "getDraftValue"
>) {
  return (
    <Card
      title="Providers"
      description="Set up replies, voice, and transcription."
      className="glass-card--spacious"
    >
      <div className="provider-grid">
        {PROVIDER_CARDS.map((provider) => {
          const selected = providerTab === provider.id;
          const status = providerStatus(state, provider.id);
          return (
            <button
              key={provider.id}
              type="button"
              className={`provider-card${selected ? " is-active" : ""}`}
              onClick={() => onChangeProviderTab(provider.id)}
            >
              <div className="provider-card__lead">
                <span className="provider-card__icon">
                  <Icon name={provider.icon} />
                </span>
                <div className="provider-card__copy">
                  <span className="provider-card__eyebrow">{provider.eyebrow}</span>
                  <div className="provider-card__title">{provider.label}</div>
                </div>
              </div>
              <div className="provider-card__status">
                <strong>{status.label}</strong>
              </div>
              <div className="provider-card__detail">{status.detail}</div>
            </button>
          );
        })}
      </div>

      {providerTab === "llm" ? (
        <div className="stack">
          <div className="field-grid field-grid--two-column field-grid--wide-bias">
            <Input
              fieldName="llm_base_url"
              label="Base URL"
              icon="api"
              inputMode="url"
              value={getDraftValue("llm_base_url")}
              errorText={state.errors.llm_base_url}
              onChange={(value) => onDraftChange("llm_base_url", value)}
              onCommit={(value) => onDraftCommit("llm_base_url", value)}
              onFocus={() => onDraftFocus("llm_base_url")}
            />

            <Input
              fieldName="llm_model_name"
              label="Model"
              icon="bot"
              value={getDraftValue("llm_model_name")}
              errorText={state.errors.llm_model_name}
              onChange={(value) => onDraftChange("llm_model_name", value)}
              onCommit={(value) => onDraftCommit("llm_model_name", value)}
              onFocus={() => onDraftFocus("llm_model_name")}
            />
          </div>

          <Input
            fieldName="llm_api_key"
            label="API Key"
            icon="key"
            value={getDraftValue("llm_api_key")}
            secret
            revealed={Boolean(revealedFields.llm_api_key)}
            onChange={(value) => onDraftChange("llm_api_key", value)}
            onCommit={(value) => onDraftCommit("llm_api_key", value)}
            onFocus={() => onDraftFocus("llm_api_key")}
            onToggleReveal={() => onToggleReveal("llm_api_key")}
          />

          <div className="api-reasoning">
            <ToggleField
              label="Reasoning"
              checked={Boolean(state.settings.llm_reasoning_enabled)}
              onChange={(nextValue) => onSetField("llm_reasoning_enabled", nextValue)}
            />

            {Boolean(state.settings.llm_reasoning_enabled) ? (
              <SelectInput
                fieldName="llm_reasoning"
                label="Reasoning Level"
                icon="level-3"
                value={settingValue(state, "llm_reasoning") || "medium"}
                options={state.reasoningOptions}
                labels={REASONING_LABELS}
                optionIcons={REASONING_ICONS}
                helperText="Default level for replies."
                open={openSelect === "llm_reasoning"}
                onToggle={() => onToggleSelect("llm_reasoning")}
                onSelect={(value) => onSelectValue("llm_reasoning", value)}
              />
            ) : null}
          </div>
        </div>
      ) : null}

      {providerTab === "speech" ? (
        <div className="stack">
          <Input
            fieldName="tts_base_url"
            label="Base URL"
            icon="api"
            inputMode="url"
            value={getDraftValue("tts_base_url")}
            errorText={state.errors.tts_base_url}
            onChange={(value) => onDraftChange("tts_base_url", value)}
            onCommit={(value) => onDraftCommit("tts_base_url", value)}
            onFocus={() => onDraftFocus("tts_base_url")}
          />

          <div className="field-grid field-grid--two-column">
            <Input
              fieldName="tts_api_key"
              label="API Key"
              icon="key"
              value={getDraftValue("tts_api_key")}
              secret
              revealed={Boolean(revealedFields.tts_api_key)}
              onChange={(value) => onDraftChange("tts_api_key", value)}
              onCommit={(value) => onDraftCommit("tts_api_key", value)}
              onFocus={() => onDraftFocus("tts_api_key")}
              onToggleReveal={() => onToggleReveal("tts_api_key")}
            />

            <SelectInput
              fieldName="tts_model"
              label="Model"
              icon="speaker"
              value={settingValue(state, "tts_model") || "eleven-v3"}
              options={state.ttsModelOptions}
              open={openSelect === "tts_model"}
              onToggle={() => onToggleSelect("tts_model")}
              onSelect={(value) => onSelectValue("tts_model", value)}
            />
          </div>
        </div>
      ) : null}

      {providerTab === "transcription" ? (
        <div className="stack">
          <div className="field-grid field-grid--two-column field-grid--wide-bias">
            <Input
              fieldName="transcription_base_url"
              label="Base URL"
              icon="api"
              inputMode="url"
              value={getDraftValue("transcription_base_url")}
              errorText={state.errors.transcription_base_url}
              onChange={(value) => onDraftChange("transcription_base_url", value)}
              onCommit={(value) => onDraftCommit("transcription_base_url", value)}
              onFocus={() => onDraftFocus("transcription_base_url")}
            />

            <Input
              fieldName="transcription_model_name"
              label="Model"
              icon="mic"
              value={getDraftValue("transcription_model_name")}
              errorText={state.errors.transcription_model_name}
              onChange={(value) => onDraftChange("transcription_model_name", value)}
              onCommit={(value) => onDraftCommit("transcription_model_name", value)}
              onFocus={() => onDraftFocus("transcription_model_name")}
            />
          </div>

          <Input
            fieldName="transcription_api_key"
            label="API Key"
            icon="key"
            value={getDraftValue("transcription_api_key")}
            secret
            revealed={Boolean(revealedFields.transcription_api_key)}
            onChange={(value) => onDraftChange("transcription_api_key", value)}
            onCommit={(value) => onDraftCommit("transcription_api_key", value)}
            onFocus={() => onDraftFocus("transcription_api_key")}
            onToggleReveal={() => onToggleReveal("transcription_api_key")}
          />

          <div className="api-reasoning">
            <ToggleField
              label="Reasoning"
              checked={Boolean(state.settings.transcription_reasoning_enabled)}
              onChange={(nextValue) =>
                onSetField("transcription_reasoning_enabled", nextValue)
              }
            />

            {Boolean(state.settings.transcription_reasoning_enabled) ? (
              <SelectInput
                fieldName="transcription_reasoning"
                label="Reasoning Level"
                icon="level-3"
                value={settingValue(state, "transcription_reasoning") || "medium"}
                options={state.transcriptionReasoningOptions}
                labels={REASONING_LABELS}
                optionIcons={REASONING_ICONS}
                helperText="Default level for transcription."
                open={openSelect === "transcription_reasoning"}
                onToggle={() => onToggleSelect("transcription_reasoning")}
                onSelect={(value) => onSelectValue("transcription_reasoning", value)}
              />
            ) : null}
          </div>
        </div>
      ) : null}
    </Card>
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
  onThresholdNudge,
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
    <Card
      title="History"
      description="Choose how much history to keep."
      footer={
        <div className="card-actions card-actions--stack">
          <div className="section-callout">
            <strong>Delete history</strong>
          </div>
          <Button
            label="Delete history"
            icon="trash"
            variant="danger"
            onClick={() => {
              if (!window.confirm("Delete all saved history on this device?")) {
                return;
              }
              onRunAction("clearHistory");
            }}
          />
        </div>
      }
    >
      <NumberInput
        fieldName="history_length"
        label="History Limit"
        icon="history"
        inputMode="numeric"
        step={1}
        min={1}
        value={getDraftValue("history_length")}
        errorText={state.errors.history_length}
        onChange={(value) => onDraftChange("history_length", value)}
        onCommit={(value) => onDraftCommit("history_length", value)}
        onFocus={() => onDraftFocus("history_length")}
      />

      {state.historyPreview.length ? (
        <div className="history-preview" aria-label="Recent saved sessions">
          {state.historyPreview.map((item) => (
            <HistoryPreviewCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <div className="history-empty">
          <strong>No saved sessions yet</strong>
          <span>Recent sessions will appear here after you use Glance.</span>
        </div>
      )}
    </Card>
  );
}

function MiscSection({
  state,
  openSelect,
  onToggleSelect,
  onSelectValue,
  onSetField,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onStartKeybindCapture,
  getDraftValue,
}: Pick<
  SettingsSectionsProps,
  | "state"
  | "openSelect"
  | "onToggleSelect"
  | "onSelectValue"
  | "onSetField"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onStartKeybindCapture"
  | "getDraftValue"
>) {
  const shortcutRows = [
    {
      id: "live_keybind",
      title: "Live",
      value: String(state.settings.live_keybind || "-"),
      active: state.bindingField === "live_keybind",
    },
    {
      id: "quick_keybind",
      title: "Quick Ask",
      value: String(state.settings.quick_keybind || "-"),
      active: state.bindingField === "quick_keybind",
    },
    {
      id: "ocr_keybind",
      title: "Read Screen",
      value: String(state.settings.ocr_keybind || "-"),
      active: state.bindingField === "ocr_keybind",
    },
  ];

  return (
    <div className="stack">
      <Card title="Appearance" description="Choose a theme and accent color.">
        <SelectInput
          fieldName="theme_preference"
          label="Theme"
          icon={
            settingValue(state, "theme_preference") === "light"
              ? "sun"
              : settingValue(state, "theme_preference") === "system"
                ? "monitor"
                : "moon"
          }
          value={settingValue(state, "theme_preference") || "dark"}
          options={state.themeOptions}
          labels={THEME_LABELS}
          helperText="Use dark, light, or follow the system."
          open={openSelect === "theme_preference"}
          onToggle={() => onToggleSelect("theme_preference")}
          onSelect={(value) => onSelectValue("theme_preference", value)}
        />

        <div className="field">
          <span className="field__label">Accent Color</span>
          <ColorPicker
            value={settingValue(state, "accent_color") || "#a7ffde"}
            presets={ACCENT_PRESETS}
            onChange={(nextValue) => onSetField("accent_color", nextValue)}
          />
          <span className="field__meta">
            Used for highlights, notices, icons, and the mic threshold.
          </span>
        </div>
      </Card>

      <Card
        title="Prompt & Keybinds"
        description="Prompt override and keybinds."
      >
        <Input
          fieldName="system_prompt_override"
          label="Extra Instructions"
          icon="quote"
          multiline
          value={getDraftValue("system_prompt_override")}
          helperText="Optional instructions added to each reply."
          placeholder="Keep replies short and useful."
          onChange={(value) => onDraftChange("system_prompt_override", value)}
          onCommit={(value) => onDraftCommit("system_prompt_override", value)}
          onFocus={() => onDraftFocus("system_prompt_override")}
        />

        <Keybinds
          rows={shortcutRows}
          onActivate={onStartKeybindCapture}
        />
      </Card>
    </div>
  );
}
