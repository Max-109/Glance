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
    notice: "I'll take a quick screenshot.",
    description: "Use the current screen when the question needs visual context.",
  },
  {
    id: "search",
    title: "Web Search",
    icon: "world-search",
    policyField: "tool_web_search_policy",
    notice: "I'll search the web for that.",
    description: "Look up recent or changing information from public results.",
  },
  {
    id: "fetch",
    title: "Web Fetch",
    icon: "fetch",
    policyField: "tool_web_fetch_policy",
    notice: "I'll read that page.",
    description: "Read a specific page when a link matters to the answer.",
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

  return (
    <div className="grid gap-5">
      <section className="overflow-hidden rounded-2xl border border-white/10 bg-card shadow-none">
        <div className="border-b border-white/10 px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <span className="grid size-11 place-items-center rounded-2xl border border-[color-mix(in_srgb,var(--accent)_36%,transparent)] bg-[color-mix(in_srgb,var(--accent)_14%,transparent)] text-[var(--accent-strong)]">
                  <Icon name="tools" className="size-5" />
                </span>
                <div>
                  <h2 className="text-base font-semibold text-[var(--text-strong)]">
                    Live tools
                  </h2>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">
                    Let Glance decide when a screenshot or web lookup would help.
                  </p>
                </div>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <StatusBadge tone={masterEnabled ? "accent" : "disabled"}>
                {masterEnabled ? `${enabledCount} enabled` : "off"}
              </StatusBadge>
              <Switch
                checked={masterEnabled}
                onCheckedChange={(value) => onSetField("tools_enabled", value)}
                aria-label="Enable Live tools"
              />
            </div>
          </div>
        </div>

        <div className="grid gap-4 px-5 py-5 lg:grid-cols-3">
          {TOOL_CARDS.map((tool) => {
            const enabled = policyEnabled(settingValue(state, tool.policyField));
            return (
              <ToolCard
                key={tool.id}
                title={tool.title}
                description={tool.description}
                icon={tool.icon}
                notice={tool.notice}
                enabled={enabled}
                masterEnabled={masterEnabled}
                onChange={(value) =>
                  onSetField(tool.policyField, value ? "allow" : "deny")
                }
              />
            );
          })}
        </div>
      </section>
    </div>
  );
}

function ToolCard({
  title,
  description,
  icon,
  notice,
  enabled,
  masterEnabled,
  onChange,
}: {
  title: string;
  description: string;
  icon: string;
  notice: string;
  enabled: boolean;
  masterEnabled: boolean;
  onChange: (value: boolean) => void;
}) {
  const active = masterEnabled && enabled;
  return (
    <article
      className={cn(
        "flex min-h-[18rem] flex-col rounded-2xl border bg-black/10 p-5 transition-[border-color,background-color,box-shadow]",
        active
          ? "border-[color-mix(in_srgb,var(--accent)_42%,rgba(255,255,255,0.1))] bg-[color-mix(in_srgb,var(--accent)_8%,transparent)] shadow-[0_0_0_1px_color-mix(in_srgb,var(--accent)_8%,transparent)]"
          : "border-white/10",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <span
          className={cn(
            "grid size-12 shrink-0 place-items-center rounded-2xl border border-white/10 bg-white/[0.045] text-[var(--text-muted)]",
            active &&
              "border-[color-mix(in_srgb,var(--accent)_42%,transparent)] bg-[color-mix(in_srgb,var(--accent)_16%,transparent)] text-[var(--accent-strong)]",
          )}
        >
          <Icon name={icon} className="size-5" />
        </span>
        <Switch checked={enabled} onCheckedChange={onChange} aria-label={title} />
      </div>

      <div className="mt-5 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-semibold text-[var(--text-strong)]">{title}</h3>
          <StatusBadge tone={enabled ? "accent" : "disabled"}>
            {enabled ? "allowed" : "denied"}
          </StatusBadge>
        </div>
        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          {description}
        </p>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.035] px-3 py-3">
        <p className="font-mono text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--text-muted)]">
          spoken first
        </p>
        <p className="mt-1 text-sm text-[var(--text-strong)]">{notice}</p>
      </div>

    </article>
  );
}
