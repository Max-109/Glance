import type { ReactNode } from "react";

export type PanelTone = "accent" | "soft" | "warm" | "danger" | "neutral" | "pulse";

export function Panel({
  title,
  description,
  status,
  summary,
  children,
  footer,
  footerAlign = "start",
  className = "",
}: {
  title?: string;
  description?: string;
  status?: { tone: PanelTone; label: string } | null;
  summary?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  footerAlign?: "start" | "end";
  className?: string;
}) {
  const hasToolbar = Boolean(title || description || summary);

  return (
    <section className={`panel${className ? ` ${className}` : ""}`}>
      {status ? (
        <div className={`panel__status panel__status--${status.tone}`}>
          <span className="panel__status-dot" />
          <span>{status.label}</span>
        </div>
      ) : null}

      {hasToolbar ? (
        <div className={`panel__toolbar${summary ? "" : " panel__toolbar--solo"}`}>
          <div className="panel__toolbar-heading">
            {title ? <span className="panel__toolbar-title">{title}</span> : null}
            {description ? (
              <p className="panel__toolbar-copy">{description}</p>
            ) : null}
          </div>
          {summary ? <div className="panel__toolbar-summary">{summary}</div> : null}
        </div>
      ) : null}

      {children ? <div className="panel__body">{children}</div> : null}

      {footer ? (
        <div className={`panel__chips${footerAlign === "end" ? " panel__chips--end" : ""}`}>
          {footer}
        </div>
      ) : null}
    </section>
  );
}
