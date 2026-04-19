"use client";

import {
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useMemo,
  useRef,
  useState,
} from "react";
import type {
  CSSProperties,
  PointerEvent as ReactPointerEvent,
} from "react";

import { sectionMeta, type BridgeState, type SectionId } from "@/lib/glance-bridge";
import { eventToKeybind } from "@/lib/keybinds";

import { Button, Sidebar, StatusBanner } from "./ui";
import { SettingsSections } from "./settings-sections";

type ProviderTab = "llm" | "speech" | "transcription";
type SystemTheme = "dark" | "light";

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
    tts_base_url: "https://api.naga.ac/v1",
    tts_api_key: "",
    tts_model: "eleven-v3",
    tts_voice_id: "auto",
    fallback_language: "en",
    history_length: 50,
    screenshot_interval: 1.5,
    screen_change_threshold: 0.08,
    batch_window_duration: 4,
    audio_input_device: "default",
    audio_output_device: "default",
    audio_activation_threshold: 0.026,
    audio_silence_seconds: 2,
    audio_max_wait_seconds: 30,
    audio_max_record_seconds: 100,
    audio_preroll_seconds: 0.25,
    system_prompt_override: "",
    theme_preference: "dark",
    accent_color: "#a7ffde",
  },
  errors: {},
  dirty: false,
  saving: false,
  statusMessage: "",
  statusKind: "neutral",
  runtimeState: "idle",
  runtimeMessage: "Live session idle.",
  audioInputDeviceOptions: ["default"],
  audioInputDeviceLabels: { default: "System Default Input" },
  audioOutputDeviceOptions: ["default"],
  audioOutputDeviceLabels: { default: "System Default Output" },
  audioDeviceStatusMessage: "Connect the Python bridge to read live device state.",
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
  voiceOptions: ["auto"],
  voiceOptionLabels: {
    auto: "Auto - Pick the best curated Eleven v3 voice for each reply",
  },
  languageOptions: ["en", "lt", "fr", "de", "es"],
  historyPreview: [],
};

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
  return "The Electron bridge is unavailable right now.";
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function normalizeHexColor(value: string) {
  const trimmedValue = value.trim().toLowerCase();
  if (!trimmedValue) {
    return "#a7ffde";
  }
  const withHash = trimmedValue.startsWith("#") ? trimmedValue : `#${trimmedValue}`;
  if (!/^#[0-9a-f]{6}$/.test(withHash)) {
    return "#a7ffde";
  }
  return withHash;
}

function hexToRgb(hex: string) {
  const normalizedHex = normalizeHexColor(hex).slice(1);
  return {
    r: Number.parseInt(normalizedHex.slice(0, 2), 16),
    g: Number.parseInt(normalizedHex.slice(2, 4), 16),
    b: Number.parseInt(normalizedHex.slice(4, 6), 16),
  };
}

function rgbToHex({ r, g, b }: { r: number; g: number; b: number }) {
  return `#${[r, g, b]
    .map((channel) => clamp(Math.round(channel), 0, 255).toString(16).padStart(2, "0"))
    .join("")}`;
}

function rgbToHsl({ r, g, b }: { r: number; g: number; b: number }) {
  const red = r / 255;
  const green = g / 255;
  const blue = b / 255;
  const max = Math.max(red, green, blue);
  const min = Math.min(red, green, blue);
  const lightness = (max + min) / 2;
  const delta = max - min;

  if (delta === 0) {
    return { h: 0, s: 0, l: lightness * 100 };
  }

  const saturation = delta / (1 - Math.abs(2 * lightness - 1));

  let hue = 0;
  if (max === red) {
    hue = ((green - blue) / delta) % 6;
  } else if (max === green) {
    hue = (blue - red) / delta + 2;
  } else {
    hue = (red - green) / delta + 4;
  }

  return {
    h: Math.round(((hue * 60) + 360) % 360),
    s: saturation * 100,
    l: lightness * 100,
  };
}

function hslToRgb(h: number, s: number, l: number) {
  const normalizedS = clamp(s, 0, 100) / 100;
  const normalizedL = clamp(l, 0, 100) / 100;
  const chroma = (1 - Math.abs(2 * normalizedL - 1)) * normalizedS;
  const segment = h / 60;
  const second = chroma * (1 - Math.abs((segment % 2) - 1));
  const match = normalizedL - chroma / 2;

  let red = 0;
  let green = 0;
  let blue = 0;
  if (segment >= 0 && segment < 1) {
    red = chroma;
    green = second;
  } else if (segment < 2) {
    red = second;
    green = chroma;
  } else if (segment < 3) {
    green = chroma;
    blue = second;
  } else if (segment < 4) {
    green = second;
    blue = chroma;
  } else if (segment < 5) {
    red = second;
    blue = chroma;
  } else {
    red = chroma;
    blue = second;
  }

  return {
    r: (red + match) * 255,
    g: (green + match) * 255,
    b: (blue + match) * 255,
  };
}

