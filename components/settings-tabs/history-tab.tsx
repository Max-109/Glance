import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlanceButton } from "@/components/settings-shell/button";
import { NumberField } from "@/components/settings-shell/form-controls";
import { StatusBadge } from "@/components/settings-shell/status-badge";
import { Switch } from "@/components/ui/switch";
import { Icon } from "@/components/icons";
import { cn } from "@/lib/utils";

import { HistoryPreviewCard } from "./history-preview-card";
import type { SettingsTabProps } from "./shared";

function settingBoolean(
  state: SettingsTabProps["state"],
  fieldName: string,
  fallback = true,
): boolean {
  const value = state.settings[fieldName];
  if (value === undefined || value === null) return fallback;
  if (typeof value === "boolean") return value;
  return String(value).toLowerCase() === "true";
}

function parseLimit(value: string): number {
  const parsedValue = Number.parseInt(value, 10);
  return Number.isFinite(parsedValue) ? Math.max(1, parsedValue) : 50;
}

function formatShortDate(value: string) {
  if (!value) return "None yet";
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function retentionCopy(enabled: boolean, limit: number, total: number) {
  if (!enabled) {
    return "Saved sessions stay here until you delete them.";
  }
  if (total > limit) {
    return `Glance will keep the newest ${limit} sessions and remove the older ones.`;
  }
  return `Glance keeps up to ${limit} sessions. Older ones are removed after that.`;
}

export function HistoryTab({
  state,
  onDraftChange,
  onDraftCommit,
  onDraftFocus,
  onRunAction,
  onSetField,
  getDraftValue,
}: Pick<
  SettingsTabProps,
  | "state"
  | "onDraftChange"
  | "onDraftCommit"
  | "onDraftFocus"
  | "onRunAction"
  | "onSetField"
  | "getDraftValue"
>) {
  const hasSessions = state.historyPreview.length > 0;
  const retentionEnabled = settingBoolean(state, "history_retention_enabled");
  const historyLimit = parseLimit(getDraftValue("history_length"));
  const totalSessions = state.historyStats.totalSessions;
  const fillPercent = retentionEnabled
    ? Math.min(100, Math.round((totalSessions / historyLimit) * 100))
    : 100;

  return (
    <Card className="shell-surface gap-0 rounded-2xl py-0 shadow-none">
      <CardHeader className="border-b border-border px-5 py-4">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base font-semibold">History</CardTitle>
            <CardDescription>
              Keep the useful sessions close and decide when old ones leave.
            </CardDescription>
          </div>
          <StatusBadge tone={hasSessions ? "accent" : "neutral"}>
            {hasSessions ? "Recent activity" : "No sessions"}
          </StatusBadge>
        </div>
      </CardHeader>

      <CardContent className="grid gap-4 px-5 py-5">
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
          <div
            className={cn(
              "rounded-2xl border bg-card p-4 transition-[border-color,box-shadow]",
              retentionEnabled
                ? "border-[color-mix(in_srgb,var(--accent)_34%,rgba(255,255,255,0.1))] shadow-[0_0_0_1px_color-mix(in_srgb,var(--accent)_8%,transparent)]"
                : "border-white/10",
            )}
          >
            <div className="flex min-w-0 items-start gap-4">
              <button
                type="button"
                className={cn(
                  "grid size-13 shrink-0 place-items-center rounded-2xl border transition-[background-color,border-color,color,transform] active:scale-95 focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_12%,transparent)]",
                  retentionEnabled
                    ? "border-[color-mix(in_srgb,var(--accent)_46%,transparent)] bg-[color-mix(in_srgb,var(--accent)_17%,transparent)] text-[var(--accent-strong)]"
                    : "border-white/10 bg-white/[0.035] text-[var(--text-muted)] hover:bg-white/[0.055]",
                )}
                aria-label={
                  retentionEnabled
                    ? "Turn off automatic history cleanup"
                    : "Turn on automatic history cleanup"
                }
                aria-pressed={retentionEnabled}
                onClick={() =>
                  onSetField("history_retention_enabled", !retentionEnabled)
                }
              >
                <Icon name="history" className="size-6" />
              </button>

              <div className="min-w-0 flex-1">
                <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="text-base font-semibold text-[var(--text-strong)]">
                      Auto clean history
                    </h3>
                    <p className="mt-1 max-w-[58ch] text-sm leading-6 text-[var(--text-muted)]">
                      {retentionCopy(retentionEnabled, historyLimit, totalSessions)}
                    </p>
                  </div>
                  <Switch
                    checked={retentionEnabled}
                    onCheckedChange={(checked) =>
                      onSetField("history_retention_enabled", checked)
                    }
                    aria-label="Auto clean history"
                  />
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,16rem)_1fr]">
                  <NumberField
                    fieldName="history_length"
                    label="Keep latest"
                    icon="history"
                    suffix="sessions"
                    inputMode="numeric"
                    step={1}
                    min={1}
                    value={getDraftValue("history_length")}
                    errorText={state.errors.history_length}
                    helperText={
                      retentionEnabled
                        ? "Newest sessions are kept first."
                        : "Used when auto clean is on."
                    }
                    onChange={(value) => onDraftChange("history_length", value)}
                    onCommit={(value) => onDraftCommit("history_length", value)}
                    onFocus={() => onDraftFocus("history_length")}
                  />

                  <div className="self-end rounded-2xl border border-white/10 bg-white/[0.025] p-4">
                    <div className="flex items-center justify-between gap-3 text-xs text-[var(--text-muted)]">
                      <span>{retentionEnabled ? "Retention meter" : "Cleanup paused"}</span>
                      <span className="font-mono tabular-nums">
                        {retentionEnabled
                          ? `${Math.min(totalSessions, historyLimit)} / ${historyLimit}`
                          : `${totalSessions} saved`}
                      </span>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/[0.055]">
                      <div
                        className={cn(
                          "h-full rounded-full transition-[width,background-color]",
                          retentionEnabled ? "bg-[var(--accent)]" : "bg-white/20",
                        )}
                        style={{ width: `${fillPercent}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <HistoryStat label="Saved" value={String(totalSessions)} />
            <HistoryStat
              label={retentionEnabled ? "Limit" : "Cleanup"}
              value={retentionEnabled ? String(historyLimit) : "Off"}
            />
            <HistoryStat
              label="Oldest"
              value={formatShortDate(state.historyStats.oldestAt)}
            />
            <HistoryStat
              label="Newest"
              value={formatShortDate(state.historyStats.newestAt)}
            />
          </div>
        </div>

        {hasSessions ? (
          <section className="grid gap-3" aria-label="Recent saved sessions">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-[var(--text-strong)]">
                  Latest sessions
                </h3>
                <p className="mt-1 text-sm text-[var(--text-muted)]">
                  The newest saves are shown first.
                </p>
              </div>
              <span className="font-mono text-xs text-[var(--text-muted)]">
                Showing {state.historyPreview.length}
              </span>
            </div>
            <div className="grid gap-3">
              {state.historyPreview.map((item, index) => (
                <HistoryPreviewCard
                  key={item.id}
                  item={item}
                  featured={index === 0}
                />
              ))}
            </div>
          </section>
        ) : (
          <div className="rounded-2xl border border-border bg-card p-5">
            <span className="mb-4 grid size-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.035] text-[var(--text-muted)]">
              <Icon name="history" className="size-5" />
            </span>
            <strong className="block text-sm font-semibold text-foreground">
              Nothing here yet
            </strong>
            <span className="mt-1 block text-sm text-muted-foreground">
              Sessions show up after you use Live, Quick Ask, or Read Screen.
            </span>
          </div>
        )}
      </CardContent>

      <CardFooter className="gap-3 border-t border-border px-5 py-4">
        <GlanceButton
          icon="trash"
          variant="danger"
          onClick={() => {
            if (!window.confirm("Delete all saved history on this device?")) {
              return;
            }
            onRunAction("clearHistory");
          }}
        >
          Delete history
        </GlanceButton>
        <div className="text-sm text-muted-foreground">
          Deletes every saved session on this device.
        </div>
      </CardFooter>
    </Card>
  );
}

function HistoryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-card p-4">
      <span className="block font-mono text-[0.64rem] font-bold uppercase tracking-[0.16em] text-[var(--text-muted)]">
        {label}
      </span>
      <strong className="mt-2 block truncate text-lg font-semibold tabular-nums text-[var(--text-strong)]">
        {value}
      </strong>
    </div>
  );
}
