import type { ReactNode } from "react";

import { Icon } from "../icons";

export function SelectInput({
  fieldName,
  label,
  value,
  options,
  labels,
  helperText,
  errorText,
  icon,
  optionIcons = {},
  open,
  className = "",
  actionSlot,
  capsValue = false,
  onToggle,
  onSelect,
}: {
  fieldName: string;
  label: string;
  value: string;
  options: string[];
  labels?: Record<string, string>;
  helperText?: string;
  errorText?: string;
  icon?: string;
  optionIcons?: Record<string, string>;
  open: boolean;
  className?: string;
  actionSlot?: ReactNode;
  capsValue?: boolean;
  onToggle: () => void;
  onSelect: (value: string) => void;
}) {
  const describedBy = errorText
    ? `${fieldName}-error`
    : helperText
      ? `${fieldName}-helper`
      : undefined;
  const menuId = `${fieldName}-options`;
  const resolvedIcon = optionIcons[value] || icon;
  const currentLabel = labels?.[value] || value || "Select";

  return (
    <div className="field">
      <label className="field__label">{label}</label>
      <div
        className={`select-shell${errorText ? " has-error" : ""}${className ? ` ${className}` : ""}`}
        data-select-root="true"
      >
        <div className="select-shell__row">
          <button
            type="button"
            className="control control--select"
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-label={label}
            aria-describedby={describedBy}
            aria-controls={open ? menuId : undefined}
            onClick={onToggle}
          >
            {resolvedIcon ? (
              <span className="field__icon">
                <Icon name={resolvedIcon} />
              </span>
            ) : null}
            <span className={`control__value${capsValue ? " is-caps" : ""}`}>
              {currentLabel}
            </span>
            <span className="control__chevron">
              <Icon name="chevron" />
            </span>
          </button>
          {actionSlot ? <div className="select-shell__action">{actionSlot}</div> : null}
        </div>
        {open ? (
          <div
            id={menuId}
            className="select-menu is-open"
            role="listbox"
            aria-label={label}
            data-scroll-host="true"
          >
            {options.map((optionValue) => {
              const selected = optionValue === value;
              const optionIcon = optionIcons[optionValue];
              return (
                <button
                  type="button"
                  key={optionValue}
                  className={`select-menu__option${selected ? " is-selected" : ""}`}
                  role="option"
                  aria-selected={selected}
                  onClick={() => onSelect(optionValue)}
                >
                  {optionIcon ? (
                    <span className="field__icon">
                      <Icon name={optionIcon} />
                    </span>
                  ) : null}
                  <span className={capsValue ? "is-caps" : undefined}>
                    {labels?.[optionValue] || optionValue}
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
      {errorText ? (
        <span className="field__meta field__meta--error" id={`${fieldName}-error`}>
          {errorText}
        </span>
      ) : helperText ? (
        <span className="field__meta" id={`${fieldName}-helper`}>
          {helperText}
        </span>
      ) : null}
    </div>
  );
}
