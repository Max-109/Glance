from __future__ import annotations

from collections.abc import Callable
import logging
import sys
from threading import Lock

from src.exceptions.app_exceptions import PermissionDeniedError
from src.models.settings import AppSettings
from src.services.keybinds import to_pynput_hotkey

try:
    from pynput import keyboard
except ImportError:  # pragma: no cover - optional runtime dependency.
    keyboard = None

try:
    import ApplicationServices
except ImportError:  # pragma: no cover - only available on macOS with pyobjc.
    ApplicationServices = None

try:
    import HIServices
except ImportError:  # pragma: no cover - only available on macOS with pyobjc.
    HIServices = None


logger = logging.getLogger("glance.hotkeys")


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
        if not _input_monitoring_is_trusted():
            logger.info("Hotkeys disabled because Accessibility access is not granted")
            raise PermissionDeniedError(
                "Global hotkeys require macOS Accessibility access for the app that launches Glance, such as Terminal or iTerm."
            )

        with self._lock:
            self._stop_locked()
            hotkey_map = self._build_hotkey_map(settings)
            logger.info("Registering hotkeys: %s", ", ".join(sorted(hotkey_map.keys())))
            try:
                listener = keyboard.GlobalHotKeys(hotkey_map)
                listener.start()
            except Exception as exc:
                if _is_accessibility_permission_error(exc):
                    logger.info(
                        "Hotkey registration failed because Accessibility access is not granted"
                    )
                    raise PermissionDeniedError(
                        "Global hotkeys require macOS Accessibility access for the app that launches Glance, such as Terminal or iTerm."
                    ) from exc
                raise
            self._listener = listener
            logger.info("Hotkeys registered successfully")

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
        logger.info("Stopping hotkeys")
        self._listener.stop()
        self._listener = None


def _input_monitoring_is_trusted() -> bool:
    if sys.platform != "darwin":
        return True
    trust_function = _resolve_trust_function()
    if trust_function is None:
        return True
    return bool(trust_function())


def _resolve_trust_function():
    for framework in (ApplicationServices, HIServices):
        if framework is None:
            continue
        trust_function = getattr(framework, "AXIsProcessTrusted", None)
        if trust_function is not None:
            return trust_function
    return None


def _is_accessibility_permission_error(exc: Exception) -> bool:
    if sys.platform != "darwin":
        return False
    message = str(exc)
    return "AXIsProcessTrusted" in message or "accessibility" in message.lower()
