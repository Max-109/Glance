import type { SVGProps } from "react";

const ICON_PATHS: Record<string, string> = {
  capture:
    "M4 8.5A4.5 4.5 0 0 1 8.5 4h2.25 M15.5 4h.5A4.5 4.5 0 0 1 20 8.5v2.25 M20 15.5A4.5 4.5 0 0 1 15.5 20h-2.25 M8.5 20A4.5 4.5 0 0 1 4 15.5v-2.25 M12 8.8a3.2 3.2 0 1 0 0 6.4a3.2 3.2 0 0 0 0-6.4Z",
  audio: "M4 12h2.5 M17.5 12H20 M8 8v8 M12 5v14 M16 7v10",
  api: "M10 7H7a3 3 0 0 0 0 6h3 M14 7h3a3 3 0 1 1 0 6h-3 M8.5 12h7",
  plug: "M9 7V4 M15 7V4 M8 7h8v4a4 4 0 0 1-8 0Z M12 15v5",
  speech:
    "M9 18v-6a3 3 0 1 1 6 0v6 M7 11a5 5 0 0 0 10 0 M12 18v3 M9 21h6",
  speaker:
    "M11 5 7 9H4v6h3l4 4V5Z M16 9.5a3.5 3.5 0 0 1 0 5 M18.5 7a7 7 0 0 1 0 10",
  settings:
    "M12 3v3 M12 18v3 M3 12h3 M18 12h3 M12 8.8a3.2 3.2 0 1 0 0 6.4a3.2 3.2 0 0 0 0-6.4Z",
  sliders:
    "M4 6h6 M14 6h6 M11 4v4 M4 12h10 M18 12h2 M16 10v4 M4 18h2 M10 18h10 M8 16v4",
  history: "M4 12a8 8 0 1 0 2.3-5.65 M4 4v4h4 M12 8v5l3 2",
  clock: "M12 4a8 8 0 1 0 0 16a8 8 0 0 0 0-16Z M12 8v4l2.5 1.5",
  timer: "M9 2h6 M12 13V8 M12 22a8 8 0 1 0 0-16a8 8 0 0 0 0 16Z",
  gauge: "M5 15a7 7 0 0 1 14 0 M12 12l3-3",
  key: "M8.5 9a2.5 2.5 0 1 0 0 5a2.5 2.5 0 0 0 0-5Z M11 11.5h8 M16 11.5V14 M18.5 11.5V13",
  bot: "M9 6h6 M12 3v3 M5 10a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v5a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3Z M8.5 11h.01 M15.5 11h.01 M9 15h6",
  mic: "M12 16a4 4 0 0 0 4-4V8a4 4 0 1 0-8 0v4a4 4 0 0 0 4 4Z M7 12a5 5 0 0 0 10 0 M12 17v4",
  headphones:
    "M5 13v-1a7 7 0 0 1 14 0v1 M4.5 12.5h3v6h-3Z M16.5 12.5h3v6h-3Z",
  play: "M8 6v12l9-6-9-6Z",
  refresh:
    "M4 11a8 8 0 0 1 13.6-5.6L20 8 M20 4.5V8h-3.5 M20 13a8 8 0 0 1-13.6 5.6L4 16 M4 19.5V16h3.5",
  trash:
    "M5 7h14 M9 7V5h6v2 M7 7h10v12H7Z M10 10v6 M14 10v6",
  languages:
    "M5 7h7 M8.5 7c0 5-2 8-4.5 10 M6 13h5 M15 7h4 M17 7c0 4 1.5 7 3 9 M14.5 13h5",
  moon: "M15 4a7 7 0 1 0 5 12.2A8.5 8.5 0 0 1 15 4Z",
  monitor: "M4 5h16v10H4Z M9 19h6 M12 15v4",
  quote:
    "M8.5 10.5h-2a2 2 0 0 0-2 2v3h4v-5Z M17.5 10.5h-2a2 2 0 0 0-2 2v3h4v-5Z",
  info: "M12 12v4 M12 8h.01 M12 22a10 10 0 1 0 0-20a10 10 0 0 0 0 20Z",
  "alert-circle":
    "M12 8v5 M12 16h.01 M12 22a10 10 0 1 0 0-20a10 10 0 0 0 0 20Z",
  close: "M6 6l12 12 M18 6 6 18",
  stop: "M9 7h6a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z",
  check: "M5 12.5 9.2 17 19 7.5",
  wave: "M5 12h1.5 M8 8v8 M11 5v14 M14 7v10 M17 9v6",
  brain:
    "M9 6.5A3.5 3.5 0 1 1 15 9v7a3 3 0 0 1-6 0V8.5A2.5 2.5 0 0 1 11.5 6 M15 11a2.5 2.5 0 1 1 0 5",
  "brain-circuit":
    "M8.5 7.5A3.5 3.5 0 1 1 15 9v6.5a2.5 2.5 0 0 1-5 0V8.4A2.4 2.4 0 0 1 12.4 6 M15.5 12.5h2 M17.5 10.5v4 M8.5 13.5H6.5 M6.5 11.5v4 M12 18v3",
  zap: "M13 3 5 13h5l-1 8 8-10h-5l1-8Z",
  undo: "M3 12a9 9 0 1 0 3-6.7 M3 5v5h5",
  rewind: "M7 7v10 M18 8l-7 4 7 4V8Z",
  sun: "M12 8.8a3.2 3.2 0 1 0 0 6.4a3.2 3.2 0 0 0 0-6.4Z M12 2.5v2.2 M12 19.3v2.2 M2.5 12h2.2 M19.3 12h2.2 M5.4 5.4l1.6 1.6 M17 17l1.6 1.6 M17 7l1.6-1.6 M5.4 18.6l1.6-1.6",
  eye: "M2.5 12s3.5-6 9.5-6s9.5 6 9.5 6s-3.5 6-9.5 6S2.5 12 2.5 12Z M12 9.2a2.8 2.8 0 1 0 0 5.6a2.8 2.8 0 0 0 0-5.6Z",
  chevron: "M7 10l5 5 5-5",
  plus: "M12 5v14 M5 12h14",
  minus: "M5 12h14",
  "level-1": "M9 15h2v4H9Z",
  "level-2": "M7 15h2v4H7Z M13 11h2v8h-2Z",
  "level-3": "M6 15h2v4H6Z M11 11h2v8h-2Z M16 7h2v12h-2Z",
  "level-4": "M5 15h2v4H5Z M9 12h2v7H9Z M13 9h2v10h-2Z M17 6h2v13h-2Z",
};

export function Icon({
  name,
  className,
  ...props
}: SVGProps<SVGSVGElement> & { name: string }) {
  const path = ICON_PATHS[name] || ICON_PATHS.settings;
  const segments = path.split(" M").map((segment, index) => {
    const d = index === 0 ? segment : `M${segment}`;
    return <path key={`${name}-${index}`} d={d} />;
  });

  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      {segments}
    </svg>
  );
}
