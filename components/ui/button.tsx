import { Icon } from "../icons";

export function Button({
  label,
  variant = "secondary",
  icon,
  disabled = false,
  ariaLabel,
  className = "",
  onClick,
}: {
  label?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "signal";
  icon?: string;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
  onClick?: () => void | Promise<void>;
}) {
  return (
    <button
      type="button"
      className={`app-button app-button--${variant}${className ? ` ${className}` : ""}`}
      disabled={disabled}
      aria-label={ariaLabel}
      onClick={() => void onClick?.()}
    >
      {icon ? (
        <span className="app-button__icon">
          <Icon name={icon} />
        </span>
      ) : null}
      {label ? <span>{label}</span> : null}
    </button>
  );
}
