"use client";

import { useMemo, useState } from "react";
import type { CSSProperties } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Icon } from "@/components/icons";
import { GlanceButton } from "@/components/settings-shell/button";
import { StatusBadge } from "@/components/settings-shell/status-badge";
import { cn } from "@/lib/utils";

import { ColorPicker } from "../ui/color-picker";
import { Keybinds } from "../ui/keybinds";

import {
  ACCENT_PRESETS,
  DEFAULT_ACCENT_COLOR,
  type SettingsTabProps,
  settingValue,
} from "./shared";

type PromptId =
  | "system_prompt_override"
  | "text_prompt_override"
  | "voice_prompt_override"
  | "voice_polish_prompt_override"
  | "transcription_prompt_override";

type PromptRow = {
  id: PromptId;
  title: string;
  eyebrow: string;
  description: string;
  helper: string;
  icon: string;
  accent: string;
  defaultValue: string;
};

type PromptStyle = CSSProperties & {
  "--prompt-accent": string;
};

function promptStyle(row: PromptRow): PromptStyle {
  return { "--prompt-accent": row.accent };
}

function wordCount(value: string) {
  return value.trim().split(/\s+/).filter(Boolean).length;
}

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
  const [activePromptId, setActivePromptId] =
    useState<PromptId>("text_prompt_override");

  const promptRows = useMemo<PromptRow[]>(
    () => [
      {
        id: "system_prompt_override",
        title: "Shared note",
        eyebrow: "Shared",
        description: "Added after text and voice prompts.",
        helper: "Leave this empty unless every reply needs the same extra rule.",
        icon: "settings",
        accent: "var(--accent)",
        defaultValue: "",
      },
      {
        id: "text_prompt_override",
        title: "Text replies",
        eyebrow: "Text",
        description: "Regular replies and screen questions.",
        helper: "Used when Glance answers in text.",
        icon: "replies",
        accent: "#38bdf8",
        defaultValue: state.promptDefaults.text_prompt_override ?? "",
      },
      {
        id: "voice_prompt_override",
        title: "Voice reply",
        eyebrow: "Voice",
        description: "The spoken answer before enhancement.",
        helper: "Used before Glance adds Eleven delivery details.",
        icon: "speaker",
        accent: "#f97316",
        defaultValue: state.promptDefaults.voice_prompt_override ?? "",
      },
      {
        id: "voice_polish_prompt_override",
        title: "Speech enhancement",
        eyebrow: "Enhance",
        description: "Adds delivery, emotion, and Eleven tags.",
        helper: "Used to add speech emotion and delivery details, not to answer again.",
        icon: "wave",
        accent: "#a78bfa",
        defaultValue: state.promptDefaults.voice_polish_prompt_override ?? "",
      },
      {
        id: "transcription_prompt_override",
        title: "Transcription",
        eyebrow: "Input",
        description: "Turns raw audio into text.",
        helper: "Used before Glance answers.",
        icon: "mic",
        accent: "#22c55e",
        defaultValue: state.promptDefaults.transcription_prompt_override ?? "",
      },
    ],
    [state.promptDefaults],
  );

  const activePrompt = promptRows.find((row) => row.id === activePromptId) ?? promptRows[1];
  const activeValue = getDraftValue(activePrompt.id);
  const activeIsCustom = activeValue !== activePrompt.defaultValue;
  const activeWords = wordCount(activeValue);
  const customPromptCount = promptRows.reduce(
    (count, row) => count + (getDraftValue(row.id) !== row.defaultValue ? 1 : 0),
    0,
  );

  const resetField = (fieldName: PromptId, value: string) => {
    onDraftChange(fieldName, value);
    onDraftCommit(fieldName, value);
  };

  const shortcutRows = [
    {
      id: "live_keybind",
      title: "Live",
      icon: "zap",
      value: String(state.settings.live_keybind || "-"),
      active: state.bindingField === "live_keybind",
    },
    {
      id: "ocr_keybind",
      title: "OCR",
      icon: "capture",
      value: String(state.settings.ocr_keybind || "-"),
      active: state.bindingField === "ocr_keybind",
    },
  ];

  return (
    <div className="grid gap-4">
      <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-start justify-between gap-4">
            <div>
              <CardTitle className="text-base font-semibold">Accent</CardTitle>
              <CardDescription>
                Pick the color used for highlights, icons, and mic controls.
              </CardDescription>
            </div>
            <span className="hidden rounded-full border border-[color-mix(in_srgb,var(--accent)_34%,transparent)] bg-[color-mix(in_srgb,var(--accent)_10%,transparent)] px-3 py-1 font-mono text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--accent-strong)] sm:inline-flex">
              {settingValue(state, "accent_color") || DEFAULT_ACCENT_COLOR}
            </span>
          </div>
        </CardHeader>
        <CardContent className="px-5 py-5">
          <ColorPicker
            value={settingValue(state, "accent_color") || DEFAULT_ACCENT_COLOR}
            presets={ACCENT_PRESETS}
            onChange={(nextValue) => onSetField("accent_color", nextValue)}
          />
        </CardContent>
      </Card>

      <Card className="shell-surface gap-0 overflow-hidden rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base font-semibold">Prompts</CardTitle>
              <CardDescription>
                Edit one prompt at a time without losing the full text.
              </CardDescription>
            </div>
            <StatusBadge
              tone={!stateReady ? "neutral" : customPromptCount ? "accent" : "neutral"}
            >
              {!stateReady
                ? "loading"
                : customPromptCount
                  ? `${customPromptCount} custom`
                  : "defaults"}
            </StatusBadge>
          </div>
        </CardHeader>

        <CardContent className="px-5 py-5">
          {!stateReady ? (
            <div className="rounded-2xl border border-dashed border-border bg-card p-4 text-sm text-muted-foreground">
              Loading saved prompts.
            </div>
          ) : (
            <div className="grid gap-4 xl:grid-cols-[18rem_minmax(0,1fr)_16rem]">
              <aside className="grid content-start gap-2" aria-label="Prompt list">
                {promptRows.map((row) => {
                  const value = getDraftValue(row.id);
                  const isActive = row.id === activePrompt.id;
                  const isCustom = value !== row.defaultValue;
                  return (
                    <button
                      key={row.id}
                      type="button"
                      className={cn(
                        "group grid gap-3 rounded-2xl border p-3 text-left transition-[background-color,border-color,box-shadow,transform] active:scale-[0.99] focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--prompt-accent)_14%,transparent)]",
                        isActive
                          ? "border-[color-mix(in_srgb,var(--prompt-accent)_44%,transparent)] bg-[radial-gradient(circle_at_14%_20%,color-mix(in_srgb,var(--prompt-accent)_14%,transparent),transparent_34%),var(--card)] shadow-[0_0_0_1px_color-mix(in_srgb,var(--prompt-accent)_10%,transparent)]"
                          : "border-white/10 bg-card hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--prompt-accent)_28%,transparent)] hover:bg-white/[0.025]",
                      )}
                      style={promptStyle(row)}
                      aria-pressed={isActive}
                      onClick={() => setActivePromptId(row.id)}
                    >
                      <span className="flex items-start justify-between gap-3">
                        <span
                          className={cn(
                            "grid size-10 shrink-0 place-items-center rounded-2xl border text-[var(--prompt-accent)]",
                            isActive
                              ? "border-[color-mix(in_srgb,var(--prompt-accent)_38%,transparent)] bg-[color-mix(in_srgb,var(--prompt-accent)_14%,transparent)]"
                              : "border-white/10 bg-white/[0.035]",
                          )}
                        >
                          <Icon name={row.icon} className="size-5" />
                        </span>
                        <span
                          className={cn(
                            "rounded-full border px-2 py-0.5 font-mono text-[0.58rem] font-bold uppercase tracking-[0.14em]",
                            isCustom
                              ? "border-[color-mix(in_srgb,var(--prompt-accent)_34%,transparent)] text-[var(--prompt-accent)]"
                              : "border-white/10 text-[var(--text-muted)]",
                          )}
                        >
                          {isCustom ? "custom" : "default"}
                        </span>
                      </span>
                      <span>
                        <span className="block text-sm font-semibold text-[var(--text-strong)]">
                          {row.title}
                        </span>
                        <span className="mt-1 line-clamp-2 block text-xs leading-5 text-[var(--text-muted)]">
                          {row.description}
                        </span>
                      </span>
                      <span className="flex items-center justify-between gap-3 font-mono text-[0.64rem] font-bold uppercase tracking-[0.12em] text-[var(--text-muted)]">
                        <span>{row.eyebrow}</span>
                        <span>{isActive ? "open" : "edit"}</span>
                      </span>
                    </button>
                  );
                })}
              </aside>

              <section
                className="min-w-0 overflow-hidden rounded-3xl border border-[color-mix(in_srgb,var(--prompt-accent)_42%,transparent)] bg-[radial-gradient(circle_at_12%_0%,color-mix(in_srgb,var(--prompt-accent)_13%,transparent),transparent_28%),var(--card)]"
                style={promptStyle(activePrompt)}
                aria-labelledby="active-prompt-title"
              >
                <div className="flex min-w-0 items-start justify-between gap-3 border-b border-border px-4 py-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="grid size-9 shrink-0 place-items-center rounded-2xl border border-[color-mix(in_srgb,var(--prompt-accent)_36%,transparent)] bg-[color-mix(in_srgb,var(--prompt-accent)_12%,transparent)] text-[var(--prompt-accent)]">
                        <Icon name={activePrompt.icon} className="size-4.5" />
                      </span>
                      <h3
                        id="active-prompt-title"
                        className="text-lg font-semibold leading-tight text-[var(--text-strong)]"
                      >
                        {activePrompt.title}
                      </h3>
                      <span className="rounded-full border border-[color-mix(in_srgb,var(--prompt-accent)_34%,transparent)] bg-[color-mix(in_srgb,var(--prompt-accent)_8%,transparent)] px-2.5 py-1 font-mono text-[0.62rem] font-bold uppercase tracking-[0.14em] text-[var(--prompt-accent)]">
                        {activePrompt.eyebrow}
                      </span>
                    </div>
                    <p className="mt-2 max-w-[68ch] text-sm leading-5 text-[var(--text-muted)]">
                      {activePrompt.helper}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <StatusBadge tone={activeIsCustom ? "accent" : "neutral"}>
                      {activeIsCustom ? "custom" : "default"}
                    </StatusBadge>
                    <GlanceButton
                      icon="undo"
                      variant="ghost"
                      disabled={!activeIsCustom}
                      onClick={() => resetField(activePrompt.id, activePrompt.defaultValue)}
                    >
                      Reset
                    </GlanceButton>
                  </div>
                </div>

                <div className="min-h-[43rem]">
                  <Textarea
                    name={activePrompt.id}
                    value={activeValue}
                    className="h-[43rem] min-h-[43rem] resize-y overflow-y-auto overscroll-contain rounded-none border-0 bg-[var(--timing-input-bg,#28282b)] px-6 py-5 font-mono text-[0.82rem] leading-6 text-[var(--text-strong)] shadow-none focus-visible:ring-0"
                    spellCheck={false}
                    onChange={(event) =>
                      onDraftChange(activePrompt.id, event.currentTarget.value)
                    }
                    onBlur={(event) =>
                      onDraftCommit(activePrompt.id, event.currentTarget.value)
                    }
                    onFocus={() => onDraftFocus(activePrompt.id)}
                    onWheelCapture={(event) => event.stopPropagation()}
                  />
                </div>
              </section>

              <aside
                className="grid content-start gap-3 rounded-3xl border border-white/10 bg-card p-4"
                style={promptStyle(activePrompt)}
                aria-label="Prompt details"
              >
                <div className="rounded-2xl border border-[color-mix(in_srgb,var(--prompt-accent)_26%,transparent)] bg-[color-mix(in_srgb,var(--prompt-accent)_7%,transparent)] p-3">
                  <span className="block font-mono text-[0.58rem] font-bold uppercase tracking-[0.14em] text-[var(--prompt-accent)]">
                    Purpose
                  </span>
                  <p className="mt-2 text-sm leading-5 text-[var(--text-strong)]">
                    {activePrompt.description}
                  </p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-3">
                  <span className="block font-mono text-[0.58rem] font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                    Total prompt text
                  </span>
                  <span className="mt-3 block text-3xl font-semibold tabular-nums text-[var(--text-strong)]">
                    {activeWords}
                  </span>
                </div>
              </aside>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="text-base font-semibold">Keyboard shortcuts</CardTitle>
          <CardDescription>Pick how you trigger each mode.</CardDescription>
        </CardHeader>
        <CardContent className="px-5 py-5">
          <Keybinds rows={shortcutRows} onActivate={onStartKeybindCapture} />
        </CardContent>
      </Card>
    </div>
  );
}
