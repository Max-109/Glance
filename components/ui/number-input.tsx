import type { KeyboardEvent } from "react";

import { Icon } from "../icons";

function formatStepValue(nextValue: number, step: number) {
  const precision = `${step}`.includes(".")
    ? `${step}`.split(".")[1]?.length ?? 0
    : 0;
  return nextValue.toFixed(precision).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

export function NumberInput({
  fieldName,
  label,
  value,
  helperText,
  errorText,
  icon,
  suffix,
  inputMode = "decimal",
  placeholder,
  step,
  min,
  max,
  onFocus,
  onChange,
  onCommit,
}: {
  fieldName: string;
  label: string;
  value: string;
  helperText?: string;
  errorText?: string;
  icon?: string;
  suffix?: string;
  inputMode?: "decimal" | "numeric";
  placeholder?: string;
  step: number;
  min?: number;
  max?: number;
  onFocus?: () => void;
  onChange: (value: string) => void;
  onCommit: (value: string) => void;
}) {
  const describedBy = errorText
    ? `${fieldName}-error`
    : helperText
      ? `${fieldName}-helper`
      : undefined;

  const adjustValue = (direction: -1 | 1) => {
    const parsedValue = Number.parseFloat(value);
    const baseValue = Number.isFinite(parsedValue)
      ? parsedValue
      : typeof min === "number"
        ? min
        : 0;
    let nextValue = baseValue + direction * step;
    if (typeof min === "number") {
      nextValue = Math.max(min, nextValue);
    }
    if (typeof max === "number") {
      nextValue = Math.min(max, nextValue);
    }
    const nextDraft = formatStepValue(nextValue, step);
    onChange(nextDraft);
    onCommit(nextDraft);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      adjustValue(1);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      adjustValue(-1);
    }
  };

  return (
    <label className="field">
      <span className="field__label">{label}</span>
      <span
        className={`field__control-shell field__control-shell--stepper${errorText ? " has-error" : ""}`}
      >
        {icon ? (
          <span className="field__icon">
            <Icon name={icon} />
          </span>
        ) : null}
        <input
          className={`control${errorText ? " is-error" : ""}`}
          value={value}
          type="text"
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
        <span className="stepper-buttons">
          <button
            type="button"
            className="stepper-button"
            aria-label={`Decrease ${label}`}
            onClick={() => adjustValue(-1)}
          >
            <Icon name="minus" />
          </button>
          <button
            type="button"
            className="stepper-button"
            aria-label={`Increase ${label}`}
            onClick={() => adjustValue(1)}
          >
            <Icon name="plus" />
          </button>
        </span>
      </span>
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
