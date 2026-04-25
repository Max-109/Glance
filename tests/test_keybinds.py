import unittest

from src.services.keybinds import (
    keybinds_are_unique,
    normalize_keybind,
)


class KeybindUtilityTests(unittest.TestCase):
    def test_normalize_keybind_orders_and_uppercases_parts(self) -> None:
        self.assertEqual(normalize_keybind("cmd+shift+l"), "CMD+SHIFT+L")
        self.assertEqual(normalize_keybind("alt+ctrl+7"), "CTRL+ALT+7")

    def test_keybinds_are_unique_detects_collisions(self) -> None:
        self.assertFalse(keybinds_are_unique(["cmd+l", "CMD+L", "ctrl+o"]))


if __name__ == "__main__":
    unittest.main()