function hslToHex(h: number, s: number, l: number) {
  return rgbToHex(hslToRgb(h, s, l));
}

function toRgba(hex: string, alpha: number) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function relativeLuminance({ r, g, b }: { r: number; g: number; b: number }) {
  const transform = (channel: number) => {
    const value = channel / 255;
    return value <= 0.03928
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4;
  };
  return (
    0.2126 * transform(r) +
    0.7152 * transform(g) +
    0.0722 * transform(b)
  );
}

function buildThemeStyle(
  accentColor: string,
  resolvedTheme: SystemTheme,
): CSSProperties {
  const accentHex = normalizeHexColor(accentColor);
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

export function SettingsShell() {
  const [state, setState] = useState<BridgeState | null>(null);
  const [systemTheme, setSystemTheme] = useState<SystemTheme>("dark");
  const [providerTab, setProviderTab] = useState<ProviderTab>("llm");
  const [openSelect, setOpenSelect] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [revealedFields, setRevealedFields] = useState<Record<string, boolean>>({});
  const [bridgeError, setBridgeError] = useState("");
  const [thresholdDraft, setThresholdDraft] = useState<number | null>(null);
  const thresholdCommitRef = useRef(0);
  const skipLinkRef = useRef<HTMLAnchorElement | null>(null);
  const workspaceRef = useRef<HTMLElement | null>(null);
  const scrollViewportRef = useRef<HTMLDivElement | null>(null);

  const liveState = state ?? EMPTY_STATE;
  const deferredAudioLevel = useDeferredValue(liveState.audioInputLevel);
  const thresholdValue = thresholdDraft ?? Number(liveState.settings.audio_activation_threshold || 0.026);
  const themePreference = String(liveState.settings.theme_preference || "dark");
  const resolvedTheme =
    themePreference === "system" ? systemTheme : (themePreference as SystemTheme);
  const accentColor = String(liveState.settings.accent_color || "#a7ffde");
  const themeStyle = useMemo(
    () => buildThemeStyle(accentColor, resolvedTheme),
    [accentColor, resolvedTheme],
  );
  const activeSection = sectionMeta(liveState.currentSection);

  const applySnapshot = useEffectEvent(
    (snapshot: BridgeState, nextSystemTheme?: SystemTheme) => {
      startTransition(() => {
        setState(snapshot);
        setBridgeError("");
        setDrafts((current) => {
          if (!editingField || current[editingField] === undefined) {
            return {};
          }
          return { [editingField]: current[editingField] };
        });
        if (nextSystemTheme) {
          setSystemTheme(nextSystemTheme);
        }
      });
    },
  );

  const refreshState = useEffectEvent(async () => {
    const bridge = getBridge();
    if (!bridge) {
      setBridgeError("Open Glance from the tray to reconnect the desktop bridge.");
      return;
    }

    try {
      const [snapshot, nextSystemTheme] = await Promise.all([
        bridge.getState(),
        bridge.getSystemTheme().catch(() => systemTheme),
      ]);
      applySnapshot(snapshot, nextSystemTheme);
    } catch (error) {
      setBridgeError(formatError(error));
    }
  });

  useEffect(() => {
    void refreshState();
  }, [refreshState]);

  const focusWorkspaceViewport = useEffectEvent(() => {
    const viewport = scrollViewportRef.current;
    if (!viewport) {
      return;
    }

    const activeElement = document.activeElement;
    const shouldMoveFocus =
      activeElement === null ||
      activeElement === document.body ||
      activeElement === document.documentElement ||
      activeElement === skipLinkRef.current;

    if (!shouldMoveFocus) {
      return;
    }

    viewport.focus({ preventScroll: true });
  });

  useEffect(() => {
    const syncFocus = () => {
      window.requestAnimationFrame(() => {
        focusWorkspaceViewport();
      });
    };

    syncFocus();
    window.addEventListener("focus", syncFocus);
    return () => {
      window.removeEventListener("focus", syncFocus);
    };
  }, [focusWorkspaceViewport]);

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

  const pollMs =
    liveState.audioInputTestActive ||
    liveState.previewActive ||
    liveState.speakerTestActive ||
    liveState.saving
      ? 240
      : 1200;

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshState();
    }, pollMs);

    return () => window.clearInterval(interval);
  }, [pollMs, refreshState]);

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
  }, [closeSelectOnOutsideInteraction]);

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
  }, [closeSelectOnEscape]);

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
  }, [blockGlobalSelectAll]);

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
  }, [routeWheelToScrollHost]);

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
  }, [captureShortcut, liveState.bindingActive]);

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

  async function commitThreshold(nextValue: number) {
    const bridge = getBridge();
    const normalizedValue = clamp(Number(nextValue.toFixed(3)), 0.001, 1);
    const requestId = thresholdCommitRef.current + 1;
    thresholdCommitRef.current = requestId;
    setThresholdDraft(normalizedValue);

    if (!bridge) {
      setThresholdDraft(null);
      return;
    }

    try {
      const snapshot = await bridge.setField(
        "audio_activation_threshold",
        normalizedValue,
      );
      if (thresholdCommitRef.current !== requestId) {
        return;
      }
      applySnapshot(snapshot);
    } catch (error) {
      if (thresholdCommitRef.current !== requestId) {
        return;
      }
      setBridgeError(formatError(error));
    } finally {
      if (thresholdCommitRef.current === requestId) {
        setThresholdDraft(null);
      }
    }
  }

  function handleThresholdPointerDown(
    event: ReactPointerEvent<HTMLDivElement>,
  ) {
    const track = event.currentTarget;

    const updateThreshold = (clientY: number) => {
      const rect = track.getBoundingClientRect();
      const ratio = Math.min(
        1,
        Math.max(0, 1 - (clientY - rect.top) / rect.height),
      );
      setThresholdDraft(Number(ratio.toFixed(3)));
      return ratio;
    };

    let lastRatio = updateThreshold(event.clientY);

    const handlePointerMove = (moveEvent: PointerEvent) => {
      lastRatio = updateThreshold(moveEvent.clientY);
    };

    const handlePointerUp = () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      void commitThreshold(lastRatio);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  }

  function handleThresholdNudge(delta: number) {
    const nextValue = clamp(Number((thresholdValue + delta).toFixed(3)), 0.001, 1);
    void commitThreshold(nextValue);
  }

  const footerStatus = bridgeError
    ? "Bridge unavailable"
    : liveState.saving
      ? "Applying changes"
      : liveState.dirty
        ? "Unsaved changes"
        : "All changes saved";

  return (
    <main className="desktop-shell" data-theme={resolvedTheme} style={themeStyle}>
      <a
        ref={skipLinkRef}
        className="skip-link"
        href="#workspace-content"
      >
        Skip to Content
      </a>

      <div className="desktop-shell__frame">
        <Sidebar
          state={liveState}
          onSelectSection={handleSectionSelect}
        />

        <section className="workspace-shell" ref={workspaceRef}>
          <header className="workspace-shell__header">
            <div className="workspace-shell__title-block">
              <h1>{activeSection.title}</h1>
              <p>{activeSection.description}</p>
            </div>
          </header>

          {bridgeError ? (
            <div className="bridge-banner" role="alert">
              <span>{bridgeError}</span>
            </div>
          ) : null}

          <StatusBanner state={liveState} />

          <div
            className="workspace-shell__scroll"
            id="workspace-content"
            ref={scrollViewportRef}
            tabIndex={-1}
            data-scroll-host="true"
          >
            <SettingsSections
              state={liveState}
              providerTab={providerTab}
              openSelect={openSelect}
              thresholdValue={thresholdValue}
              audioLevel={deferredAudioLevel}
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
              onThresholdPointerDown={handleThresholdPointerDown}
              onThresholdNudge={handleThresholdNudge}
              onStartKeybindCapture={handleStartKeybindCapture}
              getDraftValue={getDraftValue}
            />
          </div>

          <footer className="action-dock">
            <div className="action-dock__status">{footerStatus}</div>
            <div className="action-dock__actions">
              <Button
                label="Save"
                icon="check"
                variant="primary"
                disabled={!liveState.dirty}
                onClick={() => handleRunAction("save")}
              />
              <Button
                label="Reset"
                icon="refresh"
                variant="ghost"
                disabled={!liveState.dirty}
                onClick={() => handleRunAction("reset")}
              />
            </div>
          </footer>
        </section>
      </div>
    </main>
  );
}
