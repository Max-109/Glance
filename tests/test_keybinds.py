import tempfile
import unittest
from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from src.services.history_manager import HistoryManager
    from src.services.settings_manager import SettingsManager
    from src.storage.json_storage import JsonHistoryRepository, JsonSettingsStore
    from src.ui.settings_viewmodel import SettingsViewModel
except ImportError:  # pragma: no cover - optional GUI dependency.
    Qt = None
    HistoryManager = None
    SettingsManager = None
    JsonHistoryRepository = None
    JsonSettingsStore = None
    SettingsViewModel = None

from src.services.keybinds import (
    keybinds_are_unique,
    normalize_keybind,
    qt_event_to_keybind,
)
from src.models.settings import AppSettings


class KeybindUtilityTests(unittest.TestCase):
    def test_normalize_keybind_orders_and_uppercases_parts(self) -> None:
        self.assertEqual(normalize_keybind("cmd+shift+l"), "CMD+SHIFT+L")
        self.assertEqual(normalize_keybind("alt+ctrl+7"), "CTRL+ALT+7")

    def test_keybinds_are_unique_detects_collisions(self) -> None:
        self.assertFalse(keybinds_are_unique(["cmd+l", "CMD+L", "ctrl+o"]))

    @unittest.skipIf(Qt is None, "PySide6 is not installed")
    def test_qt_event_to_keybind_builds_uppercase_shortcuts(self) -> None:
        keybind = qt_event_to_keybind(
            Qt.Key_L,
            Qt.MetaModifier.value | Qt.ShiftModifier.value,
            "l",
        )
        self.assertEqual(keybind, "CMD+SHIFT+L")

    @unittest.skipIf(Qt is None, "PySide6 is not installed")
    def test_qt_event_to_keybind_prefers_physical_letter_over_alt_text(self) -> None:
        keybind = qt_event_to_keybind(
            Qt.Key_L,
            Qt.AltModifier.value,
            "∆",
        )
        self.assertEqual(keybind, "ALT+L")

    @unittest.skipIf(Qt is None, "PySide6 is not installed")
    def test_qt_event_to_keybind_maps_control_to_ctrl(self) -> None:
        keybind = qt_event_to_keybind(
            Qt.Key_K,
            Qt.ControlModifier.value,
            "k",
        )
        self.assertEqual(keybind, "CTRL+K")


@unittest.skipIf(Qt is None, "PySide6 is not installed")
class SettingsViewModelKeybindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        settings_manager = SettingsManager(
            store=JsonSettingsStore(temp_path / "config.json"),
        )
        settings_manager.save(
            AppSettings.from_mapping(
                {
                    "llm_base_url": "https://api.example.com/v1",
                    "llm_model_name": "claude-opus-4.6",
                    "tts_base_url": "https://api.naga.ac/v1",
                }
            )
        )
        self.settings_manager = settings_manager
        history_manager = HistoryManager(
            JsonHistoryRepository(temp_path / "history.json"),
            history_limit=5,
        )
        self.viewmodel = SettingsViewModel(settings_manager, history_manager)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_capture_keybind_updates_selected_field(self) -> None:
        self.viewmodel.startKeybindCapture("live_keybind")

        self.viewmodel.captureKeybind(
            Qt.Key_L,
            Qt.MetaModifier.value | Qt.ShiftModifier.value,
            "l",
        )

        self.assertEqual(self.viewmodel.settings["live_keybind"], "CMD+SHIFT+L")
        self.assertFalse(self.viewmodel.bindingActive)

    def test_capture_keybind_rejects_duplicate_shortcut(self) -> None:
        self.viewmodel.startKeybindCapture("quick_keybind")

        self.viewmodel.captureKeybind(
            Qt.Key_L,
            Qt.MetaModifier.value | Qt.ShiftModifier.value,
            "l",
        )

        self.assertEqual(
            self.viewmodel.errors["quick_keybind"],
            "Already used by Live.",
        )

    def test_capture_keybind_persists_immediately(self) -> None:
        self.viewmodel.startKeybindCapture("quick_keybind")

        self.viewmodel.captureKeybind(Qt.Key_K, Qt.AltModifier.value, "k")

        self.assertEqual(self.settings_manager.reload().quick_keybind, "ALT+K")

    def test_escape_cancels_capture_without_changing_saved_keybind(self) -> None:
        emitted = []
        self.viewmodel.savedSettingsChanged.connect(lambda: emitted.append(True))
        original_keybind = self.settings_manager.reload().live_keybind
        self.viewmodel.startKeybindCapture("live_keybind")

        self.viewmodel.captureKeybind(Qt.Key_Escape, 0, "")

        self.assertFalse(self.viewmodel.bindingActive)
        self.assertEqual(self.settings_manager.reload().live_keybind, original_keybind)
        self.assertEqual(emitted, [])

    def test_save_allows_unset_llm_base_url(self) -> None:
        self.viewmodel.setField("llm_base_url", "")
        self.viewmodel.setField("history_length", "12")

        self.viewmodel.save()

        self.assertEqual(self.settings_manager.reload().history_length, 12)
        self.assertEqual(self.viewmodel.errors, {})

    def test_regular_field_autosaves_without_manual_save(self) -> None:
        self.viewmodel.setField("llm_model_name", "claude-sonnet-4.6")

        self.assertEqual(
            self.settings_manager.reload().llm_model_name,
            "claude-sonnet-4.6",
        )
        self.assertFalse(self.viewmodel.dirty)

    def test_invalid_autosave_keeps_last_valid_config(self) -> None:
        original_threshold = self.settings_manager.reload().screen_change_threshold

        self.viewmodel.setField("screen_change_threshold", "1.2")

        self.assertEqual(
            self.settings_manager.reload().screen_change_threshold,
            original_threshold,
        )
        self.assertEqual(
            self.viewmodel.errors["screen_change_threshold"],
            "Use a value between 0 and 1.",
        )
        self.assertTrue(self.viewmodel.dirty)


if __name__ == "__main__":
    unittest.main()
