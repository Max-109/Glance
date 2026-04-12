import tempfile
import unittest
from pathlib import Path

from src.models.settings import AppSettings
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import JsonSettingsStore


class SettingsManagerTests(unittest.TestCase):
    def test_persisted_values_override_env_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / ".env"
            env_file.write_text(
                "LLM_BASE_URL=https://env.example/v1\n"
                "LLM_MODEL=claude-opus-4.6\n"
                "TTS_BASE_URL=https://tts.example/v1\n",
                encoding="utf-8",
            )

            store = JsonSettingsStore(temp_path / "config.json")
            store.save(
                AppSettings.from_mapping(
                    {
                        "llm_base_url": "https://persisted.example/v1",
                        "llm_model_name": "claude-opus-4.6",
                        "tts_base_url": "https://tts.example/v1",
                    }
                )
            )

            manager = SettingsManager(store=store, env_file=env_file)
            settings = manager.load()

        self.assertEqual(settings.llm_base_url, "https://persisted.example/v1")


if __name__ == "__main__":
    unittest.main()
