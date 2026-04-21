import { Icon } from "../icons";
import { Input } from "../ui/input";
import { Panel } from "../ui/panel";
import { SelectInput } from "../ui/select-input";
import { StatusPill, type StatusPillTone } from "../ui/status-pill";
import { ToggleField } from "../ui/toggle-field";

import {
  PROVIDER_CARDS,
  REASONING_ICONS,
  REASONING_LABELS,
  type ProviderTab,
  type SettingsTabProps,
  settingValue,
} from "./shared";

function providerStatus(
  state: SettingsTabProps["state"],
  providerTab: ProviderTab,
): { tone: StatusPillTone; label: string; detail: string } {
  if (providerTab === "llm") {
    const configured =
      Boolean(settingValue(state, "llm_base_url")) &&
      Boolean(settingValue(state, "llm_model_name")) &&
      Boolean(settingValue(state, "llm_api_key"));
    return configured
      ? {
          tone: "accent",
          label: "Configured",
          detail: settingValue(state, "llm_model_name"),
        }
      : {
          tone: "warm",
          label: "Setup",
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
          tone: "accent",
          label: "Configured",
          detail: settingValue(state, "tts_model"),
        }
      : {
          tone: "warm",
          label: "Setup",
          detail: "Add the URL, key, and model.",
        };
  }

  const configured =
    Boolean(settingValue(state, "transcription_base_url")) &&
    Boolean(settingValue(state, "transcription_model_name")) &&
    Boolean(settingValue(state, "transcription_api_key"));
  return configured
    ? {
        tone: "accent",
        label: "Configured",
        detail: settingValue(state, "transcription_model_name"),
      }
    : {
        tone: "warm",
        label: "Setup",
        detail: "Add the URL, key, and model.",
      };
}

export function ProvidersTab({
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
  SettingsTabProps,
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
  const llmReasoning = Boolean(state.settings.llm_reasoning_enabled);
  const transcriptionReasoning = Boolean(
    state.settings.transcription_reasoning_enabled,
  );

  return (
    <div className="stack">
      <Panel
        title="Providers"
        description="Choose where replies, voice, and transcription come from."
      >
        <div className="provider-tabs" role="tablist" aria-label="Provider">
          {PROVIDER_CARDS.map((provider) => {
            const selected = providerTab === provider.id;
            const status = providerStatus(state, provider.id);
            return (
              <button
                key={provider.id}
                type="button"
                role="tab"
                aria-selected={selected}
                className={`provider-tab${selected ? " is-active" : ""}`}
                onClick={() => onChangeProviderTab(provider.id)}
              >
                <span className="provider-tab__icon">
                  <Icon name={provider.icon} />
                </span>
                <span className="provider-tab__copy">
                  <span className="provider-tab__eyebrow">{provider.eyebrow}</span>
                  <span className="provider-tab__title">{provider.label}</span>
                </span>
                <StatusPill tone={status.tone} label={status.label} />
                {status.detail ? (
                  <span className="provider-tab__detail">{status.detail}</span>
                ) : null}
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

            <ToggleField
              label="Reasoning"
              helperText="Let the model think before it answers."
              icon="brain"
              checked={llmReasoning}
              onChange={(nextValue) => onSetField("llm_reasoning_enabled", nextValue)}
            />

            <div
              className={`reasoning-expand${llmReasoning ? "" : " reasoning-expand--closed"}`}
              aria-hidden={!llmReasoning}
            >
              <div className="reasoning-expand__inner">
                <SelectInput
                  fieldName="llm_reasoning"
                  label="Reasoning Level"
                  icon="level-3"
                  value={settingValue(state, "llm_reasoning") || "medium"}
                  options={state.reasoningOptions}
                  labels={REASONING_LABELS}
                  optionIcons={REASONING_ICONS}
                  helperText="Default depth for replies."
                  open={openSelect === "llm_reasoning"}
                  onToggle={() => onToggleSelect("llm_reasoning")}
                  onSelect={(value) => onSelectValue("llm_reasoning", value)}
                />
              </div>
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

            <ToggleField
              label="Reasoning"
              helperText="Let the transcription model think before it returns text."
              icon="brain"
              checked={transcriptionReasoning}
              onChange={(nextValue) =>
                onSetField("transcription_reasoning_enabled", nextValue)
              }
            />

            <div
              className={`reasoning-expand${transcriptionReasoning ? "" : " reasoning-expand--closed"}`}
              aria-hidden={!transcriptionReasoning}
            >
              <div className="reasoning-expand__inner">
                <SelectInput
                  fieldName="transcription_reasoning"
                  label="Reasoning Level"
                  icon="level-3"
                  value={settingValue(state, "transcription_reasoning") || "medium"}
                  options={state.transcriptionReasoningOptions}
                  labels={REASONING_LABELS}
                  optionIcons={REASONING_ICONS}
                  helperText="Default depth for transcription."
                  open={openSelect === "transcription_reasoning"}
                  onToggle={() => onToggleSelect("transcription_reasoning")}
                  onSelect={(value) => onSelectValue("transcription_reasoning", value)}
                />
              </div>
            </div>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}
