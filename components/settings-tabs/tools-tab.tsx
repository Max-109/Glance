import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Icon } from "@/components/icons";
import { StatusBadge } from "@/components/settings-shell/status-badge";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

import type { SettingsTabProps } from "./shared";
import { settingValue } from "./shared";

const TOOL_CARDS = [
  {
    id: "screenshot",
    title: "Screenshot",
    icon: "photo-search",
    policyField: "tool_take_screenshot_policy",
    description: "Use the current screen when visual context would help.",
  },
  {
    id: "ocr",
    title: "OCR",
    icon: "capture",
    policyField: "tool_ocr_policy",
    description: "Extract exact visible text and tables, then copy them to clipboard.",
  },
  {
    id: "search",
    title: "Web Search",
    icon: "world-search",
    policyField: "tool_web_search_policy",
    description: "Look up recent or changing information from the web.",
  },
  {
    id: "fetch",
    title: "Open Page",
    icon: "fetch",
    policyField: "tool_web_fetch_policy",
    description: "Open a specific page when the link matters.",
  },
  {
    id: "memory",
    title: "Memory",
    icon: "memory",
    policyField: "tool_add_memory_policy",
    description: "Save tasks, ideas, and project notes when you ask.",
  },
  {
    id: "read-memory",
    title: "Read Memory",
    icon: "memory",
    policyField: "tool_read_memory_policy",
    description: "Find saved notes when you ask about them.",
  },
] as const;

function policyEnabled(value: string) {
  return value === "allow";
}

export function ToolsTab({
  state,
  onSetField,
}: Pick<
  SettingsTabProps,
  "state" | "onSetField"
>) {
  const masterEnabled = state.settings.tools_enabled === true;
  const enabledCount = TOOL_CARDS.filter((tool) =>
    policyEnabled(settingValue(state, tool.policyField)),
  ).length;
  const disabledCount = TOOL_CARDS.length - enabledCount;

  return (
    <div className="grid gap-4">
      <Card className="shell-surface gap-0 overflow-hidden rounded-2xl py-0 shadow-none">
        <CardHeader className="border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-4">
              <span
                className={cn(
                  "grid size-12 shrink-0 place-items-center rounded-2xl border border-[var(--panel-border)] bg-[var(--chip-bg-soft)] text-[var(--text-muted)]",
                  masterEnabled && "text-[var(--accent-strong)]",
                )}
              >
                <Icon name="tools" className="size-5" />
              </span>
              <div className="min-w-0">
                <div className="flex min-w-0 flex-wrap items-center gap-3">
                  <CardTitle className="text-base font-semibold">Tools</CardTitle>
                  <StatusBadge tone={masterEnabled ? "accent" : "disabled"}>
                    {masterEnabled ? `${enabledCount} enabled` : "off"}
                  </StatusBadge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Choose which tools Glance can access.
                </p>
              </div>
            </div>
            <Switch
              checked={masterEnabled}
              onCheckedChange={(value) => onSetField("tools_enabled", value)}
              aria-label="Enable tools"
            />
          </div>
        </CardHeader>

        <CardContent className="grid gap-5 px-5 py-5">
          <div className="grid gap-4 xl:grid-cols-[minmax(17rem,0.48fr)_minmax(0,1fr)]">
            <section
              className={cn(
                "flex min-h-[24rem] flex-col rounded-2xl border border-[var(--panel-border)] bg-[var(--panel-bg-deep)] p-5 transition-[background-color,opacity]",
              )}
              aria-label="Tools access"
            >
              <div className="flex min-w-0 items-start justify-between gap-4">
                <span
                  className={cn(
                    "grid size-14 shrink-0 place-items-center rounded-2xl border border-[var(--panel-border)] bg-[var(--chip-bg-soft)] text-[var(--text-muted)]",
                    masterEnabled && "text-[var(--accent-strong)]",
                  )}
                >
                  <Icon name="tools" className="size-6" />
                </span>
                <Switch
                  checked={masterEnabled}
                  onCheckedChange={(value) => onSetField("tools_enabled", value)}
                  aria-label="Enable tools"
                />
              </div>

              <div className="mt-6">
                <div className="text-lg font-semibold text-[var(--text-strong)]">
                  Tool access
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                  {masterEnabled
                    ? "Allow or block tools for Live."
                    : "Tool use is paused. Your choices stay saved."}
                </p>
              </div>

              <div className="mt-6 border-t border-[var(--panel-divider)] pt-5">
                <div className="grid grid-cols-2 gap-3">
                  <ToolMetric label="Allowed" value={enabledCount} active={masterEnabled} />
                  <ToolMetric label="Blocked" value={disabledCount} active={false} />
                </div>
              </div>
            </section>

            <section className="grid gap-3" aria-label="Tool permissions">
              {TOOL_CARDS.map((tool) => {
                const enabled = policyEnabled(settingValue(state, tool.policyField));
                return (
                  <ToolPermissionRow
                    key={tool.id}
                    title={tool.title}
                    description={tool.description}
                    icon={tool.icon}
                    enabled={enabled}
                    masterEnabled={masterEnabled}
                    onChange={(value) =>
                      onSetField(tool.policyField, value ? "allow" : "deny")
                    }
                  />
                );
              })}
            </section>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ToolMetric({
  label,
  value,
  active,
}: {
  label: string;
  value: number;
  active: boolean;
}) {
  return (
    <div className="rounded-2xl border border-[var(--panel-border)] bg-[var(--chip-bg-soft)] px-4 py-3">
      <div
        className={cn(
          "font-mono text-2xl font-semibold",
          active ? "text-[var(--accent-strong)]" : "text-[var(--text-strong)]",
        )}
      >
        {value}
      </div>
      <div className="mt-1 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
        {label}
      </div>
    </div>
  );
}

function ToolPermissionRow({
  title,
  description,
  icon,
  enabled,
  masterEnabled,
  onChange,
}: {
  title: string;
  description: string;
  icon: string;
  enabled: boolean;
  masterEnabled: boolean;
  onChange: (value: boolean) => void;
}) {
  const active = masterEnabled && enabled;
  return (
    <div
      className={cn(
        "grid min-h-[7.25rem] grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-5 rounded-2xl border border-[var(--panel-border)] bg-[var(--panel-bg-deep)] p-5 transition-[background-color,opacity]",
        !masterEnabled && "opacity-70",
        !active && "hover:bg-[var(--item-hover)]",
      )}
    >
      <span
        className={cn(
          "grid size-12 shrink-0 place-items-center rounded-2xl border border-[var(--panel-border)] bg-[var(--chip-bg-soft)] text-[var(--text-muted)]",
          active && "text-[var(--accent-strong)]",
        )}
      >
        <Icon name={icon} className="size-5" />
      </span>

      <div className="min-w-0">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <h3 className="truncate text-base font-semibold text-[var(--text-strong)]">
            {title}
          </h3>
          <StatusBadge tone={enabled ? "accent" : "disabled"}>
            {enabled ? "allowed" : "blocked"}
          </StatusBadge>
        </div>
        <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">{description}</p>
      </div>

      <Switch checked={enabled} onCheckedChange={onChange} aria-label={title} />
    </div>
  );
}
