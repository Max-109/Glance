import type {
  KeyboardEvent,
  PointerEvent as ReactPointerEvent,
  ReactNode,
} from "react";

import {
  SECTION_GROUPS,
  type BridgeState,
  type SectionId,
} from "@/lib/glance-bridge";

import { Icon } from "./icons";

const RUNTIME_LABELS: Record<string, string> = {
  idle: "Idle",
  listening: "Listening",
  processing: "Processing",
  speaking: "Speaking",
  ready: "Ready",
  error: "Attention",
};

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
  variant?: "primary" | "secondary" | "ghost" | "danger";
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

export function ActivityMark({
  state,
  size = "compact",
  label,
}: {
  state: string;
  size?: "compact" | "large";
  label?: string;
}) {
  return (
    <div
      className={`activity-mark activity-mark--${size}`}
      data-state={state || "idle"}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <span className="activity-mark__segment activity-mark__segment--west" />
      <span className="activity-mark__segment activity-mark__segment--north" />
      <span className="activity-mark__segment activity-mark__segment--east" />
      <span className="activity-mark__segment activity-mark__segment--south" />
    </div>
  );
}

export function StatusBanner({ state }: { state: BridgeState }) {
  if (!state.statusMessage) {
    return null;
  }

  const iconName =
    state.statusKind === "error"
      ? "close"
      : state.statusKind === "success"
        ? "check"
        : "settings";

  return (
    <div
      className={`status-banner status-banner--${state.statusKind || "neutral"}`}
      role="status"
      aria-live="polite"
    >
      <span className="status-banner__icon">
        <Icon name={iconName} />
      </span>
      <span className="status-banner__text">{state.statusMessage}</span>
    </div>
  );
}

export function GlassCard({
  title,
  description,
  children,
  className = "",
  footer,
}: {
  title: string;
  description: string;
  children: ReactNode;
  className?: string;
  footer?: ReactNode;
}) {
  return (
    <section className={`glass-card${className ? ` ${className}` : ""}`}>
      <header className="glass-card__header">
        <div>
          <h3 className="glass-card__title">{title}</h3>
          <p className="glass-card__description">{description}</p>
        </div>
      </header>
      <div className="glass-card__body">{children}</div>
      {footer ? <div className="glass-card__footer">{footer}</div> : null}
    </section>
  );
}

export function Sidebar({
  state,
  onSelectSection,
  onStartKeybindCapture,
}: {
  state: BridgeState;
  onSelectSection: (section: SectionId) => void;
  onStartKeybindCapture: (fieldName: string) => void;
}) {
  const runtimeLabel = RUNTIME_LABELS[state.runtimeState] || RUNTIME_LABELS.idle;
  const rows = [
    { id: "live_keybind", title: "Live", value: String(state.settings.live_keybind || "-") },
    { id: "quick_keybind", title: "Quick", value: String(state.settings.quick_keybind || "-") },
    { id: "ocr_keybind", title: "OCR", value: String(state.settings.ocr_keybind || "-") },
  ];

  return (
    <aside className="sidebar-shell">
      <div className="sidebar-brand">
        <ActivityMark
          state={state.runtimeState}
          size="large"
          label={`Glance live state: ${runtimeLabel}`}
        />
        <div className="sidebar-brand__copy">
          <p className="sidebar-brand__title">Glance</p>
        </div>
      </div>

      {SECTION_GROUPS.map((group) => (
        <section className="sidebar-group" key={group.label}>
          <p className="sidebar-group__label">{group.label}</p>
          <div className="sidebar-group__items">
            {group.items.map((item) => {
              const selected = state.currentSection === item.id;
              return (
                <button
                  type="button"
                  key={item.id}
                  className={`sidebar-item${selected ? " is-selected" : ""}`}
                  aria-current={selected ? "page" : undefined}
                  onClick={() => onSelectSection(item.id)}
                >
                  <span className="sidebar-item__icon">
                    <Icon name={item.icon} />
                  </span>
                  <span>{item.title}</span>
                </button>
              );
            })}
          </div>
        </section>
      ))}

      <section className="shortcut-card">
        <div className="shortcut-card__header">
          <h3>Shortcuts</h3>
          <p>
            {state.bindingActive
              ? "Press a shortcut, or Escape to cancel."
              : "Set the tray shortcuts without leaving settings."}
          </p>
        </div>
        <div className="shortcut-card__rows">
          {rows.map((row) => {
            const active = state.bindingField === row.id;
            return (
              <button
                type="button"
                key={row.id}
                className={`shortcut-row${active ? " is-capturing" : ""}`}
                onClick={() => onStartKeybindCapture(row.id)}
              >
                <span className="shortcut-row__label">{row.title}</span>
                <span className="shortcut-row__value">
                  {active ? "PRESS SHORTCUT" : row.value}
                </span>
              </button>
            );
          })}
        </div>
      </section>

    </aside>
  );
}

export function TextField({
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

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
    }
  };

  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {multiline ? (
        <div className="select-shell select-shell--textarea">
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
            onChange={(event) => onChange(event.currentTarget.value)}
            onBlur={(event) => onCommit(event.currentTarget.value)}
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
              onClick={onToggleReveal}
            >
              <Icon name="eye" />
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

export function SelectField({
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
  onToggle: () => void;
  onSelect: (value: string) => void;
}) {
  const describedBy = errorText
    ? `${fieldName}-error`
    : helperText
      ? `${fieldName}-helper`
      : undefined;
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
            onClick={onToggle}
          >
            {resolvedIcon ? (
              <span className="field__icon">
                <Icon name={resolvedIcon} />
              </span>
            ) : null}
            <span className="control__value">{currentLabel}</span>
            <span className="control__chevron">
              <Icon name="chevron" />
            </span>
          </button>
          {actionSlot ? <div className="select-shell__action">{actionSlot}</div> : null}
        </div>
        {open ? (
          <div
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
                  <span>{labels?.[optionValue] || optionValue}</span>
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

export function AudioMeter({
  level,
  threshold,
  active,
  onPointerDown,
}: {
  level: number;
  threshold: number;
  active: boolean;
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
}) {
  const normalizedLevel = Math.max(0, Math.min(1, level || 0));
  const normalizedThreshold = Math.max(0, Math.min(1, threshold || 0));

  return (
    <div className="audio-meter">
      <div className="audio-meter__track" onPointerDown={onPointerDown}>
        <div
          className={`audio-meter__glow${active ? " is-active" : ""}`}
          style={{ width: `${normalizedLevel * 100}%` }}
        />
        <button
          type="button"
          className="audio-meter__marker"
          aria-label="Adjust mic sensitivity"
          style={{ left: `${normalizedThreshold * 100}%` }}
        />
      </div>
      <div className="audio-meter__legend">
        <span>More sensitive</span>
        <span>More selective</span>
      </div>
    </div>
  );
}

export function SegmentedTabs({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: Array<{ id: string; label: string }>;
  activeTab: string;
  onChange: (tab: string) => void;
}) {
  return (
    <div className="segmented-tabs" role="tablist" aria-label="Provider stack">
      {tabs.map((tab) => {
        const selected = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            className={`segmented-tabs__tab${selected ? " is-active" : ""}`}
            aria-selected={selected}
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
