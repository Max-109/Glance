import {
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  clamp,
  hexToRgb,
  hslToHex,
  normalizeHexColor,
  rgbToHsl,
} from "@/lib/color-utils";

function planeRatioFromLightness(lightness: number) {
  return clamp((84 - lightness) / 62, 0, 1);
}

function lightnessFromPlaneRatio(ratio: number) {
  return clamp(84 - ratio * 62, 22, 84);
}

export function ColorPicker({
  value,
  presets,
  onChange,
}: {
  value: string;
  presets: Array<{ label: string; value: string }>;
  onChange: (nextValue: string) => void;
}) {
  const normalizedValue = normalizeHexColor(value, "#a7ffde");
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
  }, [normalizedValue, presets]);

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

  const startHueDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
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
