from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import re
from pathlib import Path

from src.models.settings import DEFAULT_ACCENT_COLOR, normalize_hex_color


_CONSOLE_HANDLER_NAME = "glance-console"
_FILE_HANDLER_NAME = "glance-file"
_ANSI_RESET = "\033[0m"
_TIMING_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|s)\b")


@dataclass(frozen=True)
class _ConsolePalette:
    timestamp: str
    info: str
    debug: str
    warning: str
    error: str
    logger_name: str
    detail_label: str
    detail_value: str
    body: str


class _PlainFileFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return formatted.rstrip()


class _ConsoleLogFormatter(logging.Formatter):
    def __init__(self, *, accent_color: str, use_color: bool) -> None:
        super().__init__(datefmt="%H:%M:%S")
        self._use_color = use_color
        self._palette = _build_console_palette(accent_color)

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        level = record.levelname.lower().ljust(7)
        logger_name = _short_logger_name(record.name)

        header = " ".join(
            [
                self._colorize(timestamp, self._palette.timestamp),
                self._colorize(level, _level_color(record.levelno, self._palette)),
                self._colorize(logger_name, self._palette.logger_name),
            ]
        )

        message = record.getMessage().rstrip()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}".strip()
        if record.stack_info:
            message = f"{message}\n{self.formatStack(record.stack_info)}".strip()

        if not message:
            return header

        body_lines = [_style_console_line(line, self._palette, self._use_color) for line in message.splitlines()]
        if len(body_lines) == 1:
            return f"{header}  {body_lines[0]}"
        indented_body = "\n".join(f"  {line}" if line else "" for line in body_lines)
        return f"{header}\n{indented_body}"

    def _colorize(self, value: str, color: str) -> str:
        if not self._use_color or not value:
            return value
        return f"{color}{value}{_ANSI_RESET}"


def configure_app_logging(
    root_dir: Path,
    *,
    accent_color: str = DEFAULT_ACCENT_COLOR,
) -> Path:
    root_dir.mkdir(parents=True, exist_ok=True)
    log_file = root_dir / "glance.log"
    logger = logging.getLogger("glance")

    file_handler = _get_handler(logger, _FILE_HANDLER_NAME)
    if file_handler is None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.set_name(_FILE_HANDLER_NAME)
        logger.addHandler(file_handler)
    elif not isinstance(file_handler, logging.FileHandler) or Path(
        file_handler.baseFilename
    ) != log_file:
        logger.removeHandler(file_handler)
        file_handler.close()
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.set_name(_FILE_HANDLER_NAME)
        logger.addHandler(file_handler)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        _PlainFileFormatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S%z",
        )
    )

    console_handler = _get_handler(logger, _CONSOLE_HANDLER_NAME)
    if console_handler is None:
        console_handler = logging.StreamHandler()
        console_handler.set_name(_CONSOLE_HANDLER_NAME)
        logger.addHandler(console_handler)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        _ConsoleLogFormatter(
            accent_color=accent_color,
            use_color=_stream_supports_color(getattr(console_handler, "stream", None)),
        )
    )

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return log_file


def update_console_logging_accent(accent_color: str) -> None:
    logger = logging.getLogger("glance")
    handler = _get_handler(logger, _CONSOLE_HANDLER_NAME)
    if handler is None:
        return
    handler.setFormatter(
        _ConsoleLogFormatter(
            accent_color=accent_color,
            use_color=_stream_supports_color(getattr(handler, "stream", None)),
        )
    )


def _get_handler(logger: logging.Logger, name: str) -> logging.Handler | None:
    for handler in logger.handlers:
        if handler.get_name() == name:
            return handler
    return None


def _short_logger_name(name: str) -> str:
    if name == "glance":
        return name
    if name.startswith("glance."):
        return name.removeprefix("glance.")
    return name


def _level_color(levelno: int, palette: _ConsolePalette) -> str:
    if levelno >= logging.ERROR:
        return palette.error
    if levelno >= logging.WARNING:
        return palette.warning
    if levelno <= logging.DEBUG:
        return palette.debug
    return palette.info


def _style_console_line(line: str, palette: _ConsolePalette, use_color: bool) -> str:
    if not use_color or not line:
        return line

    detail_match = re.match(r"^(?P<label>[a-z][a-z _-]{1,20})(?P<gap>\s{2,})(?P<value>.+)$", line)
    if detail_match is not None:
        label = detail_match.group("label")
        gap = detail_match.group("gap")
        value = _TIMING_PATTERN.sub(
            lambda match: f"{palette.info}{match.group(0)}{_ANSI_RESET}{palette.detail_value}",
            detail_match.group("value"),
        )
        return (
            f"{palette.detail_label}{label}{_ANSI_RESET}"
            f"{palette.body}{gap}{_ANSI_RESET}"
            f"{palette.detail_value}{value}{_ANSI_RESET}"
        )

    styled_line = _TIMING_PATTERN.sub(
        lambda match: f"{palette.info}{match.group(0)}{_ANSI_RESET}{palette.body}",
        line,
    )
    return f"{palette.body}{styled_line}{_ANSI_RESET}"


def _stream_supports_color(stream) -> bool:
    if stream is None or not hasattr(stream, "isatty"):
        return False
    if not stream.isatty():
        return False
    return os.environ.get("TERM", "").lower() != "dumb"


def _build_console_palette(accent_color: str) -> _ConsolePalette:
    normalized_accent = normalize_hex_color(accent_color)
    accent_rgb = _hex_to_rgb(normalized_accent)
    muted_rgb = _mix_rgb(accent_rgb, (138, 146, 160), 0.4)
    detail_rgb = _mix_rgb(accent_rgb, (242, 247, 244), 0.76)
    body_rgb = _mix_rgb(accent_rgb, (226, 231, 236), 0.68)
    return _ConsolePalette(
        timestamp=_ansi_rgb(_mix_rgb(accent_rgb, (122, 128, 138), 0.3)),
        info=_ansi_rgb(_boost_rgb(accent_rgb, 1.08, floor=146)),
        debug=_ansi_rgb(muted_rgb),
        warning=_ansi_rgb((245, 183, 82)),
        error=_ansi_rgb((255, 112, 112)),
        logger_name=_ansi_rgb(_mix_rgb(accent_rgb, (180, 186, 196), 0.5)),
        detail_label=_ansi_rgb(muted_rgb),
        detail_value=_ansi_rgb(detail_rgb),
        body=_ansi_rgb(body_rgb),
    )


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    stripped_value = value.lstrip("#")
    return tuple(int(stripped_value[index : index + 2], 16) for index in (0, 2, 4))


def _mix_rgb(
    first: tuple[int, int, int],
    second: tuple[int, int, int],
    ratio: float,
) -> tuple[int, int, int]:
    return tuple(
        _clamp_channel(first[index] * ratio + second[index] * (1 - ratio))
        for index in range(3)
    )


def _boost_rgb(
    value: tuple[int, int, int],
    factor: float,
    *,
    floor: int = 0,
) -> tuple[int, int, int]:
    return tuple(
        _clamp_channel(max(channel * factor, floor)) for channel in value
    )


def _clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _ansi_rgb(value: tuple[int, int, int]) -> str:
    red, green, blue = value
    return f"\033[38;2;{red};{green};{blue}m"
