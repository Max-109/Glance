import tempfile
import unittest
from pathlib import Path

from src.services.history_manager import HistoryManager
from src.services.memory_manager import MemoryManager
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import (
    JsonSettingsStore,
    SessionDirectoryRepository,
)
from src.ui.settings_viewmodel import SettingsViewModel


class FakeAudioDeviceService:
    def list_input_devices(self):
        return []

    def list_output_devices(self):
        return []


class SettingsViewModelTests(unittest.TestCase):
    def _build_viewmodel(self, root: Path) -> SettingsViewModel:
        return SettingsViewModel(
            SettingsManager(JsonSettingsStore(root / "config.json")),
            HistoryManager(
                SessionDirectoryRepository(root / "sessions"),
                history_limit=5,
            ),
            MemoryManager(root / "memories.json"),
            audio_device_service=FakeAudioDeviceService(),
            audio_signal_service=object(),
        )

    def test_memory_tool_policy_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            viewmodel = self._build_viewmodel(root)

            viewmodel.setField("tool_add_memory_policy", "lol")
            viewmodel.setField("tool_read_memory_policy", "nope")
            viewmodel.setField("tool_change_memory_policy", "nah")
            settings = viewmodel._validate_current_settings(show_status=False)

        self.assertIsNone(settings)
        self.assertEqual(
            viewmodel.errors["tool_add_memory_policy"],
            "Choose allow or deny.",
        )
        self.assertEqual(
            viewmodel.errors["tool_read_memory_policy"],
            "Choose allow or deny.",
        )
        self.assertEqual(
            viewmodel.errors["tool_change_memory_policy"],
            "Choose allow or deny.",
        )

    def test_open_glance_keybind_can_be_captured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            viewmodel = self._build_viewmodel(Path(temp_dir))

            viewmodel.startKeybindCapture("open_glance_keybind")
            viewmodel.assignKeybind("open_glance_keybind", "cmd+alt+g")

        self.assertEqual(
            viewmodel.settings["open_glance_keybind"], "CMD+ALT+G")
        self.assertEqual(viewmodel.bindingField, "")
        self.assertEqual(
            viewmodel.statusMessage,
            "Open Glance shortcut saved.",
        )

    def test_open_glance_keybind_conflicts_with_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            viewmodel = self._build_viewmodel(Path(temp_dir))

            viewmodel.assignKeybind("open_glance_keybind", "cmd+shift+l")

        self.assertEqual(
            viewmodel.errors["open_glance_keybind"], "Already used by Live."
        )
        self.assertEqual(viewmodel.statusMessage,
                         "Each shortcut must be unique.")

    def test_show_status_exposes_runtime_notifications(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            viewmodel = self._build_viewmodel(Path(temp_dir))

            viewmodel.showStatus("Live failed: provider unavailable.", "error")

        self.assertEqual(
            viewmodel.statusMessage, "Live failed: provider unavailable."
        )
        self.assertEqual(viewmodel.statusKind, "error")


if __name__ == "__main__":
    unittest.main()
