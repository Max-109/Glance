import { Icon } from "../icons";

export function Button({
  label,
  variant = "secondary",
  icon,
  disabled = false,
  ariaLabel,
  className = "",
  active = false,
  onClick,
}: {
  label?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "signal";
  icon?: string;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
  active?: boolean;
  onClick?: () => void | Promise<void>;
}) {
  return (
    <button
      type="button"
      className={`app-button app-button--${variant}${className ? ` ${className}` : ""}`}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-pressed={active || undefined}
      data-active={active ? "true" : undefined}
      onClick={() => void onClick?.()}
    >
      {icon ? (
        <span className="app-button__icon icon--toggle" key={icon} data-enter="true">
          <Icon name={icon} />
        </span>
      ) : null}
      {label ? <span>{label}</span> : null}
    </button>
  );
}
