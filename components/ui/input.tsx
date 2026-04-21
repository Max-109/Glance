import type { KeyboardEvent } from "react";

import { Icon } from "../icons";

export function Input({
  fieldName,
  label,
  value,
  helperText,
  errorText,
  icon,
  suffix,
  multiline = false,
  inputMode,
  placeholder,
  secret = false,
  revealed = false,
  onFocus,
  onChange,
  onCommit,
  onToggleReveal,
}: {
  fieldName: string;
  label: string;
  value: string;
  helperText?: string;
  errorText?: string;
  icon?: string;
  suffix?: string;
  multiline?: boolean;
  inputMode?: "text" | "decimal" | "numeric" | "search" | "url";
  placeholder?: string;
  secret?: boolean;
  revealed?: boolean;
  onFocus?: () => void;
  onChange: (value: string) => void;
  onCommit: (value: string) => void;
  onToggleReveal?: () => void;
}) {
  const describedBy = errorText
    ? `${fieldName}-error`
    : helperText
      ? `${fieldName}-helper`
      : undefined;
  const inputType =
    secret && !revealed ? "password" : inputMode === "url" ? "url" : "text";

  const handleKeyDown = (
    event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    if (event.key === "Enter" && !multiline) {
      event.currentTarget.blur();
    }
  };

  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {multiline ? (
        <div className="field__control-shell field__control-shell--textarea">
          {icon ? (
            <span className="field__icon">
              <Icon name={icon} />
            </span>
          ) : null}
          <textarea
            className={`control control--textarea${errorText ? " is-error" : ""}`}
            value={value}
            name={fieldName}
            autoComplete="off"
            spellCheck={false}
            placeholder={placeholder}
            aria-describedby={describedBy}
            aria-invalid={errorText ? true : undefined}
            onChange={(event) => onChange(event.currentTarget.value)}
            onBlur={(event) => onCommit(event.currentTarget.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => onFocus?.()}
          />
        </div>
      ) : (
        <span className={`field__control-shell${errorText ? " has-error" : ""}`}>
          {icon ? (
            <span className="field__icon">
              <Icon name={icon} />
            </span>
          ) : null}
          <input
            className={`control${errorText ? " is-error" : ""}`}
            value={value}
            type={inputType}
            name={fieldName}
            inputMode={inputMode}
            autoComplete="off"
            spellCheck={false}
            placeholder={placeholder}
            aria-describedby={describedBy}
            aria-invalid={errorText ? true : undefined}
            onChange={(event) => onChange(event.currentTarget.value)}
            onBlur={(event) => onCommit(event.currentTarget.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => onFocus?.()}
          />
          {suffix ? <span className="field__suffix">{suffix}</span> : null}
          {secret && onToggleReveal ? (
            <button
              type="button"
              className="field__icon-button"
              aria-label={revealed ? "Hide secret" : "Show secret"}
              aria-pressed={revealed}
              onClick={onToggleReveal}
            >
              <span
                className="icon--toggle"
                key={revealed ? "eye-off" : "eye"}
                data-enter="true"
              >
                <Icon name={revealed ? "eye-off" : "eye"} />
              </span>
            </button>
          ) : null}
        </span>
      )}
      {errorText ? (
        <span className="field__meta field__meta--error" id={`${fieldName}-error`}>
          {errorText}
        </span>
      ) : helperText ? (
        <span className="field__meta" id={`${fieldName}-helper`}>
          {helperText}
        </span>
      ) : null}
    </label>
  );
}
