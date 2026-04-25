import type { CSSProperties, ReactNode, RefObject } from "react";

import { Icon } from "@/components/icons";
import { Indicator } from "@/components/ui/indicator";
import { SECTION_GROUPS, type BridgeState, type SectionId } from "@/lib/glance-bridge";
import { cn } from "@/lib/utils";

import { GlanceButton } from "./button";

const RUNTIME_LABELS: Record<string, string> = {
  idle: "Idle",
  listening: "Listening",
  processing: "Transcribing",
  transcribing: "Transcribing",
  generating: "Generating",
  speaking: "Speaking",
  error: "Error",
};

export function GlanceAppShell({
  state,
  title,
  description,
  footerStatus,
  discardLabel,
  theme = "dark",
  skipLinkEnabled,
  skipLinkRef,
  workspaceRef,
  scrollViewportRef,
  style,
  selectOpen,
  children,
  onSelectSection,
  onSave,
  onDiscard,
}: {
  state: BridgeState;
  title: string;
  description: string;
  footerStatus: string;
  discardLabel: string;
  theme?: "dark" | "light";
  skipLinkEnabled: boolean;
  skipLinkRef: RefObject<HTMLAnchorElement | null>;
  workspaceRef: RefObject<HTMLElement | null>;
  scrollViewportRef: RefObject<HTMLDivElement | null>;
  style?: CSSProperties;
  selectOpen?: boolean;
  children: ReactNode;
  onSelectSection: (section: SectionId) => void;
  onSave: () => void;
  onDiscard: () => void;
}) {
  const runtimeLabel = RUNTIME_LABELS[state.runtimeState] || RUNTIME_LABELS.idle;

  return (
    <main
      className={cn(
        "glance-redesign min-h-[100dvh] overflow-hidden text-[var(--text-strong)]",
        theme === "dark" && "dark",
      )}
      data-theme={theme}
      style={style}
    >
      {skipLinkEnabled ? (
        <a
          ref={skipLinkRef}
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--card)] focus:px-4 focus:py-2 focus:text-sm focus:text-[var(--text-strong)]"
          href="#workspace-content"
        >
          Skip to content
        </a>
      ) : null}

      <div className="grid h-[100dvh] grid-cols-1 overflow-hidden md:grid-cols-[17rem_minmax(0,1fr)]">
        <aside className="electron-drag-region hidden min-h-0 border-r border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.035),transparent_32%),var(--sidebar-bg)] md:flex md:flex-col">
          <div className="h-14 shrink-0" aria-hidden="true" />

          <div className="flex items-center gap-4 px-6 pb-6 text-[var(--text-muted)]">
            <Indicator
              state={state.runtimeState}
              size="large"
              label={`Glance live state: ${runtimeLabel}`}
              phaseStartedAtMs={state.runtimePhaseStartedAtMs}
              blinkIntervalMs={state.runtimeBlinkIntervalMs}
              errorFlashUntilMs={state.runtimeErrorFlashUntilMs}
            />
            <div className="min-w-0">
              <p className="text-2xl font-bold tracking-[-0.035em] text-[var(--text-strong)]">
                Glance
              </p>
              <span className="mt-1 inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.035] px-2.5 py-1 font-mono text-[0.72rem] font-bold tracking-[0.18em] uppercase text-[var(--text-muted)]">
                <span className="size-1.5 rounded-full bg-current opacity-70" />
                {runtimeLabel}
              </span>
            </div>
          </div>

          <nav className="electron-no-drag-region min-h-0 flex-1 overflow-y-auto px-4 pb-5" aria-label="Sections">
            {SECTION_GROUPS.map((group, index) => (
              <section
                key={group.items[0]?.id ?? index}
                className="border-t border-white/10 py-4 first:border-t-0"
              >
                <div className="grid gap-2">
                  {group.items.map((item) => {
                    const selected = state.currentSection === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        className={cn(
                          "group relative flex h-10 items-center gap-3 rounded-xl px-3 text-left text-sm font-medium text-[var(--text-muted)] transition-[background-color,color]",
                          selected
                            ? "bg-white/[0.075] text-[var(--text-strong)]"
                            : "hover:bg-white/[0.045] hover:text-[var(--text-strong)]",
                        )}
                        aria-current={selected ? "page" : undefined}
                        onClick={() => onSelectSection(item.id)}
                      >
                        {selected ? (
                          <span className="absolute left-0 h-6 w-1 rounded-full bg-[var(--accent)] shadow-[0_0_20px_var(--accent-glow)]" />
                        ) : null}
                        <span
                          className={cn(
                            "grid size-8 place-items-center rounded-xl border border-white/10 bg-white/[0.04] transition-colors",
                            selected &&
                              "border-[color-mix(in_srgb,var(--accent)_50%,transparent)] bg-[color-mix(in_srgb,var(--accent)_18%,transparent)] text-[var(--accent-strong)]",
                          )}
                        >
                          <Icon name={item.icon} className="size-5" />
                        </span>
                        <span className="min-w-0 truncate">{item.title}</span>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </nav>
        </aside>

        <section
          ref={workspaceRef}
          className="relative flex min-w-0 flex-col overflow-hidden bg-[var(--page-bg)]"
        >
          <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-[linear-gradient(180deg,rgba(255,255,255,0.018),transparent)]" />

          <header className="electron-drag-region relative z-10 shrink-0 px-5 pb-4 pt-6 md:px-7 lg:px-9">
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--text-strong)]">
              {title}
            </h1>
            <p className="mt-1.5 text-sm text-[var(--text-muted)]">{description}</p>
          </header>

          <div
            ref={scrollViewportRef}
            id="workspace-content"
            tabIndex={-1}
            data-scroll-host="true"
            className={cn(
              "electron-no-drag-region relative min-h-0 flex-1 overflow-y-auto px-5 pb-6 md:px-7 lg:px-9",
              selectOpen ? "z-40" : "z-10",
            )}
          >
            {children}
          </div>

          <footer className="electron-no-drag-region relative z-20 flex shrink-0 items-center justify-between gap-4 border-t border-white/8 bg-[rgba(9,9,10,0.92)] px-5 py-5 backdrop-blur-xl md:px-7 lg:px-9">
            <span className="min-w-0 truncate text-sm text-[var(--text-muted)]">
              {footerStatus}
            </span>
            <div className="flex items-center gap-2">
              {state.manualSaveDirty ? (
                <GlanceButton icon="check" variant="primary" onClick={onSave}>
                  Save Provider Changes
                </GlanceButton>
              ) : null}
              <GlanceButton
                icon="undo"
                variant="secondary"
                disabled={!state.dirty}
                onClick={onDiscard}
              >
                {discardLabel}
              </GlanceButton>
            </div>
          </footer>
        </section>
      </div>
    </main>
  );
}
