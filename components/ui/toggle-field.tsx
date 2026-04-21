import { Icon } from "../icons";

export function ToggleField({
  label,
  helperText,
  checked,
  onChange,
  icon = "check",
}: {
  label: string;
  helperText?: string;
  checked: boolean;
  onChange: (nextValue: boolean) => void;
  icon?: string;
}) {
  return (
    <div className={`toggle-field${checked ? " toggle-field--checked" : ""}`}>
      <div className="toggle-field__copy">
        <div className="toggle-field__label">{label}</div>
        {helperText ? <div className="toggle-field__meta">{helperText}</div> : null}
      </div>
      <button
        type="button"
        className={`toggle-switch${checked ? " is-checked" : ""}`}
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
      >
        <span className="toggle-switch__thumb" aria-hidden="true">
          <Icon name={icon} />
        </span>
      </button>
    </div>
  );
}
