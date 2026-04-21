import { AudioTab } from "./settings-tabs/audio-tab";
import { CaptureTab } from "./settings-tabs/capture-tab";
import { HistoryTab } from "./settings-tabs/history-tab";
import { PreferencesTab } from "./settings-tabs/preferences-tab";
import { ProvidersTab } from "./settings-tabs/providers-tab";
import type { SettingsTabProps } from "./settings-tabs/shared";
import { VoiceTab } from "./settings-tabs/voice-tab";

export function SettingsTab(props: SettingsTabProps) {
  if (props.state.currentSection === "api") {
    return <ProvidersTab {...props} />;
  }

  if (props.state.currentSection === "voice") {
    return <VoiceTab {...props} />;
  }

  if (props.state.currentSection === "capture") {
    return <CaptureTab {...props} />;
  }

  if (props.state.currentSection === "audio") {
    return <AudioTab {...props} />;
  }

  if (props.state.currentSection === "history") {
    return <HistoryTab {...props} />;
  }

  return <PreferencesTab {...props} />;
}
