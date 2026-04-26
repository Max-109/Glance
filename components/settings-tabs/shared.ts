import type { BridgeState } from "@/lib/glance-bridge";

export type ProviderTab = "llm" | "speech" | "transcription";

export interface SettingsTabProps {
  state: BridgeState;
  stateReady: boolean;
  providerTab: ProviderTab;
  openSelect: string | null;
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
  onStartKeybindCapture: (fieldName: string) => void;
  getDraftValue: (fieldName: string) => string;
}

export const PROVIDER_CARDS: Array<{
  id: ProviderTab;
  label: string;
  eyebrow: string;
  icon: string;
}> = [
  {
    id: "transcription",
    label: "Transcription",
    eyebrow: "INPUT",
    icon: "mic",
  },
  {
    id: "llm",
    label: "Reply",
    eyebrow: "ANSWER",
    icon: "replies",
  },
  {
    id: "speech",
    label: "Voice",
    eyebrow: "OUTPUT",
    icon: "speaker",
  },
];

export const REASONING_LABELS: Record<string, string> = {
  minimal: "Minimal",
  low: "Low",
  medium: "Medium",
  high: "High",
};

export const REASONING_ICONS: Record<string, string> = {
  minimal: "level-1",
  low: "level-2",
  medium: "level-3",
  high: "level-4",
};

export const DEFAULT_ACCENT_COLOR = "#eaabab";

export const ACCENT_PRESETS = [
  { label: "Blush", value: DEFAULT_ACCENT_COLOR },
  { label: "Signal", value: "#a7ffde" },
  { label: "Clay", value: "#b58f70" },
  { label: "Violet", value: "#b7a6ff" },
];

export function settingValue(state: BridgeState, fieldName: string): string {
  const value = state.settings[fieldName];
  return value === null || value === undefined ? "" : String(value);
}
