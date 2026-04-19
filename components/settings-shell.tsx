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
import type { PointerEvent as ReactPointerEvent } from "react";

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
    llm_reasoning: "minimal",
    transcription_base_url: "https://api.naga.ac/v1",
    transcription_api_key: "",
    transcription_model_name: "gemini-3.1-flash-lite-preview",
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
  const workspaceRef = useRef<HTMLElement | null>(null);
  const scrollViewportRef = useRef<HTMLDivElement | null>(null);

  const liveState = state ?? EMPTY_STATE;
  const deferredAudioLevel = useDeferredValue(liveState.audioInputLevel);
  const thresholdValue = thresholdDraft ?? Number(liveState.settings.audio_activation_threshold || 0.026);
  const themePreference = String(liveState.settings.theme_preference || "dark");
  const resolvedTheme =
    themePreference === "system" ? systemTheme : (themePreference as SystemTheme);
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
      setBridgeError("Desktop bridge unavailable. Open Glance from the tray to connect the Python runtime.");
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

  function handleHideWindow() {
    const bridge = getBridge();
    if (!bridge) {
      return;
    }
    void bridge.hideWindow();
  }

  function handleThresholdPointerDown(
    event: ReactPointerEvent<HTMLDivElement>,
  ) {
    const bridge = getBridge();
    const track = event.currentTarget;

    const updateThreshold = (clientX: number) => {
      const rect = track.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      setThresholdDraft(Number(ratio.toFixed(3)));
      return ratio;
    };

    let lastRatio = updateThreshold(event.clientX);

    const handlePointerMove = (moveEvent: PointerEvent) => {
      lastRatio = updateThreshold(moveEvent.clientX);
    };

    const handlePointerUp = () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      setThresholdDraft(null);

      if (!bridge) {
        return;
      }

      void withSnapshot(
        bridge.setField(
          "audio_activation_threshold",
          Number(lastRatio.toFixed(3)),
        ),
      );
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  }

  const footerStatus = bridgeError
    ? "Bridge unavailable"
    : liveState.saving
      ? "Applying changes"
      : liveState.dirty
        ? "Unsaved changes"
        : "All changes saved";

  return (
    <main className="desktop-shell" data-theme={resolvedTheme}>
      <a className="skip-link" href="#workspace-content">
        Skip to Content
      </a>

      <div className="desktop-shell__frame">
        <Sidebar
          state={liveState}
          onSelectSection={handleSectionSelect}
          onStartKeybindCapture={handleStartKeybindCapture}
        />

        <section className="workspace-shell" ref={workspaceRef}>
          <header className="workspace-shell__header">
            <div className="workspace-shell__title-block">
              <h1>{activeSection.title}</h1>
              <p>{activeSection.description}</p>
            </div>

            <Button
              icon="close"
              variant="ghost"
              ariaLabel="Close settings"
              className="workspace-shell__close"
              onClick={handleHideWindow}
            />
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
              onDraftChange={handleDraftChange}
              onDraftCommit={handleDraftCommit}
              onDraftFocus={handleDraftFocus}
              onToggleReveal={handleToggleReveal}
              onRunAction={handleRunAction}
              onThresholdPointerDown={handleThresholdPointerDown}
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
                label="Check settings"
                icon="settings"
                variant="secondary"
                onClick={() => handleRunAction("validateDraft")}
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
