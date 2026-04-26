import unittest

from src.services.keybinds import (
    keybinds_are_unique,
    normalize_keybind,
    to_pynput_hotkey,
)


class KeybindUtilityTests(unittest.TestCase):
    def test_normalize_keybind_orders_and_uppercases_parts(self) -> None:
        self.assertEqual(normalize_keybind("cmd+shift+l"), "CMD+SHIFT+L")
        self.assertEqual(normalize_keybind("alt+ctrl+7"), "CTRL+ALT+7")

    def test_keybinds_are_unique_detects_collisions(self) -> None:
        self.assertFalse(keybinds_are_unique(["cmd+l", "CMD+L", "ctrl+o"]))

    def test_to_pynput_hotkey_translates_special_keys(self) -> None:
        self.assertEqual(to_pynput_hotkey("cmd+space"), "<cmd>+<space>")
        self.assertEqual(to_pynput_hotkey("ctrl+enter"), "<ctrl>+<enter>")


if __name__ == "__main__":
    unittest.main()
