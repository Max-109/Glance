import { useEffect, useRef, useState } from "react";

import type { BridgeState } from "@/lib/glance-bridge";

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

export function HistoryPreviewCard({
  item,
}: {
  item: BridgeState["historyPreview"][number];
}) {
  const [expanded, setExpanded] = useState(false);
  const [canExpand, setCanExpand] = useState(false);
  const excerptRef = useRef<HTMLParagraphElement | null>(null);

  useEffect(() => {
    const element = excerptRef.current;
    if (!element) {
      return;
    }

    const measureOverflow = () => {
      const nextOverflow = element.scrollHeight > element.clientHeight + 1;
      setCanExpand((current) => (expanded ? current || nextOverflow : nextOverflow));
    };

    measureOverflow();
    window.addEventListener("resize", measureOverflow);
    return () => window.removeEventListener("resize", measureOverflow);
  }, [item.excerpt, expanded]);

  return (
    <article className="session-card">
      <div className="session-card__meta">
        <span>{formatHistoryDate(item.createdAt)}</span>
        <span>{item.mode.toUpperCase()}</span>
        <span>{item.interactionCount} turns</span>
      </div>
      <strong>{item.title}</strong>
      <p
        ref={excerptRef}
        className={`session-card__excerpt${expanded ? " is-expanded" : ""}`}
      >
        {item.excerpt}
      </p>
      {canExpand ? (
        <button
          type="button"
          className="session-card__toggle"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Read less" : "Read more"}
        </button>
      ) : null}
    </article>
  );
}
