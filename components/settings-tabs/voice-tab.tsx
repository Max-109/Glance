import type { CSSProperties } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Icon } from "@/components/icons";
import { cn } from "@/lib/utils";

import {
  type SettingsTabProps,
  settingValue,
} from "./shared";

const VOICE_TONES: Record<string, string> = {
  auto: "Auto",
  Ellen: "Direct",
  James: "Bold",
  Juniper: "Steady",
  Mark: "Natural",
  Arabella: "Emotive",
  Jane: "Narrator",
  Hope: "Bright",
  Bradford: "Expressive",
};

type VoicePersonality = {
  icon: string;
  label: string;
  chips: string[];
  accent: string;
  pattern: "adaptive" | "sharp" | "bold" | "calm" | "easy" | "dramatic" | "reader" | "bright" | "story";
};

const VOICE_PERSONALITIES: Record<string, VoicePersonality> = {
  auto: {
    icon: "brain",
    label: "Emotion match",
    chips: ["adaptive", "context-aware", "balanced"],
    accent: "var(--accent)",
    pattern: "adaptive",
  },
  Ellen: {
    icon: "anchor",
    label: "Direct",
    chips: ["clear", "calm", "firm"],
    accent: "#f0b100",
    pattern: "sharp",
  },
  James: {
    icon: "flame",
    label: "Bold",
    chips: ["low", "engaging", "punchy"],
    accent: "#f97316",
    pattern: "bold",
  },
  Juniper: {
    icon: "heart",
    label: "Steady",
    chips: ["warm", "grounded", "measured"],
    accent: "#22c55e",
    pattern: "calm",
  },
  Mark: {
    icon: "smile",
    label: "Natural",
    chips: ["casual", "easy", "human"],
    accent: "#38bdf8",
    pattern: "easy",
  },
  Arabella: {
    icon: "theater",
    label: "Emotive",
    chips: ["dramatic", "soft", "expressive"],
    accent: "#a78bfa",
    pattern: "dramatic",
  },
  Jane: {
    icon: "book",
    label: "Narrator",
    chips: ["polished", "composed", "even"],
    accent: "#ec4899",
    pattern: "reader",
  },
  Hope: {
    icon: "zap",
    label: "Bright",
    chips: ["upbeat", "clear", "reassuring"],
    accent: "#14b8a6",
    pattern: "bright",
  },
  Bradford: {
    icon: "quote",
    label: "Story",
    chips: ["articulate", "British", "animated"],
    accent: "#f43f5e",
    pattern: "story",
  },
};

function splitVoiceLabel(label: string): { name: string; detail: string } {
  const [name, detail] = label.split(" - ");
  return {
    name: name || label,
    detail: detail || "Glance chooses a voice for each reply based on emotions.",
  };
}

function getVoicePersonality(name: string): VoicePersonality {
  return VOICE_PERSONALITIES[name] || {
    icon: "speaker",
    label: VOICE_TONES[name] || "Voice",
    chips: ["recorded", "fixed", "ready"],
    accent: "var(--accent)",
    pattern: "easy",
  };
}

type VoiceCardStyle = CSSProperties & {
  "--voice-accent": string;
};

function voiceCardStyle(personality: VoicePersonality): VoiceCardStyle {
  return { "--voice-accent": personality.accent };
}

function voiceBars(seed: string, count = 18, pattern: VoicePersonality["pattern"] = "easy") {
  const source = seed || "voice";
  return Array.from({ length: count }, (_, index) => {
    const code = source.charCodeAt(index % source.length);
    const base = 18 + ((code + index * 13) % 46);
    if (pattern === "adaptive") {
      return 22 + ((index % 5) * 11 + code) % 58;
    }
    if (pattern === "sharp") {
      return index % 4 === 0 ? 78 : 20 + ((code + index) % 28);
    }
    if (pattern === "bold") {
      return index % 3 === 0 ? 70 : 34 + ((code + index * 7) % 32);
    }
    if (pattern === "calm") {
      return 26 + ((index % 3) * 5) + (code % 18);
    }
    if (pattern === "dramatic") {
      return index % 6 === 2 ? 92 : 18 + ((code + index * 17) % 46);
    }
    if (pattern === "reader") {
      return index % 5 === 0 ? 62 : 30 + ((code + index * 5) % 24);
    }
    if (pattern === "bright") {
      return 34 + ((code + index * 19) % 50);
    }
    if (pattern === "story") {
      return index % 2 === 0 ? 54 + (code % 26) : 22 + ((code + index) % 28);
    }
    return base;
  });
}

