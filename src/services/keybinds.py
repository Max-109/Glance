from __future__ import annotations

from collections.abc import Iterable

from src.exceptions.app_exceptions import ValidationError

try:
    from PySide6.QtCore import Qt
except ImportError:  # pragma: no cover - optional in non-Qt test environments.
    Qt = None


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
QT_SPECIAL_KEYS = {
    "Key_Escape": "ESC",
    "Key_Tab": "TAB",
    "Key_Backtab": "TAB",
    "Key_Backspace": "BACKSPACE",
    "Key_Return": "ENTER",
    "Key_Enter": "ENTER",
    "Key_Delete": "DELETE",
    "Key_Space": "SPACE",
    "Key_Up": "UP",
    "Key_Down": "DOWN",
    "Key_Left": "LEFT",
    "Key_Right": "RIGHT",
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
    elif last_part in {
        "SPACETABENTERESCBACKSPACEDELETEUPDOWNLEFTRIGHT",
    }:
        translated = {
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
        converted.append(f"<{translated[last_part]}>")
    else:
        converted.append(last_part.lower())
    return "+".join(converted)


def qt_event_to_keybind(key: int, modifiers: int, text: str) -> str | None:
    if Qt is None:
        raise RuntimeError(
            "Qt is required to build a shortcut from key events."
        )

    key_value = _enum_value(key)
    modifier_value = _enum_value(modifiers)

    if key_value == _enum_value(Qt.Key_Escape):
        return "ESC"

    if key_value in {
        _enum_value(Qt.Key_Control),
        _enum_value(Qt.Key_Meta),
        _enum_value(Qt.Key_Alt),
        _enum_value(Qt.Key_Shift),
    }:
        return None

    parts: list[str] = []
    if modifier_value & _enum_value(Qt.ControlModifier):
        parts.append("CTRL")
    if modifier_value & _enum_value(Qt.AltModifier):
        parts.append("ALT")
    if modifier_value & _enum_value(Qt.ShiftModifier):
        parts.append("SHIFT")
    if modifier_value & _enum_value(Qt.MetaModifier):
        parts.append("CMD")

    main_key = _qt_key_to_string(key_value, text)
    if not main_key:
        return None
    return normalize_keybind("+".join([*parts, main_key]))


def _normalize_main_key(value: str) -> str:
    if len(value) == 1 and value.isprintable():
        return value.upper()
    if value in SPECIAL_KEYS:
        return SPECIAL_KEYS[value]
    if value.startswith("F") and value[1:].isdigit():
        return value
    raise ValidationError(f"Unsupported shortcut key: {value}")


def _qt_key_to_string(key: int, text: str) -> str | None:
    if Qt is None:
        return None
    if _enum_value(Qt.Key_A) <= key <= _enum_value(Qt.Key_Z):
        return chr(ord("A") + key - _enum_value(Qt.Key_A))
    if _enum_value(Qt.Key_0) <= key <= _enum_value(Qt.Key_9):
        return chr(ord("0") + key - _enum_value(Qt.Key_0))

    key_name = _qt_key_name(key)
    if key_name in QT_SPECIAL_KEYS:
        return QT_SPECIAL_KEYS[key_name]
    if key_name.startswith("Key_F") and key_name[5:].isdigit():
        return key_name[4:].upper()
    if key_name.startswith("Key_"):
        suffix = key_name[4:]
        if len(suffix) == 1 and suffix.isalnum():
            return suffix.upper()

    stripped_text = text.strip()
    if len(stripped_text) == 1 and stripped_text.isprintable():
        return stripped_text.upper()

    if 32 <= key <= 126:
        return chr(key).upper()
    return None


def _qt_key_name(key: int) -> str:
    if Qt is None:
        return ""
    for name in dir(Qt):
        candidate = getattr(Qt, name)
        try:
            if int(candidate) == key:
                return name
        except (TypeError, ValueError):
            continue
    return ""


def _enum_value(value) -> int:
    return int(getattr(value, "value", value))
