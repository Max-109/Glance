from __future__ import annotations

from collections.abc import Iterable

from src.exceptions.app_exceptions import ValidationError


MODIFIER_ORDER = ("CMD", "CTRL", "ALT", "SHIFT")
MODIFIER_ALIASES = {
    "CONTROL": "CTRL",
    "CTRL": "CTRL",
    "OPTION": "ALT",
    "ALT": "ALT",
    "SHIFT": "SHIFT",
    "COMMAND": "CMD",
    "CMD": "CMD",
    "META": "CMD",
    "SUPER": "CMD",
}
SPECIAL_KEYS = {
    "ESC": "ESC",
    "ESCAPE": "ESC",
    "SPACE": "SPACE",
    "TAB": "TAB",
    "ENTER": "ENTER",
    "RETURN": "ENTER",
    "BACKSPACE": "BACKSPACE",
    "DELETE": "DELETE",
    "UP": "UP",
    "DOWN": "DOWN",
    "LEFT": "LEFT",
    "RIGHT": "RIGHT",
}
PYNPUT_SPECIAL_KEYS = {
    "SPACE": "space",
    "TAB": "tab",
    "ENTER": "enter",
    "ESC": "esc",
    "BACKSPACE": "backspace",
    "DELETE": "delete",
    "UP": "up",
    "DOWN": "down",
    "LEFT": "left",
    "RIGHT": "right",
}

def normalize_keybind(value: str) -> str:
    parts = [
        segment.strip() for segment in str(value).split("+") if segment.strip()
    ]
    if not parts:
        raise ValidationError("Shortcut cannot be empty.")

    normalized_modifiers: list[str] = []
    main_key = ""
    for raw_part in parts:
        upper_part = raw_part.upper()
        if upper_part in MODIFIER_ALIASES:
            canonical_modifier = MODIFIER_ALIASES[upper_part]
            if canonical_modifier not in normalized_modifiers:
                normalized_modifiers.append(canonical_modifier)
            continue
        if main_key:
            raise ValidationError(
                "Shortcut must have exactly one non-modifier key."
            )
        main_key = _normalize_main_key(upper_part)

    if not main_key:
        raise ValidationError("Shortcut must include a non-modifier key.")

    ordered_modifiers = [
        name for name in MODIFIER_ORDER if name in normalized_modifiers
    ]
    return "+".join([*ordered_modifiers, main_key])


def keybinds_are_unique(bindings: Iterable[str]) -> bool:
    normalized = [normalize_keybind(value) for value in bindings]
    return len(normalized) == len(set(normalized))


def to_pynput_hotkey(value: str) -> str:
    keybind = normalize_keybind(value)
    parts = keybind.split("+")
    converted: list[str] = []
    for part in parts[:-1]:
        if part == "CTRL":
            converted.append("<ctrl>")
        elif part == "ALT":
            converted.append("<alt>")
        elif part == "SHIFT":
            converted.append("<shift>")
        elif part == "CMD":
            converted.append("<cmd>")

    last_part = parts[-1]
    if last_part.startswith("F") and last_part[1:].isdigit():
        converted.append(f"<{last_part.lower()}>")
    elif last_part in PYNPUT_SPECIAL_KEYS:
        converted.append(f"<{PYNPUT_SPECIAL_KEYS[last_part]}>")
    else:
        converted.append(last_part.lower())
    return "+".join(converted)


def _normalize_main_key(value: str) -> str:
    if len(value) == 1 and value.isprintable():
        return value.upper()
    if value in SPECIAL_KEYS:
        return SPECIAL_KEYS[value]
    if value.startswith("F") and value[1:].isdigit():
        return value
    raise ValidationError(f"Unsupported shortcut key: {value}")
