import type { ReactNode } from "react";

import { Icon } from "../icons";

export type StatusPillTone = "accent" | "warm" | "danger" | "neutral";

export function StatusPill({
  tone = "neutral",
  label,
  icon,
  pulse = false,
  children,
  className = "",
}: {
  tone?: StatusPillTone;
  label?: string;
  icon?: string;
  pulse?: boolean;
  children?: ReactNode;
  className?: string;
}) {
  const toneClass = `status-pill--${tone}`;
  const pulseClass = pulse ? " status-pill--pulse" : "";
  const extra = className ? ` ${className}` : "";

  return (
    <span className={`status-pill ${toneClass}${pulseClass}${extra}`}>
      {icon ? (
        <span className="status-pill__icon">
          <Icon name={icon} />
        </span>
      ) : (
        <span className="status-pill__dot" />
      )}
      <span>{children ?? label}</span>
    </span>
  );
}
