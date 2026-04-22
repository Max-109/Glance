import type { SVGProps } from "react";
import {
  ApiIcon,
  AlertCircleIcon,
  ArrowDown01Icon,
  ArrowTurnBackwardIcon,
  AudioWave01Icon,
  Backward02Icon,
  Brain01Icon,
  Brain02Icon,
  BotIcon,
  BubbleChatIcon,
  Camera01Icon,
  Cancel01Icon,
  Clock01Icon,
  ComputerIcon,
  DashboardSpeed01Icon,
  Delete02Icon,
  EyeIcon,
  ViewOffSlashIcon,
  FlashIcon,
  HeadphonesIcon,
  InformationCircleIcon,
  Mic01Icon,
  MinusSignIcon,
  Moon02Icon,
  PlayIcon,
  PlugSocketIcon,
  PlusSignIcon,
  QuoteUpIcon,
  RefreshIcon,
  Settings02Icon,
  SignalFull02Icon,
  SignalLow02Icon,
  SignalMedium02Icon,
  SignalNo02Icon,
  SlidersHorizontalIcon,
  SquareLock01Icon,
  StopIcon,
  Sun03Icon,
  Tick02Icon,
  TimeQuarter02Icon,
  Timer02Icon,
  TranslateIcon,
  VolumeHighIcon,
  WaveIcon,
} from "hugeicons-react";
import type { ComponentType } from "react";

type HugeIconProps = {
  size?: number | string;
  color?: string;
  strokeWidth?: number;
  className?: string;
  [key: string]: unknown;
};

const ICONS: Record<string, ComponentType<HugeIconProps>> = {
  capture: Camera01Icon,
  audio: AudioWave01Icon,
  api: ApiIcon,
  plug: PlugSocketIcon,
  speech: Mic01Icon,
  speaker: VolumeHighIcon,
  settings: Settings02Icon,
  sliders: SlidersHorizontalIcon,
  history: TimeQuarter02Icon,
  clock: Clock01Icon,
  timer: Timer02Icon,
  gauge: DashboardSpeed01Icon,
  key: SquareLock01Icon,
  bot: BotIcon,
  replies: BubbleChatIcon,
  model: Brain02Icon,
  mic: Mic01Icon,
  headphones: HeadphonesIcon,
  play: PlayIcon,
  refresh: RefreshIcon,
  trash: Delete02Icon,
  languages: TranslateIcon,
  moon: Moon02Icon,
  monitor: ComputerIcon,
  quote: QuoteUpIcon,
  info: InformationCircleIcon,
  "alert-circle": AlertCircleIcon,
  close: Cancel01Icon,
  stop: StopIcon,
  check: Tick02Icon,
  wave: WaveIcon,
  brain: Brain01Icon,
  "brain-circuit": Brain02Icon,
  zap: FlashIcon,
  undo: ArrowTurnBackwardIcon,
  rewind: Backward02Icon,
  sun: Sun03Icon,
  eye: EyeIcon,
  "eye-off": ViewOffSlashIcon,
  chevron: ArrowDown01Icon,
  plus: PlusSignIcon,
  minus: MinusSignIcon,
  "level-1": SignalNo02Icon,
  "level-2": SignalLow02Icon,
  "level-3": SignalMedium02Icon,
  "level-4": SignalFull02Icon,
};

export function Icon({
  name,
  className,
  strokeWidth,
  ...props
}: SVGProps<SVGSVGElement> & { name: string }) {
  const Component = ICONS[name] ?? ICONS.settings;
  const sw =
    typeof strokeWidth === "number"
      ? strokeWidth
      : typeof strokeWidth === "string"
        ? Number(strokeWidth) || 1.8
        : 1.8;

  // Hugeicons components accept size/color/strokeWidth props. We pass through
  // className so existing CSS (chips, sizes, colors via currentColor) keeps
  // working exactly as before.
  return (
    <Component
      className={className}
      strokeWidth={sw}
      color="currentColor"
      aria-hidden="true"
      {...(props as Record<string, unknown>)}
    />
  );
}
