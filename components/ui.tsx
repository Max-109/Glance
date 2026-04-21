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

type ActivityMarkState =
  | "idle"
  | "listening"
  | "processing"
  | "speaking"
  | "ready"
  | "error";

const ACTIVITY_MARK_SEGMENTS = [
  { key: "west", x: 4, y: 11, width: 5, height: 14 },
  { key: "north", x: 11, y: 4, width: 14, height: 5 },
  { key: "east", x: 27, y: 11, width: 5, height: 14 },
  { key: "south", x: 11, y: 27, width: 14, height: 5 },
] as const;

const ACTIVITY_MARK_ANIMATION_INTERVAL_MS: Partial<
  Record<ActivityMarkState, number>
> = {
  listening: 420,
  processing: 560,
  speaking: 420,
  ready: 420,
};

const ACTIVITY_MARK_READY_FLASH_MS = 520;
const ACTIVITY_MARK_ERROR_FLASH_MS = 1400;
const ACTIVITY_MARK_ERROR_TOKENS = ["failed", "unavailable", "error"];

function normalizeActivityMarkState(state: string): ActivityMarkState {
  if (
    state === "listening" ||
    state === "processing" ||
    state === "speaking" ||
    state === "ready" ||
    state === "error"
  ) {
    return state;
  }
  return "idle";
}

function messageNeedsErrorFlash(message?: string) {
  const normalizedMessage = message?.trim().toLowerCase() || "";
  return ACTIVITY_MARK_ERROR_TOKENS.some((token) => normalizedMessage.includes(token));
}

