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
    def test_memory_tool_policy_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            viewmodel = SettingsViewModel(
                SettingsManager(JsonSettingsStore(root / "config.json")),
                HistoryManager(
                    SessionDirectoryRepository(root / "sessions"),
                    history_limit=5,
                ),
                MemoryManager(root / "memories.json"),
                audio_device_service=FakeAudioDeviceService(),
                audio_signal_service=object(),
            )

            viewmodel.setField("tool_add_memory_policy", "lol")
            viewmodel.setField("tool_read_memory_policy", "nope")
            settings = viewmodel._validate_current_settings(
                show_status=False
            )

        self.assertIsNone(settings)
        self.assertEqual(
            viewmodel.errors["tool_add_memory_policy"],
            "Choose allow or deny.",
        )
        self.assertEqual(
            viewmodel.errors["tool_read_memory_policy"],
            "Choose allow or deny.",
        )


if __name__ == "__main__":
    unittest.main()
