from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from src.exceptions.app_exceptions import PermissionDeniedError
from src.models.settings import AppSettings
from src.services.keybinds import to_pynput_hotkey

try:
    from pynput import keyboard
except ImportError:  # pragma: no cover - optional runtime dependency.
    keyboard = None


class GlobalHotkeyManager:
    def __init__(self, callbacks: dict[str, Callable[[], None]]) -> None:
        self._callbacks = callbacks
        self._listener = None
        self._lock = Lock()

    def update_bindings(self, settings: AppSettings) -> None:
        if keyboard is None:
            raise PermissionDeniedError(
                "Global hotkeys require the 'pynput' package and accessibility permission."
            )

        with self._lock:
            self._stop_locked()
            hotkey_map = self._build_hotkey_map(settings)
            self._listener = keyboard.GlobalHotKeys(hotkey_map)
            self._listener.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _build_hotkey_map(self, settings: AppSettings) -> dict[str, Callable[[], None]]:
        mapping = {
            settings.live_keybind: self._callbacks.get("live"),
            settings.quick_keybind: self._callbacks.get("quick"),
            settings.ocr_keybind: self._callbacks.get("ocr"),
        }
        return {
            to_pynput_hotkey(keybind): callback
            for keybind, callback in mapping.items()
            if callback is not None
        }

    def _stop_locked(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
