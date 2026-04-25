export type SectionId =
  | "tools"
  | "audio"
  | "api"
  | "voice"
  | "advanced"
  | "history";

export interface HistoryPreviewItem {
  id: string;
  mode: string;
  createdAt: string;
  title: string;
  excerpt: string;
  interactionCount: number;
}

export interface HistoryStats {
  totalSessions: number;
  oldestAt: string;
  newestAt: string;
}

export interface RuntimeStatusPayload {
  runtimeState: string;
  runtimeMessage: string;
  runtimeRevision: number;
  runtimePhaseStartedAtMs: number;
  runtimeBlinkIntervalMs: number;
  runtimeErrorFlashUntilMs: number;
}

export interface BridgeState {
  settings: Record<string, string | number | boolean | null>;
  errors: Record<string, string>;
  dirty: boolean;
  manualSaveDirty: boolean;
  saving: boolean;
  stateRevision: number;
  statusMessage: string;
  statusKind: string;
  runtimeState: string;
  runtimeMessage: string;
  runtimeRevision: number;
  runtimePhaseStartedAtMs: number;
  runtimeBlinkIntervalMs: number;
  runtimeErrorFlashUntilMs: number;
  audioInputDeviceOptions: string[];
  audioInputDeviceLabels: Record<string, string>;
  audioOutputDeviceOptions: string[];
  audioOutputDeviceLabels: Record<string, string>;
  audioDeviceStatusMessage: string;
  audioInputLevel: number;
  audioInputTestActive: boolean;
  speakerTestActive: boolean;
  currentSection: SectionId;
  bindingField: string;
  bindingActive: boolean;
  previewingVoice: string;
  previewActive: boolean;
  themeOptions: string[];
  reasoningOptions: string[];
  transcriptionReasoningOptions: string[];
  ttsModelOptions: string[];
  voiceOptions: string[];
  voiceOptionLabels: Record<string, string>;
  languageOptions: string[];
  promptDefaults: Record<string, string>;
  historyPreview: HistoryPreviewItem[];
  historyStats: HistoryStats;
}

export interface AudioBridgeState {
  audioInputLevel: number;
  audioInputTestActive: boolean;
  audioDeviceStatusMessage: string;
}

export interface GlanceBridge {
  getState: () => Promise<BridgeState>;
  getAudioState: () => Promise<AudioBridgeState>;
  setSection: (section: SectionId) => Promise<BridgeState>;
  setField: (
    fieldName: string,
    value: string | number | boolean,
  ) => Promise<BridgeState>;
  runAction: (
    action: string,
    payload?: Record<string, string | number | boolean>,
  ) => Promise<BridgeState>;
  assignKeybind: (fieldName: string, keybind: string) => Promise<BridgeState>;
  hideWindow: () => Promise<{ ok: boolean }>;
  focusWindow: () => Promise<{ ok: boolean }>;
  getSystemTheme: () => Promise<"dark" | "light">;
  subscribeRuntimeStatus: (callback: (status: RuntimeStatusPayload) => void) => number;
  unsubscribeRuntimeStatus: (subscriptionId: number) => void;
}

declare global {
  interface Window {
    glanceBridge: GlanceBridge;
  }
}

export const SECTION_GROUPS: Array<{
  label?: string;
  items: Array<{ id: SectionId; icon: string; title: string }>;
}> = [
  {
    items: [
      { id: "tools", icon: "tools", title: "Tools" },
      { id: "audio", icon: "audio", title: "Audio" },
    ],
  },
  {
    items: [
      { id: "api", icon: "plug", title: "Providers" },
      { id: "voice", icon: "speaker", title: "Voice" },
      { id: "advanced", icon: "sliders", title: "Preferences" },
    ],
  },
  {
    items: [{ id: "history", icon: "history", title: "History" }],
  },
];

export function sectionMeta(section: SectionId): {
  title: string;
  description: string;
} {
  if (section === "api") {
    return {
      title: "Providers",
      description: "Set up replies, voice, and transcription.",
    };
  }
  if (section === "voice") {
    return {
      title: "Voice",
      description: "Choose a voice, preview it, and set a default language.",
    };
  }
  if (section === "tools") {
    return {
      title: "Tools",
      description: "Choose what Glance can use during Live replies.",
    };
  }
  if (section === "audio") {
    return {
      title: "Audio",
      description: "Tune mic and pauses.",
    };
  }
  if (section === "history") {
    return {
      title: "History",
      description: "Choose how much history to keep.",
    };
  }
  return {
    title: "Preferences",
    description: "Theme, accent color, prompt, and keybinds.",
  };
}
