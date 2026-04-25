export function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function normalizeHexColor(value: string, fallback = "") {
  const normalizedValue = value.trim().toLowerCase();
  if (!normalizedValue) {
    return fallback;
  }

  const withHash = normalizedValue.startsWith("#")
    ? normalizedValue
    : `#${normalizedValue}`;

  if (/^#[0-9a-f]{6}$/.test(withHash)) {
    return withHash;
  }

  return fallback;
}

export function hexToRgb(hex: string, fallback = "") {
  const normalizedHex = normalizeHexColor(hex, fallback);
  if (!normalizedHex) {
    return { r: 0, g: 0, b: 0 };
  }

  const color = normalizedHex.slice(1);
  return {
    r: Number.parseInt(color.slice(0, 2), 16),
    g: Number.parseInt(color.slice(2, 4), 16),
    b: Number.parseInt(color.slice(4, 6), 16),
  };
}

function rgbToHex({ r, g, b }: { r: number; g: number; b: number }) {
  return `#${[r, g, b]
    .map((channel) => clamp(Math.round(channel), 0, 255).toString(16).padStart(2, "0"))
    .join("")}`;
}

export function rgbToHsl({ r, g, b }: { r: number; g: number; b: number }) {
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

export function hslToHex(h: number, s: number, l: number) {
  return rgbToHex(hslToRgb(h, s, l));
}

export function toRgba(hex: string, alpha: number, fallback = "") {
  const { r, g, b } = hexToRgb(hex, fallback);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function relativeLuminance({ r, g, b }: { r: number; g: number; b: number }) {
  const transform = (channel: number) => {
    const value = channel / 255;
    return value <= 0.03928
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4;
  };

  return (
    0.2126 * transform(r) +
    0.7152 * transform(g) +
    0.0722 * transform(b)
  );
}
