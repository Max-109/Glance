"use client";

import {
  startTransition,
  useEffect,
  useEffectEvent,
  useMemo,
  useRef,
  useState,
} from "react";
import type { CSSProperties } from "react";

import {
  sectionMeta,
  type BridgeState,
  type RuntimeStatusPayload,
  type SectionId,
} from "@/lib/glance-bridge";
import {
  clamp,
  hexToRgb,
  hslToHex,
  normalizeHexColor,
  relativeLuminance,
  rgbToHsl,
  toRgba,
} from "@/lib/color-utils";
import { eventToKeybind } from "@/lib/keybinds";

import { GlanceAppShell } from "./settings-shell/app-shell";
import { SettingsTab } from "./settings-tab";
import { DEFAULT_ACCENT_COLOR, type ProviderTab } from "./settings-tabs/shared";
import { Notice } from "./ui/notice";

type SystemTheme = "dark";

const EMPTY_RUNTIME_STATUS: RuntimeStatusPayload = {
  runtimeState: "idle",
  runtimeMessage: "Live is idle.",
  runtimeRevision: 0,
  runtimePhaseStartedAtMs: 0,
  runtimeBlinkIntervalMs: 0,
  runtimeErrorFlashUntilMs: 0,
};

const EMPTY_STATE: BridgeState = {
  settings: {
    live_keybind: "CMD+L",
    quick_keybind: "CMD+SHIFT+Q",
    ocr_keybind: "CMD+SHIFT+O",
    llm_base_url: "",
    llm_api_key: "",
    llm_model_name: "gemini-3.1-flash-lite-preview",
    llm_reasoning_enabled: true,
    llm_reasoning: "minimal",
    transcription_base_url: "https://api.naga.ac/v1",
    transcription_api_key: "",
    transcription_model_name: "gemini-3.1-flash-lite-preview",
    transcription_reasoning_enabled: true,
    transcription_reasoning: "minimal",
    multimodal_live_enabled: false,
    tts_base_url: "https://api.naga.ac/v1",
    tts_api_key: "",
    tts_model: "eleven-v3",
    tts_voice_id: "auto",
    fallback_language: "en",
    history_retention_enabled: true,
    history_length: 50,
    tools_enabled: false,
    tool_take_screenshot_policy: "allow",
    tool_web_search_policy: "allow",
    tool_web_fetch_policy: "allow",
    screenshot_interval: 1.5,
    screen_change_threshold: 0.08,
    batch_window_duration: 4,
    audio_input_device: "default",
    audio_output_device: "default",
    audio_vad_threshold: 0.5,
    audio_endpoint_patience: "balanced",
    audio_wait_for_speech_enabled: true,
    audio_max_wait_seconds: 15,
    audio_max_turn_length_enabled: true,
    audio_max_record_seconds: 30,
    audio_preroll_enabled: true,
    audio_preroll_seconds: 0.25,
    system_prompt_override: "",
    text_prompt_override: "",
    voice_prompt_override: "",
    voice_polish_prompt_override: "",
    transcription_prompt_override: "",
    theme_preference: "dark",
    accent_color: DEFAULT_ACCENT_COLOR,
  },
  errors: {},
  dirty: false,
  manualSaveDirty: false,
  saving: false,
  stateRevision: 0,
  statusMessage: "",
  statusKind: "neutral",
  ...EMPTY_RUNTIME_STATUS,
  audioInputDeviceOptions: ["default"],
  audioInputDeviceLabels: { default: "System Default Input" },
  audioOutputDeviceOptions: ["default"],
  audioOutputDeviceLabels: { default: "System Default Output" },
  audioDeviceStatusMessage: "Reconnect Glance to load current audio devices.",
  audioInputLevel: 0,
  audioInputTestActive: false,
  speakerTestActive: false,
  currentSection: "api",
  bindingField: "",
  bindingActive: false,
  previewingVoice: "",
  previewActive: false,
  themeOptions: ["dark", "light", "system"],
  reasoningOptions: ["minimal", "low", "medium", "high"],
  transcriptionReasoningOptions: ["minimal", "low", "medium", "high"],
  ttsModelOptions: ["eleven-v3"],
  voiceOptions: [
    "auto",
    "BIvP0GN1cAtSRTxNHnWS",
    "EkK5I93UQWFDigLMpZcX",
    "aMSt68OGf4xUZAnLpTU8",
    "UgBBYS2sOqTuMpoF3BR0",
    "Z3R5wn05IrDiVCyEkUrK",
    "RILOU7YmBhvwJGDGjNmP",
    "tnSpp4vdxKPjI9w0GnoV",
    "NNl6r8mD7vthiJatiJt1",
  ],
  voiceOptionLabels: {
    auto: "Auto",
    BIvP0GN1cAtSRTxNHnWS: "Ellen - Serious, Direct and Confident",
    EkK5I93UQWFDigLMpZcX: "James - Husky, Engaging and Bold",
    aMSt68OGf4xUZAnLpTU8: "Juniper - Grounded and Professional",
    UgBBYS2sOqTuMpoF3BR0: "Mark - Natural Conversations",
    Z3R5wn05IrDiVCyEkUrK: "Arabella - Mysterious and Emotive",
    RILOU7YmBhvwJGDGjNmP: "Jane - Professional Audiobook Reader",
    tnSpp4vdxKPjI9w0GnoV: "Hope - Upbeat and Clear",
    NNl6r8mD7vthiJatiJt1: "Bradford - Expressive and Articulate",
  },
  languageOptions: ["en", "lt", "fr", "de", "es"],
  promptDefaults: {},
  historyPreview: [],
  historyStats: {
    totalSessions: 0,
    oldestAt: "",
    newestAt: "",
  },
};

