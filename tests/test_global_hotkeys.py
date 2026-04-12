import unittest
from unittest.mock import patch

from src.exceptions.app_exceptions import PermissionDeniedError
from src.models.settings import AppSettings
from src.services import global_hotkeys


class FakeListener:
    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release
        self.started = False
        self.stopped = False
        self.waited = False
        self.joined_with = None

    def start(self) -> None:
        self.started = True

    def wait(self) -> None:
        self.waited = True

    def stop(self) -> None:
        self.stopped = True

    def join(self, timeout=None) -> None:
        self.joined_with = timeout

    def canonical(self, key):
        return key


class FakeHotKey:
    def __init__(self, keys, on_activate):
        self.keys = keys
        self.on_activate = on_activate
        self.pressed = []
        self.released = []

    @staticmethod
    def parse(keys):
        return keys

    def press(self, key) -> None:
        self.pressed.append(key)

    def release(self, key) -> None:
        self.released.append(key)


class FakeHotKeyType:
    def __init__(self, module) -> None:
        self._module = module

    @staticmethod
    def parse(keys):
        return keys

    def __call__(self, keys, on_activate):
        hotkey = FakeHotKey(keys, on_activate)
        self._module.hotkeys.append(hotkey)
        return hotkey


class FakeKeyboardModule:
    def __init__(self) -> None:
        self.listener = None
        self.listeners = []
        self.hotkeys = []
        self.HotKey = FakeHotKeyType(self)

    def Listener(self, on_press=None, on_release=None):
        self.listener = FakeListener(on_press=on_press, on_release=on_release)
        self.listeners.append(self.listener)
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
        self.assertTrue(keyboard_module.listener.waited)
        self.assertEqual(len(keyboard_module.listeners), 1)
        self.assertEqual(keyboard_module.hotkeys[0].keys, "<cmd>+<shift>+l")

    def test_stop_waits_for_listener_shutdown(self) -> None:
        keyboard_module = FakeKeyboardModule()
        manager = global_hotkeys.GlobalHotkeyManager({"live": lambda: None})

        with (
            patch.object(global_hotkeys, "keyboard", keyboard_module),
            patch.object(
                global_hotkeys, "_input_monitoring_is_trusted", return_value=True
            ),
        ):
            manager.update_bindings(AppSettings())
            manager.stop()

        self.assertTrue(keyboard_module.listener.stopped)
        self.assertEqual(keyboard_module.listener.joined_with, 1.0)

    def test_update_bindings_reuses_listener_and_rebuilds_hotkeys(self) -> None:
        keyboard_module = FakeKeyboardModule()
        manager = global_hotkeys.GlobalHotkeyManager({"live": lambda: None})
        first_settings = AppSettings()
        second_settings = AppSettings.from_mapping(
            {
                "live_keybind": "CMD+K",
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "claude-opus-4.6",
                "tts_base_url": "https://api.naga.ac/v1",
            },
            validate=False,
        )

        with (
            patch.object(global_hotkeys, "keyboard", keyboard_module),
            patch.object(
                global_hotkeys, "_input_monitoring_is_trusted", return_value=True
            ),
        ):
            manager.update_bindings(first_settings)
            manager.update_bindings(second_settings)

        self.assertEqual(len(keyboard_module.listeners), 1)
        self.assertEqual(keyboard_module.hotkeys[-1].keys, "<cmd>+k")

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
