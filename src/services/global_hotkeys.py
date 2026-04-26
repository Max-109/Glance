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
        self._enabled = True
        self._hotkey_specs: list[tuple[str, Callable[[], None]]] = []
        self._hotkeys = []

    def update_bindings(self, settings: AppSettings) -> None:
        if keyboard is None:
            raise PermissionDeniedError(
                "Global hotkeys require the 'pynput' package and "
                "accessibility permission."
            )
        if not _input_monitoring_is_trusted():
            logger.info(
                "Hotkeys disabled because Accessibility access is not granted"
            )
            raise PermissionDeniedError(
                "Global hotkeys require macOS Accessibility access for the "
                "app that launches Glance, such as Terminal or iTerm."
            )

        with self._lock:
            self._ensure_listener_locked()
            self._hotkey_specs = self._build_hotkey_specs(settings)
            self._rebuild_hotkeys_locked()
            logger.debug(
                "Active hotkeys updated in place: %s",
                ", ".join(
                    description for description, _ in self._hotkey_specs
                ),
            )

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            if self._enabled == enabled:
                return
            self._enabled = enabled
            self._rebuild_hotkeys_locked()
            logger.debug("Hotkeys %s", "enabled" if enabled else "suspended")

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _build_hotkey_specs(
        self, settings: AppSettings
    ) -> list[tuple[str, Callable[[], None]]]:
        mapping = {
            settings.live_keybind: self._callbacks.get("live"),
            settings.ocr_keybind: self._callbacks.get("ocr"),
            settings.open_glance_keybind: self._callbacks.get("open_glance"),
        }
        return [
            (to_pynput_hotkey(keybind), callback)
            for keybind, callback in mapping.items()
            if callback is not None
        ]

    def _ensure_listener_locked(self) -> None:
        if self._listener is not None:
            return
        try:
            listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            logger.debug("Starting hotkey listener")
            listener.start()
            wait_method = getattr(listener, "wait", None)
            if callable(wait_method):
                logger.debug("Waiting for hotkey listener to become active")
                wait_method()
        except Exception as exc:
            if _is_accessibility_permission_error(exc):
                logger.info(
                    "Hotkey registration failed because Accessibility access "
                    "is not granted"
                )
                raise PermissionDeniedError(
                    "Global hotkeys require macOS Accessibility access for "
                    "the app that launches Glance, such as Terminal or iTerm."
                ) from exc
            raise
        self._listener = listener
        logger.debug("Hotkey listener active")

    def _rebuild_hotkeys_locked(self) -> None:
        if keyboard is None:
            self._hotkeys = []
            return
        self._hotkeys = [
            keyboard.HotKey(keyboard.HotKey.parse(description), callback)
            for description, callback in self._hotkey_specs
        ]

    def _on_press(self, key) -> None:
        with self._lock:
            if not self._enabled or self._listener is None:
                return
            canonical_key = self._listener.canonical(key)
            hotkeys = list(self._hotkeys)
        for hotkey in hotkeys:
            hotkey.press(canonical_key)

    def _on_release(self, key) -> None:
        with self._lock:
            if self._listener is None:
                return
            canonical_key = self._listener.canonical(key)
            hotkeys = list(self._hotkeys)
        for hotkey in hotkeys:
            hotkey.release(canonical_key)

    def _stop_locked(self) -> None:
        if self._listener is None:
            return
        logger.debug("Stopping hotkeys")
        listener = self._listener
        listener.stop()
        join_method = getattr(listener, "join", None)
        if callable(join_method):
            logger.debug("Waiting for hotkey listener to stop")
            join_method(timeout=1.0)
        logger.debug("Hotkey listener stopped")
        self._listener = None
        self._hotkeys = []


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
    return (
        "AXIsProcessTrusted" in message or "accessibility" in message.lower()
    )