function pickRuntimeStatus(snapshot: RuntimeStatusPayload): RuntimeStatusPayload {
  return {
    runtimeState: snapshot.runtimeState,
    runtimeMessage: snapshot.runtimeMessage,
    runtimeRevision: snapshot.runtimeRevision,
    runtimePhaseStartedAtMs: snapshot.runtimePhaseStartedAtMs,
    runtimeBlinkIntervalMs: snapshot.runtimeBlinkIntervalMs,
    runtimeErrorFlashUntilMs: snapshot.runtimeErrorFlashUntilMs,
  };
}

function mergeRuntimeSnapshot(current: BridgeState | null, snapshot: BridgeState): BridgeState {
  if (current === null || current.runtimeRevision <= snapshot.runtimeRevision) {
    return snapshot;
  }
  return { ...snapshot, ...pickRuntimeStatus(current) };
}

function shouldReuseSnapshot(current: BridgeState | null, next: BridgeState): boolean {
  if (current === null) {
    return false;
  }

  return (
    current.stateRevision === next.stateRevision &&
    current.runtimeRevision === next.runtimeRevision &&
    current.runtimeState === next.runtimeState &&
    current.runtimeMessage === next.runtimeMessage &&
    current.runtimePhaseStartedAtMs === next.runtimePhaseStartedAtMs &&
    current.runtimeBlinkIntervalMs === next.runtimeBlinkIntervalMs &&
    current.runtimeErrorFlashUntilMs === next.runtimeErrorFlashUntilMs
  );
}

function getBridge() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.glanceBridge ?? null;
}

function formatError(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Glance isn't connected right now.";
}

function isMacDesktopPlatform() {
  if (typeof navigator === "undefined") {
    return false;
  }

  return /mac/i.test(`${navigator.platform} ${navigator.userAgent}`);
}

function buildThemeStyle(
  accentColor: string,
  resolvedTheme: SystemTheme,
): CSSProperties {
  const accentHex = normalizeHexColor(accentColor, DEFAULT_ACCENT_COLOR);
  const accentRgb = hexToRgb(accentHex);
  const accentHsl = rgbToHsl(accentRgb);
  const accentStrong = hslToHex(
    accentHsl.h,
    clamp(accentHsl.s + 6, 40, 96),
    resolvedTheme === "dark"
      ? clamp(accentHsl.l + 10, 50, 84)
      : clamp(accentHsl.l - 18, 24, 56),
  );
  const signalHex = accentHex;
  const contrast = relativeLuminance(accentRgb) > 0.56 ? "#08120e" : "#f6fbf8";
  const signalContrast =
    relativeLuminance(hexToRgb(signalHex)) > 0.56 ? "#100b07" : "#fff8f2";

  return {
    ["--accent" as const]: accentHex,
    ["--accent-strong" as const]: accentStrong,
    ["--accent-soft" as const]: toRgba(accentHex, resolvedTheme === "dark" ? 0.18 : 0.12),
    ["--accent-border" as const]: toRgba(accentHex, resolvedTheme === "dark" ? 0.36 : 0.26),
    ["--accent-glow" as const]: toRgba(accentHex, resolvedTheme === "dark" ? 0.42 : 0.24),
    ["--accent-contrast" as const]: contrast,
    ["--success" as const]: accentStrong,
    ["--success-soft" as const]: toRgba(accentHex, resolvedTheme === "dark" ? 0.16 : 0.1),
    ["--signal" as const]: signalHex,
    ["--signal-soft" as const]: toRgba(signalHex, resolvedTheme === "dark" ? 0.16 : 0.11),
    ["--signal-border" as const]: toRgba(signalHex, resolvedTheme === "dark" ? 0.34 : 0.22),
    ["--signal-glow" as const]: toRgba(signalHex, resolvedTheme === "dark" ? 0.35 : 0.2),
    ["--signal-contrast" as const]: signalContrast,
  } as CSSProperties;
}

