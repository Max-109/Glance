import unittest
from unittest.mock import patch

from src.exceptions.app_exceptions import PermissionDeniedError
from src.models.settings import AppSettings
from src.services import global_hotkeys


class FakeListener:
    def __init__(self, mapping):
        self.mapping = mapping
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class FakeKeyboardModule:
    def __init__(self) -> None:
        self.listener = None

    def GlobalHotKeys(self, mapping):
        self.listener = FakeListener(mapping)
        return self.listener


class GlobalHotkeyManagerTests(unittest.TestCase):
    def test_update_bindings_starts_listener_when_trusted(self) -> None:
        keyboard_module = FakeKeyboardModule()
        manager = global_hotkeys.GlobalHotkeyManager({"live": lambda: None})

        with (
            patch.object(global_hotkeys, "keyboard", keyboard_module),
            patch.object(
                global_hotkeys, "_input_monitoring_is_trusted", return_value=True
            ),
        ):
            manager.update_bindings(AppSettings())

        self.assertTrue(keyboard_module.listener.started)
        self.assertIn("<cmd>+<shift>+l", keyboard_module.listener.mapping)

    def test_update_bindings_raises_permission_error_when_untrusted(self) -> None:
        manager = global_hotkeys.GlobalHotkeyManager({"live": lambda: None})

        with (
            patch.object(global_hotkeys, "keyboard", FakeKeyboardModule()),
            patch.object(
                global_hotkeys, "_input_monitoring_is_trusted", return_value=False
            ),
        ):
            with self.assertRaises(PermissionDeniedError):
                manager.update_bindings(AppSettings())

    def test_input_monitoring_uses_application_services_symbol(self) -> None:
        fake_framework = type("FakeFramework", (), {"AXIsProcessTrusted": lambda: True})

        with (
            patch.object(global_hotkeys.sys, "platform", "darwin"),
            patch.object(global_hotkeys, "ApplicationServices", fake_framework),
            patch.object(global_hotkeys, "HIServices", None),
        ):
            self.assertTrue(global_hotkeys._input_monitoring_is_trusted())


if __name__ == "__main__":
    unittest.main()
