import { ColorPicker } from "../ui/color-picker";
import { Input } from "../ui/input";
import { Keybinds } from "../ui/keybinds";
import { Panel } from "../ui/panel";

import { ACCENT_PRESETS, type SettingsTabProps, settingValue } from "./shared";

export function PreferencesTab({
  state,
  onSetField,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onStartKeybindCapture,
  getDraftValue,
}: Pick<
  SettingsTabProps,
  | "state"
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
        title="Extra instructions"
        description="Anything here gets appended to every reply."
      >
        <Input
          fieldName="system_prompt_override"
          label=""
          multiline
          value={getDraftValue("system_prompt_override")}
          placeholder="e.g. Keep replies short and useful."
          onChange={(value) => onDraftChange("system_prompt_override", value)}
          onCommit={(value) => onDraftCommit("system_prompt_override", value)}
          onFocus={() => onDraftFocus("system_prompt_override")}
        />
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