export function SettingsPage() {
  const [state, setState] = useState<BridgeState | null>(null);
  const [isMacOs, setIsMacOs] = useState(false);
  const [providerTab, setProviderTab] = useState<ProviderTab>("transcription");
  const [openSelect, setOpenSelect] = useState<string | null>(null);
  const [skipLinkEnabled, setSkipLinkEnabled] = useState(false);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [revealedFields, setRevealedFields] = useState<Record<string, boolean>>({});
  const [bridgeError, setBridgeError] = useState("");
  const refreshInFlightRef = useRef(false);
  const audioRefreshInFlightRef = useRef(false);
  const skipLinkRef = useRef<HTMLAnchorElement | null>(null);
  const workspaceRef = useRef<HTMLElement | null>(null);
  const scrollViewportRef = useRef<HTMLDivElement | null>(null);

  const liveState = state ?? EMPTY_STATE;
  const multimodalLive = Boolean(liveState.settings.multimodal_live_enabled);

  useEffect(() => {
    if (multimodalLive && providerTab === "llm") {
      setProviderTab("transcription");
    }
  }, [multimodalLive, providerTab]);
  const resolvedTheme: SystemTheme = "dark";
  const accentColor = String(liveState.settings.accent_color || DEFAULT_ACCENT_COLOR);
  const themeStyle = useMemo(
    () => buildThemeStyle(accentColor, resolvedTheme),
    [accentColor, resolvedTheme],
  );
  const activeSection = sectionMeta(liveState.currentSection);

  const applySnapshot = useEffectEvent(
    (snapshot: BridgeState) => {
      startTransition(() => {
        setState((current) => {
          const nextState = mergeRuntimeSnapshot(current, snapshot);
          return shouldReuseSnapshot(current, nextState) ? current : nextState;
        });
        setBridgeError("");
        setDrafts((current) => {
          if (!editingField || current[editingField] === undefined) {
            return Object.keys(current).length === 0 ? current : {};
          }
          return { [editingField]: current[editingField] };
        });
      });
    },
  );

  const applyRuntimeStatus = useEffectEvent((runtimeStatus: RuntimeStatusPayload) => {
    startTransition(() => {
      setState((current) => {
        const baseState = current ?? EMPTY_STATE;
        if (runtimeStatus.runtimeRevision < baseState.runtimeRevision) {
          return current;
        }
        return { ...baseState, ...pickRuntimeStatus(runtimeStatus) };
      });
      setBridgeError("");
    });
  });

  const refreshState = useEffectEvent(async () => {
    const bridge = getBridge();
    if (!bridge) {
      setBridgeError("Open Glance from the tray to reconnect.");
      return;
    }

    if (refreshInFlightRef.current) {
      return;
    }

    refreshInFlightRef.current = true;

    try {
      applySnapshot(await bridge.getState());
    } catch (error) {
      setBridgeError(formatError(error));
    } finally {
      refreshInFlightRef.current = false;
    }
  });

  useEffect(() => {
    void refreshState();
  }, []);

  const refreshVisibleState = useEffectEvent(() => {
    if (document.visibilityState !== "visible") {
      return;
    }
    void refreshState();
  });

  const refreshAudioState = useEffectEvent(async () => {
    const bridge = getBridge();
    if (!bridge || typeof bridge.getAudioState !== "function") {
      return;
    }
    if (audioRefreshInFlightRef.current) {
      return;
    }

    audioRefreshInFlightRef.current = true;
    try {
      const audioState = await bridge.getAudioState();
      startTransition(() => {
        setState((current) => ({
          ...(current ?? EMPTY_STATE),
          ...audioState,
        }));
      });
      setBridgeError("");
    } catch (error) {
      setBridgeError(formatError(error));
    } finally {
      audioRefreshInFlightRef.current = false;
    }
  });

  useEffect(() => {
    const bridge = getBridge();
    if (
      !bridge ||
      typeof bridge.subscribeRuntimeStatus !== "function" ||
      typeof bridge.unsubscribeRuntimeStatus !== "function"
    ) {
      return;
    }

    const subscriptionId = bridge.subscribeRuntimeStatus((runtimeStatus) => {
      applyRuntimeStatus(runtimeStatus);
    });

    return () => {
      bridge.unsubscribeRuntimeStatus(subscriptionId);
    };
  }, []);

  useEffect(() => {
    setIsMacOs(isMacDesktopPlatform());
  }, []);

  useEffect(() => {
    window.addEventListener("focus", refreshVisibleState);
    document.addEventListener("visibilitychange", refreshVisibleState);
    return () => {
      window.removeEventListener("focus", refreshVisibleState);
      document.removeEventListener("visibilitychange", refreshVisibleState);
    };
  }, []);

  const enableSkipLinkOnTab = useEffectEvent((event: KeyboardEvent) => {
    if (event.key !== "Tab" || event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }

    const activeElement = document.activeElement;
    const shouldFocusSkipLink =
      activeElement === null ||
      activeElement === document.body ||
      activeElement === document.documentElement;

    if (!shouldFocusSkipLink) {
      return;
    }

    setSkipLinkEnabled(true);
    event.preventDefault();
    window.requestAnimationFrame(() => {
      skipLinkRef.current?.focus({ preventScroll: true });
    });
  });

  const hideSkipLink = useEffectEvent(() => {
    if (document.activeElement === skipLinkRef.current) {
      skipLinkRef.current?.blur();
    }
    setSkipLinkEnabled(false);
  });

  const hideSkipLinkWhenHidden = useEffectEvent(() => {
    if (document.visibilityState === "visible") {
      return;
    }
    hideSkipLink();
  });

  useEffect(() => {
    window.addEventListener("keydown", enableSkipLinkOnTab, true);
    window.addEventListener("pointerdown", hideSkipLink, true);
    window.addEventListener("blur", hideSkipLink);
    document.addEventListener("visibilitychange", hideSkipLinkWhenHidden);
    return () => {
      window.removeEventListener("keydown", enableSkipLinkOnTab, true);
      window.removeEventListener("pointerdown", hideSkipLink, true);
      window.removeEventListener("blur", hideSkipLink);
      document.removeEventListener("visibilitychange", hideSkipLinkWhenHidden);
    };
  }, []);

  useEffect(() => {
    if (!liveState.dirty) {
      return;
    }

    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [liveState.dirty]);

  const transientRefreshActive =
    liveState.previewActive ||
    liveState.speakerTestActive ||
    liveState.saving;

  useEffect(() => {
    if (!transientRefreshActive) {
      return;
    }

    const interval = window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }
      void refreshState();
    }, 700);

    return () => window.clearInterval(interval);
  }, [transientRefreshActive]);

  useEffect(() => {
    if (!liveState.audioInputTestActive) {
      return;
    }

    void refreshAudioState();
    const interval = window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }
      void refreshAudioState();
    }, 90);

    return () => window.clearInterval(interval);
  }, [liveState.audioInputTestActive]);

  const closeSelectOnOutsideInteraction = useEffectEvent((event: PointerEvent) => {
    if (!openSelect) {
      return;
    }
    if (
      event.target instanceof Element &&
      event.target.closest("[data-select-root='true']")
    ) {
      return;
    }
    setOpenSelect(null);
  });

  useEffect(() => {
    window.addEventListener("pointerdown", closeSelectOnOutsideInteraction, true);
    return () => {
      window.removeEventListener(
        "pointerdown",
        closeSelectOnOutsideInteraction,
        true,
      );
    };
  }, []);

  const closeSelectOnEscape = useEffectEvent((event: KeyboardEvent) => {
    if (event.key !== "Escape" || !openSelect) {
      return;
    }
    setOpenSelect(null);
  });

  useEffect(() => {
    window.addEventListener("keydown", closeSelectOnEscape, true);
    return () => {
      window.removeEventListener("keydown", closeSelectOnEscape, true);
    };
  }, []);

  const blockGlobalSelectAll = useEffectEvent((event: KeyboardEvent) => {
    if (liveState.bindingActive) {
      return;
    }
    if (event.key.toLowerCase() !== "a" || (!event.metaKey && !event.ctrlKey)) {
      return;
    }

    const target = event.target;
    const editable =
      target instanceof HTMLElement &&
      (
        target.isContentEditable ||
        target.closest("input, textarea, [contenteditable='true'], [role='textbox']")
      );

    if (editable) {
      return;
    }

    event.preventDefault();
  });

  useEffect(() => {
    window.addEventListener("keydown", blockGlobalSelectAll, true);
    return () => {
      window.removeEventListener("keydown", blockGlobalSelectAll, true);
    };
  }, []);

  const routeWheelToScrollHost = useEffectEvent((event: WheelEvent) => {
    const workspace = workspaceRef.current;
    const defaultViewport = scrollViewportRef.current;
    if (!workspace || !defaultViewport) {
      return;
    }
    if (!(event.target instanceof Element) || !workspace.contains(event.target)) {
      return;
    }

    const resolveScrollableHost = (candidate: HTMLElement | null) => {
      if (!candidate || candidate.scrollHeight <= candidate.clientHeight + 1) {
        return null;
      }
      return candidate;
    };

    const canScrollInDirection = (element: HTMLElement, deltaY: number) => {
      if (deltaY < 0) {
        return element.scrollTop > 0;
      }
      return element.scrollTop + element.clientHeight < element.scrollHeight - 1;
    };

    const normalizeDelta = (deltaY: number, deltaMode: number) => {
      if (deltaMode === WheelEvent.DOM_DELTA_LINE) {
        return deltaY * 18;
      }
      if (deltaMode === WheelEvent.DOM_DELTA_PAGE) {
        return deltaY * defaultViewport.clientHeight;
      }
      return deltaY;
    };

    const nextDeltaY = normalizeDelta(event.deltaY, event.deltaMode);
    if (Math.abs(nextDeltaY) < 0.01) {
      return;
    }

    const closestScrollHost = event.target.closest(
      "[data-scroll-host='true']",
    ) as HTMLElement | null;
    const primaryHost =
      resolveScrollableHost(closestScrollHost) ??
      resolveScrollableHost(defaultViewport);

    if (!primaryHost) {
      return;
    }

    if (canScrollInDirection(primaryHost, nextDeltaY)) {
      event.preventDefault();
      primaryHost.scrollTop += nextDeltaY;
      return;
    }

    if (
      primaryHost !== defaultViewport &&
      canScrollInDirection(defaultViewport, nextDeltaY)
    ) {
      event.preventDefault();
      defaultViewport.scrollTop += nextDeltaY;
    }
  });

  useEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) {
      return;
    }
    workspace.addEventListener("wheel", routeWheelToScrollHost, {
      passive: false,
      capture: true,
    });
    return () => {
      workspace.removeEventListener("wheel", routeWheelToScrollHost, true);
    };
  }, []);

  const captureShortcut = useEffectEvent(async (event: KeyboardEvent) => {
    if (!liveState.bindingActive || !liveState.bindingField) {
      return;
    }

    const bridge = getBridge();
    if (!bridge) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    if (event.repeat) {
      return;
    }

    if (event.key === "Escape") {
      try {
        applySnapshot(await bridge.runAction("cancelKeybindCapture"));
      } catch (error) {
        setBridgeError(formatError(error));
      }
      return;
    }

    const keybind = eventToKeybind(event);
    if (!keybind) {
      return;
    }

    try {
      applySnapshot(await bridge.assignKeybind(liveState.bindingField, keybind));
    } catch (error) {
      setBridgeError(formatError(error));
    }
  });

  useEffect(() => {
    if (!liveState.bindingActive) {
      return;
    }

    window.addEventListener("keydown", captureShortcut, true);
    return () => {
      window.removeEventListener("keydown", captureShortcut, true);
    };
  }, [liveState.bindingActive]);

  const getDraftValue = useMemo(() => {
    return (fieldName: string) => {
      if (drafts[fieldName] !== undefined) {
        return drafts[fieldName];
      }
      const value = liveState.settings[fieldName];
      return value === null || value === undefined ? "" : String(value);
    };
  }, [drafts, liveState.settings]);

  async function withSnapshot(task: Promise<BridgeState>) {
    try {
      const snapshot = await task;
      applySnapshot(snapshot);
    } catch (error) {
      setBridgeError(formatError(error));
    }
  }

  function handleSectionSelect(section: SectionId) {
    const bridge = getBridge();
    setOpenSelect(null);
    if (!bridge) {
      setState((current) =>
        current ? { ...current, currentSection: section } : { ...EMPTY_STATE, currentSection: section },
      );
      return;
    }
    void withSnapshot(bridge.setSection(section));
  }

  function handleToggleSelect(fieldName: string) {
    setOpenSelect((current) => (current === fieldName ? null : fieldName));
  }

  function handleSelectValue(fieldName: string, value: string) {
    const bridge = getBridge();
    setOpenSelect(null);
    if (!bridge) {
      setState((current) => {
        const nextState = current ?? EMPTY_STATE;
        return {
          ...nextState,
          settings: {
            ...nextState.settings,
            [fieldName]: value,
          },
        };
      });
      return;
    }
    void withSnapshot(bridge.setField(fieldName, value));
  }

  function handleSetField(
    fieldName: string,
    value: string | number | boolean,
  ) {
    const bridge = getBridge();
    setOpenSelect(null);
    if (!bridge) {
      setState((current) => {
        const nextState = current ?? EMPTY_STATE;
        return {
          ...nextState,
          settings: {
            ...nextState.settings,
            [fieldName]: value,
          },
        };
      });
      return;
    }
    void withSnapshot(bridge.setField(fieldName, value));
  }

  function handleDraftChange(fieldName: string, value: string) {
    setDrafts((current) => ({ ...current, [fieldName]: value }));
  }

  function handleDraftFocus(fieldName: string) {
    setEditingField(fieldName);
  }

  function handleDraftCommit(fieldName: string, value: string) {
    const bridge = getBridge();
    setEditingField((current) => (current === fieldName ? null : current));
    if (!bridge) {
      return;
    }
    void withSnapshot(bridge.setField(fieldName, value));
  }

  function handleToggleReveal(fieldName: string) {
    setRevealedFields((current) => ({
      ...current,
      [fieldName]: !current[fieldName],
    }));
  }

  function handleRunAction(
    action: string,
    payload?: Record<string, string | number | boolean>,
  ) {
    const bridge = getBridge();
    if (!bridge) {
      return;
    }
    void withSnapshot(bridge.runAction(action, payload));
  }

  function handleStartKeybindCapture(fieldName: string) {
    const bridge = getBridge();
    if (!bridge) {
      return;
    }
    void withSnapshot(
      bridge.runAction("startKeybindCapture", { fieldName }),
    );
  }

  const footerStatus = bridgeError
    ? "Not connected"
    : liveState.saving
      ? "Saving provider changes"
      : liveState.manualSaveDirty
        ? "Provider changes not saved"
        : liveState.dirty
          ? "Fix highlighted fields"
          : "All changes saved";

  const discardLabel = liveState.manualSaveDirty
    ? "Discard provider changes"
    : "Discard changes";

  return (
    <GlanceAppShell
      state={liveState}
      title={activeSection.title}
      description={activeSection.description}
      footerStatus={footerStatus}
      discardLabel={discardLabel}
      theme={resolvedTheme}
      skipLinkEnabled={skipLinkEnabled}
      skipLinkRef={skipLinkRef}
      workspaceRef={workspaceRef}
      scrollViewportRef={scrollViewportRef}
      style={themeStyle}
      selectOpen={openSelect !== null}
      onSelectSection={handleSectionSelect}
      onSave={() => handleRunAction("save")}
      onDiscard={() => handleRunAction("reset")}
    >
      {bridgeError ? (
        <div
          className="mb-4 rounded-2xl border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm font-medium text-red-100"
          role="alert"
        >
          {bridgeError}
        </div>
      ) : null}

      <Notice state={liveState} />

      <SettingsTab
        state={liveState}
        stateReady={state !== null}
        providerTab={providerTab}
        openSelect={openSelect}
        audioLevel={liveState.audioInputLevel}
        revealedFields={revealedFields}
        onChangeProviderTab={setProviderTab}
        onToggleSelect={handleToggleSelect}
        onSelectValue={handleSelectValue}
        onSetField={handleSetField}
        onDraftChange={handleDraftChange}
        onDraftCommit={handleDraftCommit}
        onDraftFocus={handleDraftFocus}
        onToggleReveal={handleToggleReveal}
        onRunAction={handleRunAction}
        onStartKeybindCapture={handleStartKeybindCapture}
        getDraftValue={getDraftValue}
      />
    </GlanceAppShell>
  );
}
