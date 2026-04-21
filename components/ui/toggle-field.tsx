export function ToggleField({
  label,
  helperText,
  checked,
  onChange,
}: {
  label: string;
  helperText?: string;
  checked: boolean;
  onChange: (nextValue: boolean) => void;
}) {
  return (
    <div className="toggle-field">
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
        <span className="toggle-switch__thumb" />
      </button>
    </div>
  );
}
