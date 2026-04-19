import {
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
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

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function formatStepValue(nextValue: number, step: number) {
  const precision = `${step}`.includes(".")
    ? `${step}`.split(".")[1]?.length ?? 0
    : 0;
  return nextValue.toFixed(precision).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

function normalizeHexColor(value: string) {
  const normalizedValue = value.trim().toLowerCase();
  if (!normalizedValue) {
    return "";
  }
  const withHash = normalizedValue.startsWith("#")
    ? normalizedValue
    : `#${normalizedValue}`;
  if (/^#[0-9a-f]{6}$/.test(withHash)) {
    return withHash;
  }
  return "";
}

function hexToRgb(hex: string) {
  const normalizedHex = normalizeHexColor(hex).slice(1);
  return {
    r: Number.parseInt(normalizedHex.slice(0, 2), 16),
    g: Number.parseInt(normalizedHex.slice(2, 4), 16),
    b: Number.parseInt(normalizedHex.slice(4, 6), 16),
  };
}

function rgbToHex({ r, g, b }: { r: number; g: number; b: number }) {
  return `#${[r, g, b]
    .map((channel) => clamp(Math.round(channel), 0, 255).toString(16).padStart(2, "0"))
    .join("")}`;
}

function rgbToHsl({ r, g, b }: { r: number; g: number; b: number }) {
  const red = r / 255;
  const green = g / 255;
  const blue = b / 255;
  const max = Math.max(red, green, blue);
  const min = Math.min(red, green, blue);
  const lightness = (max + min) / 2;
  const delta = max - min;

  if (delta === 0) {
    return { h: 0, s: 0, l: lightness * 100 };
  }

  const saturation = delta / (1 - Math.abs(2 * lightness - 1));

  let hue = 0;
  if (max === red) {
    hue = ((green - blue) / delta) % 6;
  } else if (max === green) {
    hue = (blue - red) / delta + 2;
  } else {
    hue = (red - green) / delta + 4;
  }

  return {
    h: Math.round(((hue * 60) + 360) % 360),
    s: saturation * 100,
    l: lightness * 100,
  };
}

function hslToRgb(h: number, s: number, l: number) {
  const normalizedS = clamp(s, 0, 100) / 100;
  const normalizedL = clamp(l, 0, 100) / 100;
  const chroma = (1 - Math.abs(2 * normalizedL - 1)) * normalizedS;
  const segment = h / 60;
  const second = chroma * (1 - Math.abs((segment % 2) - 1));
  const match = normalizedL - chroma / 2;

  let red = 0;
  let green = 0;
  let blue = 0;
  if (segment >= 0 && segment < 1) {
    red = chroma;
    green = second;
  } else if (segment < 2) {
    red = second;
    green = chroma;
  } else if (segment < 3) {
    green = chroma;
    blue = second;
  } else if (segment < 4) {
    green = second;
    blue = chroma;
  } else if (segment < 5) {
    red = second;
    blue = chroma;
  } else {
    red = chroma;
    blue = second;
  }

  return {
    r: (red + match) * 255,
    g: (green + match) * 255,
    b: (blue + match) * 255,
  };
}

function hslToHex(h: number, s: number, l: number) {
  return rgbToHex(hslToRgb(h, s, l));
}

function planeRatioFromLightness(lightness: number) {
  return clamp((84 - lightness) / 62, 0, 1);
}

function lightnessFromPlaneRatio(ratio: number) {
  return clamp(84 - ratio * 62, 22, 84);
}

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
}: {
  state: BridgeState;
  onSelectSection: (section: SectionId) => void;
}) {
  const runtimeLabel = RUNTIME_LABELS[state.runtimeState] || RUNTIME_LABELS.idle;

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
          <p className="sidebar-brand__status">{runtimeLabel}</p>
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

      <section className="runtime-card" aria-label="Live runtime status">
        <div className="runtime-card__label">Live Session</div>
        <div className="runtime-card__value">{runtimeLabel}</div>
        <p className="runtime-card__message">{state.runtimeMessage}</p>
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

export function StepperField({
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

export function AccentPicker({
  value,
  presets,
  onChange,
}: {
  value: string;
  presets: Array<{ label: string; value: string }>;
  onChange: (nextValue: string) => void;
}) {
  const normalizedValue = normalizeHexColor(value) || "#a7ffde";
  const initialPreset = presets.find(
    (preset) => preset.value.toLowerCase() === normalizedValue,
  );
  const [previewHex, setPreviewHex] = useState(normalizedValue);
  const [draftHex, setDraftHex] = useState(normalizedValue.toUpperCase());
  const [showCustomControls, setShowCustomControls] = useState(!initialPreset);
  const planeRef = useRef<HTMLDivElement | null>(null);
  const hueRef = useRef<HTMLDivElement | null>(null);
  const hexInputRef = useRef<HTMLInputElement | null>(null);
  const hslRef = useRef(rgbToHsl(hexToRgb(normalizedValue)));

  useEffect(() => {
    setPreviewHex(normalizedValue);
    setDraftHex(normalizedValue.toUpperCase());
    setShowCustomControls(
      !presets.some((preset) => preset.value.toLowerCase() === normalizedValue),
    );
  }, [normalizedValue]);

  useEffect(() => {
    hslRef.current = rgbToHsl(hexToRgb(previewHex));
  }, [previewHex]);

  const currentPreset = presets.find(
    (preset) => preset.value.toLowerCase() === previewHex,
  );
  const currentHsl = hslRef.current;

  const applyPreview = (nextHex: string, commit = false) => {
    const normalizedHex = normalizeHexColor(nextHex);
    if (!normalizedHex) {
      return;
    }
    setPreviewHex(normalizedHex);
    setDraftHex(normalizedHex.toUpperCase());
    hslRef.current = rgbToHsl(hexToRgb(normalizedHex));
    if (commit) {
      onChange(normalizedHex);
    }
  };

  const updateFromPlane = (clientX: number, clientY: number, commit = false) => {
    const rect = planeRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    const saturation = clamp(((clientX - rect.left) / rect.width) * 100, 0, 100);
    const lightness = lightnessFromPlaneRatio(
      clamp((clientY - rect.top) / rect.height, 0, 1),
    );
    applyPreview(hslToHex(hslRef.current.h, saturation, lightness), commit);
  };

  const updateFromHue = (clientX: number, commit = false) => {
    const rect = hueRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    const hue = clamp(((clientX - rect.left) / rect.width) * 360, 0, 360);
    applyPreview(hslToHex(hue, hslRef.current.s, hslRef.current.l), commit);
  };

  const startPointerDrag = (
    event: ReactPointerEvent<HTMLDivElement>,
    update: (clientX: number, clientY: number, commit?: boolean) => void,
  ) => {
    event.preventDefault();
    update(event.clientX, event.clientY);

    const handlePointerMove = (moveEvent: PointerEvent) => {
      update(moveEvent.clientX, moveEvent.clientY);
    };

    const handlePointerUp = (upEvent: PointerEvent) => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      update(upEvent.clientX, upEvent.clientY, true);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  };

  const startHueDrag = (
    event: ReactPointerEvent<HTMLDivElement>,
  ) => {
    event.preventDefault();
    updateFromHue(event.clientX);

    const handlePointerMove = (moveEvent: PointerEvent) => {
      updateFromHue(moveEvent.clientX);
    };

    const handlePointerUp = (upEvent: PointerEvent) => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      updateFromHue(upEvent.clientX, true);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  };

  return (
    <div className="accent-picker">
      <div className="accent-picker__swatches" role="radiogroup" aria-label="Accent color">
        <button
          type="button"
          role="radio"
          aria-checked={showCustomControls}
          className={`accent-swatch accent-swatch--custom${showCustomControls ? " is-active" : ""}`}
          onClick={() => {
            setShowCustomControls(true);
            window.requestAnimationFrame(() => hexInputRef.current?.focus());
          }}
        >
          <span
            className="accent-swatch__dot"
            style={{ "--swatch": previewHex } as CSSProperties}
          />
          <span>Custom</span>
        </button>
        {presets.map((preset) => {
          const selected = !showCustomControls && currentPreset?.value === preset.value;
          return (
            <button
              key={preset.value}
              type="button"
              role="radio"
              aria-checked={selected}
              className={`accent-swatch${selected ? " is-active" : ""}`}
              onClick={() => {
                setShowCustomControls(false);
                applyPreview(preset.value, true);
              }}
            >
              <span
                className="accent-swatch__dot"
                style={{ "--swatch": preset.value } as CSSProperties}
              />
              <span>{preset.label}</span>
            </button>
          );
        })}
      </div>

      {showCustomControls ? (
        <div className="accent-picker__detail">
          <div className="accent-tuner">
            <div
              ref={planeRef}
              className="accent-plane"
              style={{ "--accent-hue": `${currentHsl.h}deg` } as CSSProperties}
              onPointerDown={(event) => startPointerDrag(event, updateFromPlane)}
            >
              <span
                className="accent-plane__handle"
                style={{
                  left: `clamp(12px, ${currentHsl.s}%, calc(100% - 12px))`,
                  top: `clamp(12px, ${planeRatioFromLightness(currentHsl.l) * 100}%, calc(100% - 12px))`,
                }}
              />
            </div>

            <div
              ref={hueRef}
              className="accent-hue"
              onPointerDown={startHueDrag}
            >
              <span
                className="accent-hue__handle"
                style={{ left: `clamp(10px, ${(currentHsl.h / 360) * 100}%, calc(100% - 10px))` }}
              />
            </div>

            <label className="accent-hex">
              <span className="sr-only">Accent hex color</span>
              <input
                ref={hexInputRef}
                type="text"
                inputMode="text"
                autoComplete="off"
                spellCheck={false}
                value={draftHex}
                aria-label="Accent hex color"
                onChange={(event) => setDraftHex(event.currentTarget.value.toUpperCase())}
                onKeyDown={(event) => {
                  if (event.key !== "Enter") {
                    return;
                  }
                  event.preventDefault();
                  const nextValue = normalizeHexColor(draftHex);
                  if (nextValue) {
                    applyPreview(nextValue, true);
                    event.currentTarget.blur();
                  }
                }}
                onBlur={() => {
                  const nextValue = normalizeHexColor(draftHex);
                  if (nextValue) {
                    applyPreview(nextValue, true);
                  } else {
                    setPreviewHex(normalizedValue);
                    setDraftHex(normalizedValue.toUpperCase());
                  }
                }}
              />
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function ShortcutCaptureList({
  rows,
  onActivate,
}: {
  rows: Array<{ id: string; title: string; value: string; active: boolean }>;
  onActivate: (fieldName: string) => void;
}) {
  return (
    <div className="shortcut-list" aria-label="Keyboard shortcuts">
      {rows.map((row) => (
        <button
          key={row.id}
          type="button"
          className={`shortcut-row${row.active ? " is-capturing" : ""}`}
          onClick={() => onActivate(row.id)}
        >
          <span className="shortcut-row__label">{row.title}</span>
          <span className="shortcut-row__value" translate="no">
            {row.active ? "PRESS SHORTCUT" : row.value}
          </span>
        </button>
      ))}
    </div>
  );
}

export function MicGateMeter({
  level,
  threshold,
  active,
  onPointerDown,
  onNudge,
}: {
  level: number;
  threshold: number;
  active: boolean;
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onNudge: (delta: number) => void;
}) {
  const vizRef = useRef<HTMLDivElement | null>(null);
  const [barCount, setBarCount] = useState(24);
  const normalizedLevel = Math.max(0, Math.min(1, level || 0));
  const normalizedThreshold = Math.max(0, Math.min(1, threshold || 0));

  useEffect(() => {
    const element = vizRef.current;
    if (!element || typeof ResizeObserver === "undefined") {
      return;
    }

    const updateBarCount = () => {
      const nextCount = clamp(
        Math.round((element.clientWidth - 56) / 26),
        18,
        56,
      );
      setBarCount(nextCount);
    };

    updateBarCount();
    const observer = new ResizeObserver(updateBarCount);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const bars = Array.from({ length: barCount }, (_, index) => {
    const progress = index / Math.max(1, barCount - 1);
    const baseWave = 0.12 + Math.abs(Math.sin(progress * 13 + normalizedLevel * 8)) * 0.18;
    const primaryPeak =
      Math.max(0, 1 - Math.abs(progress - 0.44) * 3.2) * normalizedLevel * 0.82;
    const secondaryPeak =
      Math.max(0, 1 - Math.abs(progress - 0.72) * 6.1) * normalizedLevel * 0.24;
    const idleWave = active ? baseWave : baseWave * 0.55;
    const height = Math.min(1, idleWave + primaryPeak + secondaryPeak);
    return {
      key: `bar-${index}`,
      height,
      live: active && height >= normalizedThreshold,
    };
  });

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowUp" || event.key === "ArrowRight") {
      event.preventDefault();
      onNudge(0.01);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowLeft") {
      event.preventDefault();
      onNudge(-0.01);
    }
  };

  return (
    <div className="mic-gate">
      <div
        ref={vizRef}
        className={`mic-gate__viz${active ? " is-active" : ""}`}
        data-scroll-host="false"
        role="slider"
        tabIndex={0}
        aria-label="Mic sensitivity threshold"
        aria-orientation="vertical"
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuenow={Number(normalizedThreshold.toFixed(3))}
        aria-valuetext={`Trigger ${normalizedThreshold.toFixed(3)}`}
        title={`Trigger ${normalizedThreshold.toFixed(3)}`}
        onPointerDown={onPointerDown}
        onKeyDown={handleKeyDown}
      >
        <div
          className="mic-gate__threshold"
          style={{ bottom: `${normalizedThreshold * 100}%` }}
        />

        <div className="mic-gate__bars" aria-label="Live microphone level meter">
          {bars.map((bar) => (
            <span
              key={bar.key}
              className={`mic-gate__bar${bar.live ? " is-live" : ""}`}
              style={{ height: `${Math.max(12, bar.height * 100)}%` }}
            />
          ))}
        </div>
      </div>

      <div className="mic-gate__footer">
        <span>More Sensitive</span>
        <span className="mic-gate__metric">
          Level {normalizedLevel.toFixed(3)} / Trigger {normalizedThreshold.toFixed(3)}
        </span>
        <span>More Selective</span>
      </div>
    </div>
  );
}