function getActivityMarkSegmentOpacities(
  state: ActivityMarkState,
  frame: number,
): [number, number, number, number] {
  const pulseOpacity = frame ? 1 : 0.38;
  const completedOpacity = 0.9;
  const idleOpacity = 0.56;
  const inactiveOpacity = 0.24;

  if (state === "listening") {
    return [pulseOpacity, inactiveOpacity, inactiveOpacity, inactiveOpacity];
  }
  if (state === "processing") {
    return [completedOpacity, pulseOpacity, inactiveOpacity, inactiveOpacity];
  }
  if (state === "speaking") {
    return [completedOpacity, completedOpacity, pulseOpacity, inactiveOpacity];
  }
  if (state === "ready") {
    return [completedOpacity, completedOpacity, completedOpacity, pulseOpacity];
  }
  if (state === "error") {
    return [1, 1, 1, 1];
  }
  return [idleOpacity, idleOpacity, idleOpacity, idleOpacity];
}

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
  message,
  size = "compact",
  label,
}: {
  state: string;
  message?: string;
  size?: "compact" | "large";
  label?: string;
}) {
  const normalizedState = normalizeActivityMarkState(state);
  const [overrideState, setOverrideState] = useState<ActivityMarkState | null>(null);
  const [frame, setFrame] = useState(0);
  const previousStateRef = useRef<ActivityMarkState>(normalizedState);
  const previousErrorFlashRef = useRef(messageNeedsErrorFlash(message));
  const readyTimerRef = useRef<number | null>(null);
  const errorTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (readyTimerRef.current !== null) {
        window.clearTimeout(readyTimerRef.current);
      }
      if (errorTimerRef.current !== null) {
        window.clearTimeout(errorTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const previousState = previousStateRef.current;
    previousStateRef.current = normalizedState;

    if (normalizedState !== "listening" && readyTimerRef.current !== null) {
      window.clearTimeout(readyTimerRef.current);
      readyTimerRef.current = null;
      setOverrideState((current) => (current === "ready" ? null : current));
    }

    if (previousState === "speaking" && normalizedState === "listening") {
      if (readyTimerRef.current !== null) {
        window.clearTimeout(readyTimerRef.current);
      }
      setOverrideState("ready");
      readyTimerRef.current = window.setTimeout(() => {
        readyTimerRef.current = null;
        setOverrideState((current) => (current === "ready" ? null : current));
      }, ACTIVITY_MARK_READY_FLASH_MS);
    }
  }, [normalizedState]);

  const shouldFlashError = messageNeedsErrorFlash(message);

  useEffect(() => {
    const wasFlashingError = previousErrorFlashRef.current;
    previousErrorFlashRef.current = shouldFlashError;

    if (!shouldFlashError || wasFlashingError) {
      return;
    }

    if (readyTimerRef.current !== null) {
      window.clearTimeout(readyTimerRef.current);
      readyTimerRef.current = null;
    }
    if (errorTimerRef.current !== null) {
      window.clearTimeout(errorTimerRef.current);
    }

    setOverrideState("error");
    errorTimerRef.current = window.setTimeout(() => {
      errorTimerRef.current = null;
      setOverrideState((current) => (current === "error" ? null : current));
    }, ACTIVITY_MARK_ERROR_FLASH_MS);
  }, [shouldFlashError]);

  const effectiveState = overrideState ?? normalizedState;
  const segmentOpacities = getActivityMarkSegmentOpacities(effectiveState, frame);

  useEffect(() => {
    setFrame(0);
    const interval = ACTIVITY_MARK_ANIMATION_INTERVAL_MS[effectiveState];
    if (!interval) {
      return;
    }

    const timer = window.setInterval(() => {
      setFrame((current) => 1 - current);
    }, interval);

    return () => window.clearInterval(timer);
  }, [effectiveState]);

  return (
    <div
      className={`activity-mark activity-mark--${size}`}
      data-state={effectiveState}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <svg
        className="activity-mark__svg"
        viewBox="0 0 36 36"
        shapeRendering="geometricPrecision"
        aria-hidden="true"
      >
        {ACTIVITY_MARK_SEGMENTS.map((segment, index) => (
          <rect
            key={segment.key}
            className={`activity-mark__segment activity-mark__segment--${segment.key}`}
            x={segment.x}
            y={segment.y}
            width={segment.width}
            height={segment.height}
            opacity={segmentOpacities[index]}
          />
        ))}
      </svg>
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
          message={state.runtimeMessage}
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

const MIC_GATE_HISTORY_SECONDS = 6;
const MIC_GATE_SAMPLE_HZ = 30;
const MIC_GATE_HISTORY_LENGTH = MIC_GATE_HISTORY_SECONDS * MIC_GATE_SAMPLE_HZ;
const MIC_GATE_PEAK_DECAY = 0.94;

type MicGateStatus = "idle" | "quiet" | "speech" | "noisy";

function percentile(values: number[], p: number) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.max(
    0,
    Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p)),
  );
  return sorted[idx];
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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const historyRef = useRef<Float32Array>(
    new Float32Array(MIC_GATE_HISTORY_LENGTH),
  );
  const peakRef = useRef<Float32Array>(
    new Float32Array(MIC_GATE_HISTORY_LENGTH),
  );
  const headRef = useRef(0);
  const latestLevelRef = useRef(0);
  const thresholdRef = useRef(0);
  const activeRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const lastSampleRef = useRef(0);
  const aboveSinceRef = useRef<number | null>(null);

  const [noiseFloor, setNoiseFloor] = useState(0);
  const [status, setStatus] = useState<MicGateStatus>("idle");

  const normalizedLevel = Math.max(0, Math.min(1, level || 0));
  const normalizedThreshold = Math.max(0, Math.min(1, threshold || 0));

  latestLevelRef.current = normalizedLevel;
  thresholdRef.current = normalizedThreshold;
  activeRef.current = active;

  // Read accent from CSS custom props
  const readColors = () => {
    if (typeof window === "undefined") {
      return {
        accent: "#a7ffde",
        accentStrong: "#d3fff0",
        accentGlow: "rgba(167, 255, 222, 0.38)",
        muted: "rgba(255, 255, 255, 0.18)",
        mutedSoft: "rgba(255, 255, 255, 0.09)",
        threshold: "#a7ffde",
      };
    }
    const styles = getComputedStyle(document.documentElement);
    return {
      accent: styles.getPropertyValue("--accent").trim() || "#a7ffde",
      accentStrong:
        styles.getPropertyValue("--accent-strong").trim() || "#d3fff0",
      accentGlow:
        styles.getPropertyValue("--accent-glow").trim() ||
        "rgba(167, 255, 222, 0.38)",
      muted: "rgba(255, 255, 255, 0.22)",
      mutedSoft: "rgba(255, 255, 255, 0.08)",
      threshold: styles.getPropertyValue("--accent").trim() || "#a7ffde",
    };
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    const host = vizRef.current;
    if (!canvas || !host) return;

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const rect = host.getBoundingClientRect();
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    const observer =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(resize)
        : null;
    observer?.observe(host);

    const sampleInterval = 1000 / MIC_GATE_SAMPLE_HZ;

    const pushSample = (value: number) => {
      const history = historyRef.current;
      const peak = peakRef.current;
      const idx = headRef.current;
      history[idx] = value;
      const prevPeakIdx =
        (idx - 1 + MIC_GATE_HISTORY_LENGTH) % MIC_GATE_HISTORY_LENGTH;
      const prevPeak = peak[prevPeakIdx] * MIC_GATE_PEAK_DECAY;
      peak[idx] = Math.max(value, prevPeak);
      headRef.current = (idx + 1) % MIC_GATE_HISTORY_LENGTH;
    };

    const draw = () => {
      const width = host.clientWidth;
      const height = host.clientHeight;
      if (width <= 0 || height <= 0) return;

      const colors = readColors();
      const history = historyRef.current;
      const peak = peakRef.current;
      const head = headRef.current;
      const thr = thresholdRef.current;

      ctx.clearRect(0, 0, width, height);

      // Background grid marks at 25/50/75%
      ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
      ctx.lineWidth = 1;
      for (const p of [0.25, 0.5, 0.75]) {
        const y = Math.round((1 - p) * height) + 0.5;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Threshold line (drawn under bars so peaks can glow over it)
      const thrY = Math.round((1 - thr) * height) + 0.5;
      ctx.strokeStyle = colors.threshold;
      ctx.shadowColor = colors.accentGlow;
      ctx.shadowBlur = 14;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, thrY);
      ctx.lineTo(width, thrY);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Dashed segment above threshold (showing headroom zone)
      ctx.save();
      ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
      ctx.setLineDash([3, 4]);
      ctx.beginPath();
      ctx.moveTo(0, Math.round(height * 0.05) + 0.5);
      ctx.lineTo(width, Math.round(height * 0.05) + 0.5);
      ctx.stroke();
      ctx.restore();

      // Bars: oldest on the left, newest on the right.
      const barWidth = 2;
      const gap = 1;
      const step = barWidth + gap;
      const visibleCount = Math.min(
        MIC_GATE_HISTORY_LENGTH,
        Math.floor(width / step),
      );
      const startReadIdx =
        (head - visibleCount + MIC_GATE_HISTORY_LENGTH) %
        MIC_GATE_HISTORY_LENGTH;

      // Collect visible peaks as we draw so we can render the peak-hold polyline after.
      const peakPoints: Array<[number, number]> = [];

      for (let i = 0; i < visibleCount; i++) {
        const srcIdx = (startReadIdx + i) % MIC_GATE_HISTORY_LENGTH;
        const v = history[srcIdx];
        const p = peak[srcIdx];
        // Anchor to the right edge so newest samples hug the "now" line
        const x = width - (visibleCount - i) * step;
        const barH = Math.max(1, v * height);
        const y = height - barH;

        const above = v >= thr && thr > 0;
        ctx.fillStyle = above ? colors.accent : colors.muted;
        ctx.globalAlpha = above ? 0.95 : 0.55;
        ctx.fillRect(x, y, barWidth, barH);

        // Soft glow pass for above-threshold
        if (above) {
          ctx.globalCompositeOperation = "lighter";
          ctx.globalAlpha = 0.18;
          ctx.fillStyle = colors.accentStrong;
          ctx.fillRect(x - 1, y - 1, barWidth + 2, barH + 2);
          ctx.globalCompositeOperation = "source-over";
        }
        ctx.globalAlpha = 1;

        peakPoints.push([x + barWidth / 2, height - Math.max(1, p * height)]);
      }

      // Peak-hold polyline
      if (peakPoints.length > 1) {
        ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(peakPoints[0][0], peakPoints[0][1]);
        for (let i = 1; i < peakPoints.length; i++) {
          ctx.lineTo(peakPoints[i][0], peakPoints[i][1]);
        }
        ctx.stroke();
      }

      // "Now" indicator on right edge
      ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(width - 0.5, 0);
      ctx.lineTo(width - 0.5, height);
      ctx.stroke();
    };

    const tick = (now: number) => {
      if (!lastSampleRef.current) lastSampleRef.current = now;
      while (now - lastSampleRef.current >= sampleInterval) {
        pushSample(
          activeRef.current ? latestLevelRef.current : 0,
        );
        lastSampleRef.current += sampleInterval;
      }
      draw();

      // Noise floor + status compute every ~200ms
      if ((now | 0) % 6 === 0) {
        const arr = Array.from(historyRef.current);
        const nf = percentile(arr, 0.1);
        setNoiseFloor(nf);
        const thr = thresholdRef.current;
        const lvl = latestLevelRef.current;
        let next: MicGateStatus = "idle";
        if (!activeRef.current) {
          next = "idle";
          aboveSinceRef.current = null;
        } else if (nf > thr) {
          next = "noisy";
        } else if (lvl >= thr) {
          if (aboveSinceRef.current == null) aboveSinceRef.current = now;
          if (now - aboveSinceRef.current > 100) next = "speech";
          else next = "quiet";
        } else {
          aboveSinceRef.current = null;
          next = "quiet";
        }
        setStatus((prev) => (prev === next ? prev : next));
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    if (prefersReducedMotion) {
      // Static draw only; still update on re-render via effect deps
      draw();
    } else {
      rafRef.current = requestAnimationFrame(tick);
    }

    return () => {
      observer?.disconnect();
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastSampleRef.current = 0;
    };
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    let delta = 0;
    const step = event.shiftKey ? 0.05 : 0.01;
    if (event.key === "ArrowUp" || event.key === "ArrowRight") delta = step;
    else if (event.key === "ArrowDown" || event.key === "ArrowLeft")
      delta = -step;
    else if (event.key === "PageUp") delta = 0.1;
    else if (event.key === "PageDown") delta = -0.1;
    else if (event.key === "Home") {
      event.preventDefault();
      onNudge(-1);
      return;
    } else if (event.key === "End") {
      event.preventDefault();
      onNudge(1);
      return;
    }
    if (delta !== 0) {
      event.preventDefault();
      onNudge(delta);
    }
  };

  const thresholdPct = Math.round(normalizedThreshold * 100);
  const levelPct = Math.round(normalizedLevel * 100);
  const noisePct = Math.round(noiseFloor * 100);

  const statusLabel =
    status === "speech"
      ? "Speech detected"
      : status === "noisy"
        ? "Noise crossing line — raise threshold"
        : status === "quiet"
          ? "Quiet"
          : "Mic test off";

  // Sparkline segments for level chip
  const sparkSegments = 8;
  const filledSegments = Math.round(
    Math.max(0, Math.min(1, normalizedLevel)) * sparkSegments,
  );

  return (
    <div className="mic-gate">
      <div className={`mic-gate__status mic-gate__status--${status}`}>
        <span className="mic-gate__status-dot" aria-hidden="true" />
        <span>{statusLabel}</span>
      </div>

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
        aria-valuetext={`Threshold ${thresholdPct}%`}
        title={`Threshold ${thresholdPct}% · drag to adjust`}
        onPointerDown={onPointerDown}
        onKeyDown={handleKeyDown}
      >
        <canvas ref={canvasRef} className="mic-gate__canvas" aria-hidden="true" />

        <div
          className="mic-gate__handle"
          style={{ bottom: `${normalizedThreshold * 100}%` }}
          aria-hidden="true"
        >
          <span className="mic-gate__handle-grip" />
          <span className="mic-gate__handle-value">{thresholdPct}%</span>
        </div>

        <div className="mic-gate__now-label" aria-hidden="true">
          now
        </div>
        <div className="mic-gate__past-label" aria-hidden="true">
          −{MIC_GATE_HISTORY_SECONDS}s
        </div>
      </div>

      <div className="mic-gate__chips">
        <div className="mic-gate__chip">
          <span className="mic-gate__chip-label">Noise floor</span>
          <span className="mic-gate__chip-value">{noisePct}%</span>
        </div>
        <div className="mic-gate__chip mic-gate__chip--level">
          <span className="mic-gate__chip-label">Live level</span>
          <span className="mic-gate__chip-value">
            {levelPct}%
            <span className="mic-gate__spark" aria-hidden="true">
              {Array.from({ length: sparkSegments }).map((_, i) => (
                <span
                  key={i}
                  className={`mic-gate__spark-seg${
                    i < filledSegments ? " is-on" : ""
                  }${
                    i < filledSegments &&
                    i / sparkSegments >= normalizedThreshold
                      ? " is-hot"
                      : ""
                  }`}
                />
              ))}
            </span>
          </span>
        </div>
        <div className="mic-gate__chip mic-gate__chip--threshold">
          <span className="mic-gate__chip-label">Threshold</span>
          <span className="mic-gate__chip-controls">
            <button
              type="button"
              className="mic-gate__chip-btn"
              aria-label="Lower threshold by 1%"
              onClick={() => onNudge(-0.01)}
            >
              −
            </button>
            <span className="mic-gate__chip-value mic-gate__chip-value--lg">
              {thresholdPct}%
            </span>
            <button
              type="button"
              className="mic-gate__chip-btn"
              aria-label="Raise threshold by 1%"
              onClick={() => onNudge(0.01)}
            >
              +
            </button>
          </span>
        </div>
      </div>
    </div>
  );
}
