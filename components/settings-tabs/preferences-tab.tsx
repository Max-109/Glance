import { Card } from "../ui/card";
import { ColorPicker } from "../ui/color-picker";
import { Input } from "../ui/input";
import { Keybinds } from "../ui/keybinds";
import { SelectInput } from "../ui/select-input";

import {
  ACCENT_PRESETS,
  THEME_LABELS,
  type SettingsTabProps,
  settingValue,
} from "./shared";

export function PreferencesTab({
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
  SettingsTabProps,
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
