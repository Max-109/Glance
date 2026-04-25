import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/icons";
import type { BridgeState } from "@/lib/glance-bridge";
import { cn } from "@/lib/utils";

function formatHistoryDate(value: string) {
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

function formatRelativeDate(value: string) {
  try {
    const timestamp = new Date(value).getTime();
    const diffMs = timestamp - Date.now();
    const absoluteDiff = Math.abs(diffMs);
    const minute = 60_000;
    const hour = 60 * minute;
    const day = 24 * hour;
    const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
    if (absoluteDiff < hour) {
      return formatter.format(Math.round(diffMs / minute), "minute");
    }
    if (absoluteDiff < day) {
      return formatter.format(Math.round(diffMs / hour), "hour");
    }
    return formatter.format(Math.round(diffMs / day), "day");
  } catch {
    return "";
  }
}

function modeMeta(mode: string) {
  const normalizedMode = mode.toLowerCase();
  if (normalizedMode === "quick") {
    return {
      label: "Legacy",
      icon: "replies",
      tone: "text-sky-300",
      rail: "bg-sky-300",
    };
  }
  if (normalizedMode === "ocr") {
    return {
      label: "OCR",
      icon: "capture",
      tone: "text-emerald-300",
      rail: "bg-emerald-300",
    };
  }
  return {
    label: "Live",
    icon: "wave",
    tone: "text-[var(--accent-strong)]",
    rail: "bg-[var(--accent)]",
  };
}

export function HistoryPreviewCard({
  item,
  featured = false,
}: {
  item: BridgeState["historyPreview"][number];
  featured?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [canExpand, setCanExpand] = useState(false);
  const excerptRef = useRef<HTMLParagraphElement | null>(null);
  const meta = modeMeta(item.mode);
  const relativeDate = formatRelativeDate(item.createdAt);

  useEffect(() => {
    const element = excerptRef.current;
    if (!element) return;

    const measureOverflow = () => {
      const nextOverflow = element.scrollHeight > element.clientHeight + 1;
      setCanExpand((current) => (expanded ? current || nextOverflow : nextOverflow));
    };

    measureOverflow();
    window.addEventListener("resize", measureOverflow);
    return () => window.removeEventListener("resize", measureOverflow);
  }, [item.excerpt, expanded]);

  return (
    <article
      className={cn(
        "group relative overflow-hidden rounded-2xl border bg-card transition-[background-color,border-color,box-shadow,transform] hover:-translate-y-px hover:bg-white/[0.035]",
        featured
          ? "border-[color-mix(in_srgb,var(--accent)_38%,rgba(255,255,255,0.1))] shadow-[0_0_0_1px_color-mix(in_srgb,var(--accent)_8%,transparent)]"
          : "border-white/10",
      )}
    >
      <span
        className={cn(
          "absolute bottom-4 left-0 top-4 w-1 rounded-r-full opacity-75",
          featured ? "bg-[var(--accent)]" : meta.rail,
        )}
      />
      <div className="grid gap-4 p-4 md:grid-cols-[2.75rem_minmax(0,1fr)_auto]">
        <div
          className={cn(
            "grid size-11 place-items-center rounded-2xl border border-white/10 bg-white/[0.035]",
            featured &&
              "border-[color-mix(in_srgb,var(--accent)_34%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)]",
          )}
        >
          <Icon
            name={meta.icon}
            className={cn("size-5", featured ? "text-[var(--accent-strong)]" : meta.tone)}
          />
        </div>

        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge
              variant="secondary"
              className={cn(
                "h-6 rounded-full px-2.5 font-mono text-[0.68rem] font-bold uppercase tracking-[0.14em]",
                featured &&
                  "border-[color-mix(in_srgb,var(--accent)_38%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--accent-strong)]",
              )}
            >
              {meta.label}
            </Badge>
            <span className="font-mono">{formatHistoryDate(item.createdAt)}</span>
            {relativeDate ? <span className="text-[var(--text-faint)]">{relativeDate}</span> : null}
            <span className="font-mono tabular-nums">{item.interactionCount} turns</span>
          </div>
          <strong className="block truncate text-sm font-semibold leading-6 text-foreground">
            {item.title}
          </strong>
          <p
            ref={excerptRef}
            className={cn(
              "mt-2 text-sm leading-6 text-muted-foreground",
              expanded ? "" : "line-clamp-2",
            )}
          >
            {item.excerpt || "No preview text was saved for this session."}
          </p>
          {canExpand ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-3 h-8 rounded-xl px-0 text-[var(--text-muted)] hover:text-[var(--text-strong)]"
              onClick={() => setExpanded((current) => !current)}
            >
              {expanded ? "Read less" : "Read more"}
            </Button>
          ) : null}
        </div>

        <div className="flex items-start justify-end">
          <span className="rounded-full border border-white/10 bg-white/[0.035] px-3 py-1.5 font-mono text-[0.68rem] font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]">
            #{item.id.slice(0, 5)}
          </span>
        </div>
      </div>
    </article>
  );
}
