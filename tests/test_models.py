import unittest

from src.exceptions.app_exceptions import ValidationError
from src.models.interactions import QuickInteraction, SessionRecord
from src.models.settings import AppSettings, DEFAULT_TTS_VOICE


class AppSettingsTests(unittest.TestCase):
    def test_from_mapping_builds_valid_settings(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        self.assertEqual(settings.llm_model_name, "model-a")
        self.assertEqual(settings.history_length, 50)

    def test_from_mapping_normalizes_keybinds_to_uppercase(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "live_keybind": "cmd+shift+l",
                "quick_keybind": "ctrl+alt+q",
                "ocr_keybind": "cmd+o",
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        self.assertEqual(settings.live_keybind, "CMD+SHIFT+L")
        self.assertEqual(settings.quick_keybind, "CTRL+ALT+Q")
        self.assertEqual(settings.ocr_keybind, "CMD+O")

    def test_validate_rejects_invalid_threshold(self) -> None:
        with self.assertRaises(ValidationError):
            AppSettings.from_mapping(
                {
                    "llm_base_url": "https://api.example.com/v1",
                    "llm_model_name": "model-a",
                    "tts_base_url": "https://tts.example.com/v1",
                    "screen_change_threshold": 2,
                }
            )

    def test_from_mapping_replaces_invalid_alloy_voice(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "tts_voice_id": "alloy",
            }
        )

        self.assertEqual(settings.tts_voice_id, DEFAULT_TTS_VOICE)


class SessionRecordTests(unittest.TestCase):
    def test_session_rejects_mismatched_mode(self) -> None:
        session = SessionRecord(mode="quick")
        interaction = QuickInteraction(
            mode="ocr",
            question="What is this?",
            answer="Text",
            image_path="capture.png",
        )

        with self.assertRaises(ValidationError):
            session.add_interaction(interaction)


if __name__ == "__main__":
    unittest.main()