function Waveform({
  seed,
  active,
  selected,
  dense = false,
  pattern = "easy",
}: {
  seed: string;
  active: boolean;
  selected: boolean;
  dense?: boolean;
  pattern?: VoicePersonality["pattern"];
}) {
  return (
    <span
      className={cn(
        "flex items-end gap-1.5 rounded-2xl bg-[var(--timing-input-bg,#28282b)] px-4",
        dense ? "h-12 py-3" : "h-16 py-4",
      )}
    >
      {voiceBars(seed, dense ? 14 : 22, pattern).map((height, index) => (
        <span
          key={`${seed}-${index}`}
          className={cn(
            "min-w-1 flex-1 rounded-full transition-[height,background-color]",
            selected
              ? "bg-[var(--voice-accent,var(--accent))]"
              : "bg-[color-mix(in_srgb,var(--voice-accent,var(--text-muted))_42%,transparent)]",
          )}
          style={{ height: `${active ? Math.min(100, height + 20) : height}%` }}
        />
      ))}
    </span>
  );
}

export function VoiceTab({
  state,
  onSetField,
  onRunAction,
}: Pick<SettingsTabProps, "state" | "onSetField" | "onRunAction">) {
  const selectedVoice = settingValue(state, "tts_voice_id") || state.voiceOptions[0] || "auto";
  const selectedLabel = state.voiceOptionLabels[selectedVoice] || selectedVoice;
  const selectedVoiceMeta = splitVoiceLabel(selectedLabel);
  const selectedPersonality = getVoicePersonality(
    selectedVoice === "auto" ? "auto" : selectedVoiceMeta.name,
  );
  const selectedPreviewActive =
    state.previewActive && state.previewingVoice === selectedVoice;
  const selectedPreviewDisabled = selectedVoice === "auto";
  const otherVoices = state.voiceOptions.filter((voiceId) => voiceId !== selectedVoice);

  return (
    <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
      <CardHeader className="border-b border-border px-5 py-4">
        <div className="flex min-w-0 items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base font-semibold">Voice</CardTitle>
            <CardDescription>Pick the voice Glance uses for spoken replies.</CardDescription>
          </div>
          <span className="rounded-full border border-[color-mix(in_srgb,var(--accent)_34%,transparent)] bg-[color-mix(in_srgb,var(--accent)_10%,transparent)] px-3 py-1 font-mono text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
            Recorded samples
          </span>
        </div>
      </CardHeader>

      <CardContent className="grid gap-7 px-5 py-5">
        <section className="grid gap-4" aria-labelledby="voice-picker-title">
          <div>
            <h2 id="voice-picker-title" className="text-sm font-semibold text-[var(--text-strong)]">
              Voice deck
            </h2>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              Pick a voice and play its recorded sample.
            </p>
          </div>

          <article
            className="grid gap-5 rounded-3xl border border-[color-mix(in_srgb,var(--voice-accent)_48%,transparent)] bg-[radial-gradient(circle_at_18%_20%,color-mix(in_srgb,var(--voice-accent)_15%,transparent),transparent_34%),color-mix(in_srgb,var(--voice-accent)_4%,var(--card))] p-6 shadow-[0_0_0_1px_color-mix(in_srgb,var(--voice-accent)_10%,transparent)] lg:grid-cols-[minmax(0,1fr)_12rem]"
            style={voiceCardStyle(selectedPersonality)}
          >
            <div className="min-w-0">
              <div className="flex min-w-0 items-start gap-4">
                <span className="grid size-16 shrink-0 place-items-center rounded-3xl border border-[color-mix(in_srgb,var(--voice-accent)_46%,transparent)] bg-[color-mix(in_srgb,var(--voice-accent)_16%,transparent)] text-[var(--voice-accent)]">
                  <Icon
                    name={selectedPreviewActive ? "wave" : selectedPersonality.icon}
                    className="size-7"
                  />
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-2xl font-semibold leading-tight text-[var(--text-strong)]">
                      {selectedVoiceMeta.name}
                    </h3>
                    <span className="rounded-full border border-[color-mix(in_srgb,var(--voice-accent)_42%,transparent)] bg-[color-mix(in_srgb,var(--voice-accent)_9%,transparent)] px-2.5 py-1 font-mono text-[0.66rem] font-bold uppercase tracking-[0.14em] text-[var(--voice-accent)]">
                      {selectedPersonality.label}
                    </span>
                  </div>
                  <p className="mt-2 max-w-[60ch] text-sm leading-6 text-[var(--text-muted)]">
                    {selectedVoice === "auto"
                      ? "Glance chooses a voice for each reply based on emotions."
                      : selectedVoiceMeta.detail}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selectedPersonality.chips.map((chip) => (
                      <span
                        key={chip}
                        className="rounded-full border border-[color-mix(in_srgb,var(--voice-accent)_28%,transparent)] bg-[color-mix(in_srgb,var(--voice-accent)_9%,transparent)] px-2.5 py-1 text-xs font-medium text-[var(--text-strong)]"
                      >
                        {chip}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-6">
                <Waveform
                  seed={`${selectedVoice}-${selectedLabel}`}
                  active={selectedPreviewActive}
                  selected
                  pattern={selectedPersonality.pattern}
                />
              </div>
            </div>

            <div className="flex items-end justify-between gap-3 lg:flex-col lg:items-stretch">
              <span
                className={cn(
                  "inline-flex h-9 items-center justify-center rounded-full border px-3 font-mono text-[0.66rem] font-bold uppercase tracking-[0.14em]",
                  selectedPreviewDisabled
                    ? "border-white/10 text-[var(--text-muted)]"
                    : "border-[color-mix(in_srgb,var(--voice-accent)_34%,transparent)] text-[var(--voice-accent)]",
                )}
              >
                {selectedPreviewDisabled ? "Auto" : "Ready"}
              </span>
              {selectedPreviewDisabled ? (
                <span className="inline-flex h-12 items-center justify-center rounded-2xl border border-white/10 bg-[var(--timing-input-bg,#28282b)] px-4 text-sm font-semibold text-[var(--text-muted)]">
                  Picks during reply
                </span>
              ) : (
                <button
                  type="button"
                  className={cn(
                    "inline-flex h-12 items-center justify-center gap-3 rounded-2xl border px-4 text-sm font-semibold transition-[background-color,border-color,color,opacity,transform] active:scale-95 focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--voice-accent)_16%,transparent)]",
                    selectedPreviewActive
                      ? "border-[color-mix(in_srgb,var(--voice-accent)_50%,transparent)] bg-[color-mix(in_srgb,var(--voice-accent)_18%,transparent)] text-[var(--voice-accent)]"
                      : "border-white/10 bg-[var(--timing-input-bg,#28282b)] text-[var(--text-strong)] hover:border-[color-mix(in_srgb,var(--voice-accent)_36%,transparent)] hover:text-[var(--voice-accent)]",
                  )}
                  aria-label={`${selectedPreviewActive ? "Stop" : "Play"} ${selectedVoiceMeta.name} preview`}
                  onClick={() => onRunAction("previewVoice", { voiceName: selectedVoice })}
                >
                  <Icon name={selectedPreviewActive ? "stop" : "play"} className="size-4" />
                  {selectedPreviewActive ? "Stop" : "Play sample"}
                </button>
              )}
            </div>
          </article>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {otherVoices.map((voiceId) => {
              const label = state.voiceOptionLabels[voiceId] || voiceId;
              const { name, detail } = splitVoiceLabel(label);
              const personality = getVoicePersonality(voiceId === "auto" ? "auto" : name);
              const previewActive = state.previewActive && state.previewingVoice === voiceId;
              const previewDisabled = voiceId === "auto";

              return (
                <article
                  key={voiceId}
                  className="group grid min-h-44 gap-4 rounded-2xl border border-white/10 bg-[radial-gradient(circle_at_15%_18%,color-mix(in_srgb,var(--voice-accent)_10%,transparent),transparent_34%),var(--card)] p-4 transition-[background-color,border-color,box-shadow,transform] hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--voice-accent)_34%,transparent)] hover:bg-[radial-gradient(circle_at_15%_18%,color-mix(in_srgb,var(--voice-accent)_15%,transparent),transparent_36%),var(--card)]"
                  style={voiceCardStyle(personality)}
                >
                  <button
                    type="button"
                    className="grid gap-3 text-left focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--voice-accent)_14%,transparent)]"
                    onClick={() => onSetField("tts_voice_id", voiceId)}
                  >
                    <span className="flex min-w-0 items-start justify-between gap-3">
                      <span className="grid size-11 shrink-0 place-items-center rounded-2xl border border-[color-mix(in_srgb,var(--voice-accent)_28%,transparent)] bg-[color-mix(in_srgb,var(--voice-accent)_12%,transparent)] text-[var(--voice-accent)]">
                        <Icon name={previewActive ? "wave" : personality.icon} className="size-5" />
                      </span>
                      <span className="rounded-full border border-[color-mix(in_srgb,var(--voice-accent)_24%,transparent)] bg-[color-mix(in_srgb,var(--voice-accent)_7%,transparent)] px-2 py-0.5 font-mono text-[0.6rem] font-bold uppercase tracking-[0.14em] text-[var(--voice-accent)]">
                        {personality.label}
                      </span>
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-base font-semibold text-[var(--text-strong)]">
                        {name}
                      </span>
                      <span className="mt-1 line-clamp-2 block text-sm leading-5 text-[var(--text-muted)]">
                        {detail}
                      </span>
                    </span>
                    <span className="flex flex-wrap gap-1.5">
                      {personality.chips.slice(0, 3).map((chip) => (
                        <span
                          key={chip}
                          className="rounded-full border border-white/10 bg-white/[0.025] px-2 py-0.5 text-[0.68rem] font-medium text-[var(--text-muted)] transition-colors group-hover:border-[color-mix(in_srgb,var(--voice-accent)_22%,transparent)] group-hover:text-[var(--text-strong)]"
                        >
                          {chip}
                        </span>
                      ))}
                    </span>
                    <Waveform
                      seed={`${voiceId}-${label}`}
                      active={previewActive}
                      selected={false}
                      dense
                      pattern={personality.pattern}
                    />
                  </button>

                  {previewDisabled ? (
                    <span className="inline-flex h-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.025] text-sm font-semibold text-[var(--text-muted)]">
                      Auto picks live
                    </span>
                  ) : (
                    <button
                      type="button"
                      className={cn(
                        "inline-flex h-10 items-center justify-center gap-2 rounded-2xl border text-sm font-semibold transition-[background-color,border-color,color,opacity,transform] active:scale-95 focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--voice-accent)_14%,transparent)]",
                        previewActive
                          ? "border-[color-mix(in_srgb,var(--voice-accent)_50%,transparent)] bg-[color-mix(in_srgb,var(--voice-accent)_16%,transparent)] text-[var(--voice-accent)]"
                          : "border-white/10 bg-white/[0.025] text-[var(--text-muted)] hover:border-[color-mix(in_srgb,var(--voice-accent)_30%,transparent)] hover:text-[var(--voice-accent)]",
                      )}
                      aria-label={`${previewActive ? "Stop" : "Play"} ${name} preview`}
                      onClick={() => onRunAction("previewVoice", { voiceName: voiceId })}
                    >
                      <Icon name={previewActive ? "stop" : "play"} className="size-4" />
                      {previewActive ? "Stop" : "Sample"}
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      </CardContent>
    </Card>
  );
}
