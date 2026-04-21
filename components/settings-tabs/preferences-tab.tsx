import { ColorPicker } from "../ui/color-picker";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Keybinds } from "../ui/keybinds";
import { Panel } from "../ui/panel";
import { StatusPill } from "../ui/status-pill";

import { ACCENT_PRESETS, type SettingsTabProps, settingValue } from "./shared";

export function PreferencesTab({
  state,
  stateReady,
  onSetField,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onStartKeybindCapture,
  getDraftValue,
}: Pick<
  SettingsTabProps,
  | "state"
  | "stateReady"
  | "onSetField"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onStartKeybindCapture"
  | "getDraftValue"
>) {
  const promptRows = [
    {
      id: "text_prompt_override",
      title: "Text replies",
      description: "Used for regular replies and screen questions.",
    },
    {
      id: "voice_prompt_override",
      title: "Voice reply",
      description: "Used for the main spoken answer before any speech polishing.",
    },
    {
      id: "voice_polish_prompt_override",
      title: "Speech polish",
      description: "Used when Glance reshapes a reply to sound better in Eleven.",
    },
    {
      id: "transcription_prompt_override",
      title: "Transcription",
      description: "Used when Glance turns raw audio into text.",
    },
  ] as const;

  const resetField = (fieldName: string, value: string) => {
    onDraftChange(fieldName, value);
    onDraftCommit(fieldName, value);
  };

  const customPromptCount = promptRows.reduce(
    (count, row) =>
      count + (getDraftValue(row.id) !== (state.promptDefaults[row.id] ?? "") ? 1 : 0),
    0,
  );
  const sharedPromptActive = getDraftValue("system_prompt_override").trim().length > 0;
  const shortcutRows = [
    {
      id: "live_keybind",
      title: "Live",
      icon: "zap",
      value: String(state.settings.live_keybind || "-"),
      active: state.bindingField === "live_keybind",
    },
    {
      id: "quick_keybind",
      title: "Quick Ask",
      icon: "bot",
      value: String(state.settings.quick_keybind || "-"),
      active: state.bindingField === "quick_keybind",
    },
    {
      id: "ocr_keybind",
      title: "Read Screen",
      icon: "capture",
      value: String(state.settings.ocr_keybind || "-"),
      active: state.bindingField === "ocr_keybind",
    },
  ];

  return (
    <div className="stack">
      <Panel
        title="Accent"
        description="Pick the color used for highlights, icons, and the mic threshold."
      >
        <ColorPicker
          value={settingValue(state, "accent_color") || "#a7ffde"}
          presets={ACCENT_PRESETS}
          onChange={(nextValue) => onSetField("accent_color", nextValue)}
        />
      </Panel>

      <Panel
        title="Prompts"
        description="Edit the exact prompts Glance saves and uses in each mode."
        summary={
          <StatusPill
            tone={!stateReady ? "neutral" : customPromptCount ? "accent" : "neutral"}
            label={
              !stateReady
                ? "loading"
                : customPromptCount
                  ? `${customPromptCount} custom`
                  : "using defaults"
            }
          />
        }
        footer={
          <span className="inline-note">
            Reset brings back the built-in prompt for that mode.
          </span>
        }
      >
        {!stateReady ? (
          <div className="preferences-prompts__loading">Loading saved prompts.</div>
        ) : (
          <div className="preferences-prompts">
            <section className="preferences-prompt-card preferences-prompt-card--shared">
              <div className="preferences-prompt-card__header">
                <div className="preferences-prompt-card__copy">
                  <h3 className="preferences-prompt-card__title">Shared note</h3>
                  <p className="preferences-prompt-card__description">
                    Appended to text and voice replies after the main prompt.
                  </p>
                </div>
                <div className="preferences-prompt-card__actions">
                  <StatusPill
                    tone={sharedPromptActive ? "accent" : "neutral"}
                    label={sharedPromptActive ? "active" : "empty"}
                  />
                  <Button
                    label="Reset"
                    icon="undo"
                    variant="ghost"
                    disabled={!sharedPromptActive}
                    onClick={() => resetField("system_prompt_override", "")}
                  />
                </div>
              </div>
              <Input
                fieldName="system_prompt_override"
                multiline
                value={getDraftValue("system_prompt_override")}
                helperText="Leave it empty if you do not need extra global rules."
                onChange={(value) => onDraftChange("system_prompt_override", value)}
                onCommit={(value) => onDraftCommit("system_prompt_override", value)}
                onFocus={() => onDraftFocus("system_prompt_override")}
              />
            </section>

            {promptRows.map((row) => {
              const value = getDraftValue(row.id);
              const defaultValue = state.promptDefaults[row.id] ?? "";
              const isCustom = value !== defaultValue;

              return (
                <section className="preferences-prompt-card" key={row.id}>
                  <div className="preferences-prompt-card__header">
                    <div className="preferences-prompt-card__copy">
                      <h3 className="preferences-prompt-card__title">{row.title}</h3>
                      <p className="preferences-prompt-card__description">{row.description}</p>
                    </div>
                    <div className="preferences-prompt-card__actions">
                      <StatusPill
                        tone={isCustom ? "accent" : "neutral"}
                        label={isCustom ? "custom" : "default"}
                      />
                      <Button
                        label="Reset"
                        icon="undo"
                        variant="ghost"
                        disabled={!isCustom}
                        onClick={() => resetField(row.id, defaultValue)}
                      />
                    </div>
                  </div>
                  <Input
                    fieldName={row.id}
                    multiline
                    value={value}
                    onChange={(nextValue) => onDraftChange(row.id, nextValue)}
                    onCommit={(nextValue) => onDraftCommit(row.id, nextValue)}
                    onFocus={() => onDraftFocus(row.id)}
                  />
                </section>
              );
            })}
          </div>
        )}
      </Panel>

      <Panel
        title="Keyboard shortcuts"
        description="Pick how you trigger each mode."
      >
        <Keybinds rows={shortcutRows} onActivate={onStartKeybindCapture} />
      </Panel>
    </div>
  );
}
