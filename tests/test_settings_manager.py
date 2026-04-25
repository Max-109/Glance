import tempfile
import unittest
import json
from pathlib import Path

from src.models.prompt_defaults import (
    DEFAULT_TEXT_REPLY_PROMPT,
    DEFAULT_TRANSCRIPTION_PROMPT,
    DEFAULT_TTS_PREPARATION_PROMPT,
    DEFAULT_VOICE_REPLY_PROMPT,
)
from src.models.settings import AppSettings
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import JsonSettingsStore


class SettingsManagerTests(unittest.TestCase):
    def test_persisted_values_override_env_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
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

            manager = SettingsManager(store=store)
            settings = manager.load()

        self.assertEqual(settings.llm_base_url, "https://persisted.example/v1")
        self.assertEqual(
            settings.transcription_model_name,
            "whisper-large-v3-turbo",
        )

    def test_load_migrates_legacy_transcription_provider_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = JsonSettingsStore(temp_path / "config.json")
            (temp_path / "config.json").write_text(
                "{\n  \"llm_base_url\": \"https://persisted.example/v1\","
                "\n  "
                "\"llm_model_name\": \"claude-opus-4.6\",\n  "
                "\"tts_base_url\": "
                "\"https://speech.example/v1\",\n  \"tts_api_key\": "
                "\"speech-secret\"\n}",
                encoding="utf-8",
            )

            manager = SettingsManager(store=store)
            settings = manager.load()

        self.assertEqual(
            settings.transcription_base_url, "https://speech.example/v1"
        )
        self.assertEqual(settings.transcription_api_key, "speech-secret")

    def test_load_creates_defaults_without_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.json"
            manager = SettingsManager(store=JsonSettingsStore(config_path))

            settings = manager.load()
            saved_payload = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(settings.llm_base_url, "")
        self.assertEqual(
            settings.transcription_base_url, "https://api.naga.ac/v1"
        )
        self.assertEqual(settings.tts_base_url, "https://api.naga.ac/v1")
        self.assertEqual(
            saved_payload["text_prompt_override"], DEFAULT_TEXT_REPLY_PROMPT
        )
        self.assertEqual(
            saved_payload["voice_prompt_override"], DEFAULT_VOICE_REPLY_PROMPT
        )
        self.assertEqual(
            saved_payload["voice_polish_prompt_override"],
            DEFAULT_TTS_PREPARATION_PROMPT,
        )
        self.assertEqual(
            saved_payload["transcription_prompt_override"],
            DEFAULT_TRANSCRIPTION_PROMPT,
        )

    def test_load_rewrites_blank_prompt_values_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "llm_base_url": "https://persisted.example/v1",
                        "llm_model_name": "claude-opus-4.6",
                        "tts_base_url": "https://tts.example/v1",
                        "text_prompt_override": " ",
                        "voice_prompt_override": "",
                        "voice_polish_prompt_override": "\n",
                        "transcription_prompt_override": "   ",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            manager = SettingsManager(store=JsonSettingsStore(config_path))
            settings = manager.load()
            saved_payload = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(
            settings.text_prompt_override, DEFAULT_TEXT_REPLY_PROMPT
        )
        self.assertEqual(
            settings.voice_prompt_override, DEFAULT_VOICE_REPLY_PROMPT
        )
        self.assertEqual(
            settings.voice_polish_prompt_override,
            DEFAULT_TTS_PREPARATION_PROMPT,
        )
        self.assertEqual(
            settings.transcription_prompt_override,
            DEFAULT_TRANSCRIPTION_PROMPT,
        )
        self.assertEqual(
            saved_payload["text_prompt_override"], DEFAULT_TEXT_REPLY_PROMPT
        )
        self.assertEqual(
            saved_payload["voice_prompt_override"], DEFAULT_VOICE_REPLY_PROMPT
        )
        self.assertEqual(
            saved_payload["voice_polish_prompt_override"],
            DEFAULT_TTS_PREPARATION_PROMPT,
        )
        self.assertEqual(
            saved_payload["transcription_prompt_override"],
            DEFAULT_TRANSCRIPTION_PROMPT,
        )


if __name__ == "__main__":
    unittest.main()
