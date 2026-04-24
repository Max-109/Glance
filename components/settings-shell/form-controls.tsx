import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Icon } from "@/components/icons";
import { cn } from "@/lib/utils";

function splitOptionLabel(label: string): { primary: string; secondary?: string } {
  const voiceParts = label.split(" - ");
  if (voiceParts.length === 2) {
    return { primary: voiceParts[0], secondary: voiceParts[1] };
  }
  const languageParts = label.split(" · ");
  if (languageParts.length === 2) {
    return { primary: languageParts[0], secondary: languageParts[1] };
  }
  return { primary: label };
}

export function FieldControl({
  fieldName,
  label,
  value,
  icon,
  helperText,
  errorText,
  inputMode,
  secret,
  revealed,
  onChange,
  onCommit,
  onFocus,
  onToggleReveal,
}: {
  fieldName: string;
  label: string;
  value: string;
  icon?: string;
  helperText?: string;
  errorText?: string;
  inputMode?: "text" | "decimal" | "numeric" | "search" | "url";
  secret?: boolean;
  revealed?: boolean;
  onChange: (value: string) => void;
  onCommit: (value: string) => void;
  onFocus?: () => void;
  onToggleReveal?: () => void;
}) {
  const inputType =
    secret && !revealed ? "password" : inputMode === "url" ? "url" : "text";
  const describedBy = errorText
    ? `${fieldName}-error`
    : helperText
      ? `${fieldName}-helper`
      : undefined;

  return (
    <label className="grid min-w-0 gap-2">
      <span className="text-sm font-semibold text-[color-mix(in_srgb,var(--text-base)_88%,white)]">
        {label}
      </span>
      <span
        className={cn(
          "relative flex h-12 min-w-0 items-center rounded-2xl border border-white/10 bg-black/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.025)] transition-colors focus-within:border-[color-mix(in_srgb,var(--accent)_48%,transparent)] focus-within:ring-4 focus-within:ring-[color-mix(in_srgb,var(--accent)_12%,transparent)]",
          errorText && "border-red-400/45",
        )}
      >
        {icon ? (
          <Icon
            name={icon}
            className="pointer-events-none absolute left-4 size-5 text-[var(--text-muted)]"
          />
        ) : null}
        <Input
          className={cn(
            "h-full min-w-0 flex-1 rounded-2xl border-0 bg-transparent px-4 text-[1.02rem] text-[var(--text-strong)] shadow-none outline-none ring-0 placeholder:text-[var(--text-faint)] focus-visible:ring-0",
            icon && "pl-12",
            secret && onToggleReveal && "pr-12",
          )}
          value={value}
          type={inputType}
          name={fieldName}
          inputMode={inputMode}
          autoComplete="off"
          spellCheck={false}
          aria-describedby={describedBy}
          aria-invalid={errorText ? true : undefined}
          onChange={(event) => onChange(event.currentTarget.value)}
          onBlur={(event) => onCommit(event.currentTarget.value)}
          onFocus={() => onFocus?.()}
          onKeyDown={(event) => {
            if (event.key === "Enter") event.currentTarget.blur();
          }}
        />
        {secret && onToggleReveal ? (
          <button
            type="button"
            className="absolute right-2 grid size-8 place-items-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-white/5 hover:text-[var(--text-strong)]"
            aria-label={revealed ? "Hide secret" : "Show secret"}
            aria-pressed={revealed}
            onClick={onToggleReveal}
          >
            <Icon name={revealed ? "eye-off" : "eye"} className="size-4" />
          </button>
        ) : null}
      </span>
      {errorText ? (
        <span id={`${fieldName}-error`} className="text-xs text-red-300">
          {errorText}
        </span>
      ) : helperText ? (
        <span id={`${fieldName}-helper`} className="text-xs text-[var(--text-muted)]">
          {helperText}
        </span>
      ) : null}
    </label>
  );
}

