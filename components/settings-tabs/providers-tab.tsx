import { Icon } from "../icons";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Input } from "../ui/input";
import { SelectInput } from "../ui/select-input";
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
