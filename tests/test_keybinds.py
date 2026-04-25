import tempfile
import unittest
from pathlib import Path

try:
    from PySide6.QtCore import QCoreApplication, Qt
    from src.services.history_manager import HistoryManager
    from src.services.settings_manager import SettingsManager
    from src.storage.json_storage import JsonSettingsStore, SessionDirectoryRepository
    from src.ui.settings_viewmodel import SettingsViewModel
    from src.services.audio_devices import AudioDeviceOption
except ImportError:  # pragma: no cover - optional GUI dependency.
    QCoreApplication = None
    Qt = None
    HistoryManager = None
    SettingsManager = None
    SessionDirectoryRepository = None
    JsonSettingsStore = None
    SettingsViewModel = None
    AudioDeviceOption = None

from src.services.keybinds import (
    keybinds_are_unique,
    normalize_keybind,
    qt_event_to_keybind,
)
from src.models.interactions import QuickInteraction
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
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.qt_app = QCoreApplication.instance() or QCoreApplication([])

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
            SessionDirectoryRepository(temp_path / "sessions"),
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

    def test_capture_keybind_stays_dirty_until_save(self) -> None:
        self.viewmodel.startKeybindCapture("quick_keybind")

        self.viewmodel.captureKeybind(Qt.Key_K, Qt.AltModifier.value, "k")

        self.assertEqual(self.settings_manager.reload().quick_keybind, "CMD+SHIFT+Q")
        self.assertTrue(self.viewmodel.dirty)

    def test_assign_keybind_updates_without_persisting_shortcut(self) -> None:
        self.viewmodel.startKeybindCapture("quick_keybind")

        self.viewmodel.assignKeybind("quick_keybind", "alt+k")

        self.assertEqual(self.viewmodel.settings["quick_keybind"], "ALT+K")
        self.assertEqual(self.settings_manager.reload().quick_keybind, "CMD+SHIFT+Q")
        self.assertFalse(self.viewmodel.bindingActive)
        self.assertTrue(self.viewmodel.dirty)

    def test_assign_keybind_rejects_duplicate_shortcut(self) -> None:
        self.viewmodel.startKeybindCapture("quick_keybind")

        self.viewmodel.assignKeybind("quick_keybind", "cmd+shift+l")

        self.assertEqual(
            self.viewmodel.errors["quick_keybind"],
            "Already used by Live.",
        )
        self.assertTrue(self.viewmodel.bindingActive)

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

    def test_regular_field_stays_dirty_until_manual_save(self) -> None:
        self.viewmodel.setField("llm_model_name", "claude-sonnet-4.6")

        self.assertEqual(
            self.settings_manager.reload().llm_model_name,
            "claude-opus-4.6",
        )
        self.assertTrue(self.viewmodel.dirty)

    def test_invalid_save_keeps_last_valid_config(self) -> None:
        original_threshold = self.settings_manager.reload().screen_change_threshold

        self.viewmodel.setField("screen_change_threshold", "1.2")
        self.viewmodel.save()

        self.assertEqual(
            self.settings_manager.reload().screen_change_threshold,
            original_threshold,
        )
        self.assertEqual(
            self.viewmodel.errors["screen_change_threshold"],
            "Use a value between 0 and 1.",
        )
        self.assertTrue(self.viewmodel.dirty)

    def test_audio_fields_stay_dirty_until_manual_save(self) -> None:
        self.viewmodel.setField("audio_vad_threshold", "0.6")

        self.assertEqual(
            self.settings_manager.reload().audio_vad_threshold, 0.5
        )
        self.assertTrue(self.viewmodel.dirty)

    def test_build_history_preview_uses_latest_interaction_summary_and_answer(self) -> None:
        session = self.viewmodel._history_manager.start_session("quick")
        self.viewmodel._history_manager.save_interaction(
            session,
            QuickInteraction(
                mode="quick",
                question="What changed on the screen?",
                answer="A modal opened with the new deployment summary.\nIt also shows two warnings.",
                image_path="capture.png",
            ),
        )

        preview = self.viewmodel.buildHistoryPreview(limit=1)

        self.assertEqual(len(preview), 1)
        self.assertEqual(preview[0]["mode"], "quick")
        self.assertEqual(preview[0]["interactionCount"], 1)
        self.assertEqual(preview[0]["title"], "Quick: What changed on the screen?")
        self.assertEqual(
            preview[0]["excerpt"],
            "A modal opened with the new deployment summary. It also shows two warnings.",
        )

    def test_reset_audio_defaults_uses_transient_status_for_noop(self) -> None:
        self.viewmodel._set_status("Saved.", "success")

        self.viewmodel.resetAudioDefaults()

        revision = self.viewmodel._status_revision
        self.assertEqual(self.viewmodel.statusMessage, "")
        self.assertEqual(self.viewmodel.statusKind, "neutral")

        self.viewmodel._apply_deferred_transient_status(
            revision,
            "Audio settings are already at their defaults.",
            "neutral",
            self.viewmodel._TRANSIENT_INFO_STATUS_DURATION_MS,
        )

        self.assertEqual(
            self.viewmodel.statusMessage,
            "Audio settings are already at their defaults.",
        )
        self.assertEqual(self.viewmodel.statusKind, "neutral")
        self.assertTrue(self.viewmodel._status_timer.isActive())

    def test_invalid_audio_preroll_shows_validation_error(self) -> None:
        self.viewmodel.setField("audio_preroll_seconds", "-1")
        self.viewmodel.save()

        self.assertEqual(
            self.viewmodel.errors["audio_preroll_seconds"],
            "Value cannot be negative.",
        )

    def test_audio_device_refresh_exposes_labels_and_preserves_missing_saved_value(
        self,
    ) -> None:
        self.viewmodel.setField("audio_input_device", "input:99")
        self.viewmodel._audio_device_service = type(
            "FakeAudioService",
            (),
            {
                "list_input_devices": staticmethod(
                    lambda: [
                        AudioDeviceOption("default", "System Default Input"),
                        AudioDeviceOption("input:0", "Built-in Mic"),
                    ]
                ),
                "list_output_devices": staticmethod(
                    lambda: [
                        AudioDeviceOption("default", "System Default Output"),
                    ]
                ),
            },
        )()

        self.viewmodel.refreshAudioDevices()

        self.assertIn("input:0", self.viewmodel.audioInputDeviceOptions)
        self.assertEqual(
            self.viewmodel.audioInputDeviceLabels["input:0"],
            "Built-in Mic",
        )
        self.assertEqual(
            self.viewmodel.audioInputDeviceLabels["input:99"],
            "Saved input device unavailable",
        )


if __name__ == "__main__":
    unittest.main()