export function SelectControl({
  fieldName,
  label,
  value,
  options,
  labels,
  optionIcons = {},
  icon,
  accented,
  helperText,
  open,
  actionSlot,
  onToggle,
  onSelect,
}: {
  fieldName: string;
  label: string;
  value: string;
  options: string[];
  labels?: Record<string, string>;
  optionIcons?: Record<string, string>;
  icon?: string;
  accented?: boolean;
  helperText?: string;
  open: boolean;
  actionSlot?: ReactNode;
  onToggle: () => void;
  onSelect: (value: string) => void;
}) {
  const currentLabel = labels?.[value] || value || "Select";
  const currentDisplay = splitOptionLabel(currentLabel);
  const currentIcon = optionIcons[value] || icon;
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [mounted, setMounted] = useState(false);
  const [portalTarget, setPortalTarget] = useState<Element | null>(null);
  const [menuRect, setMenuRect] = useState({
    left: 0,
    top: 0,
    width: 0,
  });

  useEffect(() => {
    setMounted(true);
    setPortalTarget(rootRef.current?.closest(".glance-redesign") ?? document.body);
  }, []);

  useEffect(() => {
    if (!open) return;

    const updateMenuRect = () => {
      const rect = rootRef.current?.getBoundingClientRect();
      if (!rect) return;
      setMenuRect({
        left: rect.left,
        top: rect.bottom + 6,
        width: rect.width,
      });
    };

    updateMenuRect();
    window.addEventListener("resize", updateMenuRect);
    window.addEventListener("scroll", updateMenuRect, true);
    return () => {
      window.removeEventListener("resize", updateMenuRect);
      window.removeEventListener("scroll", updateMenuRect, true);
    };
  }, [open]);

  const menu = open ? (
    <div
      id={`${fieldName}-options`}
      className="fixed z-[100] max-h-64 overflow-y-auto rounded-2xl border border-white/10 bg-[#19191b] p-1.5 shadow-2xl"
      style={{
        left: menuRect.left,
        top: menuRect.top,
        width: menuRect.width,
      }}
      role="listbox"
      data-select-root="true"
    >
      {options.map((option) => {
        const selected = option === value;
        const optionIcon = optionIcons[option] || icon;
        const optionDisplay = splitOptionLabel(labels?.[option] || option);
        return (
          <button
            key={option}
            type="button"
            className={cn(
              "flex min-h-11 w-full items-center gap-2.5 rounded-xl px-2.5 py-1.5 text-left text-sm text-[var(--text-muted)] transition-colors hover:bg-white/[0.055] hover:text-[var(--text-strong)]",
              selected && "bg-white/[0.075] text-[var(--text-strong)]",
            )}
            role="option"
            aria-selected={selected}
            onClick={() => onSelect(option)}
          >
            {optionIcon ? (
              <span
                className={cn(
                  "grid size-8 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.035] text-[var(--text-muted)] transition-colors",
                  accented || selected
                    ? "border-[color-mix(in_srgb,var(--accent)_30%,transparent)] bg-[color-mix(in_srgb,var(--accent)_10%,transparent)] text-[var(--accent-strong)]"
                    : "",
                )}
                style={
                  accented || selected
                    ? { color: "var(--accent-strong)" }
                    : undefined
                }
              >
                <Icon name={optionIcon} className="size-4" />
              </span>
            ) : null}
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">
                {optionDisplay.primary}
              </span>
              {optionDisplay.secondary ? (
                <span className="mt-0.5 block truncate text-xs text-[var(--text-muted)]">
                  {optionDisplay.secondary}
                </span>
              ) : null}
            </span>
            {selected ? <Icon name="check" className="size-4 text-[var(--accent)]" /> : null}
          </button>
        );
      })}
    </div>
  ) : null;

  return (
    <div ref={rootRef} className="relative grid min-w-0 gap-2" data-select-root="true">
      <span className="text-sm font-semibold text-[color-mix(in_srgb,var(--text-base)_88%,white)]">
        {label}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="relative flex h-12 min-w-0 flex-1 items-center gap-3 rounded-2xl border border-white/10 bg-black/10 px-4 text-left text-[1.02rem] text-[var(--text-strong)] transition-colors hover:bg-white/[0.035] focus-visible:border-[color-mix(in_srgb,var(--accent)_48%,transparent)] focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_12%,transparent)]"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={open ? `${fieldName}-options` : undefined}
          onClick={onToggle}
        >
          {currentIcon ? (
            <Icon
              name={currentIcon}
              className={cn(
                "size-5 text-[var(--text-muted)]",
                accented && "text-[var(--accent-strong)]",
              )}
              style={accented ? { color: "var(--accent-strong)" } : undefined}
            />
          ) : null}
          <span className="min-w-0 flex-1">
            <span className="block truncate">{currentDisplay.primary}</span>
            {currentDisplay.secondary ? (
              <span className="mt-0.5 block truncate text-xs text-[var(--text-muted)]">
                {currentDisplay.secondary}
              </span>
            ) : null}
          </span>
          <Icon name="chevron" className="size-5 text-[var(--text-muted)]" />
        </button>
        {actionSlot}
      </div>
      {helperText ? <span className="text-xs text-[var(--text-muted)]">{helperText}</span> : null}
      {mounted && menu ? createPortal(menu, portalTarget ?? document.body) : null}
    </div>
  );
}

export function ToggleCard({
  label,
  helperText,
  icon,
  checked,
  onChange,
}: {
  label: string;
  helperText: string;
  icon?: string;
  checked: boolean;
  onChange: (nextValue: boolean) => void;
}) {
  return (
    <div
      role="group"
      className={cn(
        "flex min-h-20 w-full items-center gap-4 rounded-2xl border bg-card px-5 py-4 text-left transition-[background-color,border-color,box-shadow]",
        checked
          ? "border-[color-mix(in_srgb,var(--accent)_42%,rgba(255,255,255,0.1))] shadow-[0_0_0_1px_color-mix(in_srgb,var(--accent)_10%,transparent)]"
          : "border-white/10 hover:bg-white/[0.035]",
      )}
    >
      {icon ? (
        <span
          className={cn(
            "grid size-10 shrink-0 place-items-center rounded-2xl border border-white/10 bg-white/[0.045] text-[var(--text-muted)] transition-colors",
            checked &&
              "border-[color-mix(in_srgb,var(--accent)_46%,transparent)] bg-[color-mix(in_srgb,var(--accent)_16%,transparent)] text-[var(--accent-strong)]",
          )}
        >
          <Icon name={icon} className="size-5" />
        </span>
      ) : null}
      <span className="min-w-0 flex-1">
        <span className="block text-base font-semibold text-[var(--text-strong)]">
          {label}
        </span>
        <span className="mt-1 block text-sm text-[var(--text-muted)]">{helperText}</span>
      </span>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={label} />
    </div>
  );
}

function formatStepValue(nextValue: number, step: number) {
  const precision = `${step}`.includes(".")
    ? `${step}`.split(".")[1]?.length ?? 0
    : 0;
  return nextValue.toFixed(precision).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

export function NumberField({
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
  const [flash, setFlash] = useState(false);
  const previousValue = useRef(value);
  const flashTimer = useRef<number | null>(null);

  useEffect(() => {
    if (previousValue.current !== value) {
      previousValue.current = value;
      setFlash(true);
      if (flashTimer.current) window.clearTimeout(flashTimer.current);
      flashTimer.current = window.setTimeout(() => setFlash(false), 260);
    }
    return () => {
      if (flashTimer.current) window.clearTimeout(flashTimer.current);
    };
  }, [value]);

  const adjustValue = (direction: -1 | 1) => {
    const parsedValue = Number.parseFloat(value);
    const baseValue = Number.isFinite(parsedValue)
      ? parsedValue
      : typeof min === "number"
        ? min
        : 0;
    let nextValue = baseValue + direction * step;
    if (typeof min === "number") nextValue = Math.max(min, nextValue);
    if (typeof max === "number") nextValue = Math.min(max, nextValue);
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
    <label className="grid min-w-0 gap-2">
      <span className="text-sm font-semibold text-[color-mix(in_srgb,var(--text-base)_88%,white)]">
        {label}
      </span>
      <span
        className={cn(
          "relative flex h-12 min-w-0 items-center rounded-2xl border border-white/10 bg-card transition-[border-color,box-shadow,background-color] focus-within:border-[color-mix(in_srgb,var(--accent)_48%,transparent)] focus-within:ring-4 focus-within:ring-[color-mix(in_srgb,var(--accent)_12%,transparent)]",
          errorText && "border-red-400/45",
          flash && "border-[color-mix(in_srgb,var(--accent)_44%,transparent)]",
        )}
      >
        {icon ? (
          <Icon
            name={icon}
            className="pointer-events-none absolute left-4 size-5 text-[var(--text-muted)]"
          />
        ) : null}
        <Input
          className={cn(
            "h-full min-w-0 flex-1 rounded-2xl border-0 bg-transparent px-4 text-[1.02rem] text-[var(--text-strong)] shadow-none outline-none ring-0 placeholder:text-[var(--text-faint)] focus-visible:ring-0",
            icon && "pl-12",
            suffix && "pr-10",
          )}
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
        {suffix ? (
          <span className="absolute right-20 text-sm font-medium text-[var(--text-muted)]">
            {suffix}
          </span>
        ) : null}
        <span className="absolute right-2 flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            className="rounded-xl"
            aria-label={`Decrease ${label}`}
            onClick={() => adjustValue(-1)}
          >
            <Icon name="minus" className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            className="rounded-xl"
            aria-label={`Increase ${label}`}
            onClick={() => adjustValue(1)}
          >
            <Icon name="plus" className="size-3.5" />
          </Button>
        </span>
      </span>
      {errorText ? (
        <span id={`${fieldName}-error`} className="text-xs text-red-300">
          {errorText}
        </span>
      ) : helperText ? (
        <span id={`${fieldName}-helper`} className="text-xs text-[var(--text-muted)]">
          {helperText}
        </span>
      ) : null}
    </label>
  );
}
