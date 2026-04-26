import unittest

from src.exceptions.app_exceptions import ValidationError
from src.models.interactions import QuickInteraction, SessionRecord
from src.models.prompt_defaults import (
    DEFAULT_TEXT_REPLY_PROMPT,
    DEFAULT_TRANSCRIPTION_PROMPT,
    DEFAULT_TTS_PREPARATION_PROMPT,
    DEFAULT_VOICE_REPLY_PROMPT,
)
from src.models.settings import (
    AppSettings,
    DEFAULT_ACCENT_COLOR,
    DEFAULT_ELECTRON_WINDOW_HEIGHT,
    DEFAULT_ELECTRON_WINDOW_WIDTH,
    DEFAULT_TTS_VOICE,
    MIN_ELECTRON_WINDOW_HEIGHT,
    MIN_ELECTRON_WINDOW_WIDTH,
)


class AppSettingsTests(unittest.TestCase):
    def test_from_mapping_builds_valid_settings(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "transcription_base_url": "https://transcribe.example.com/v1",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        self.assertEqual(settings.llm_model_name, "model-a")
        self.assertEqual(
            settings.transcription_base_url,
            "https://transcribe.example.com/v1",
        )
        self.assertEqual(settings.history_length, 50)
        self.assertTrue(settings.history_retention_enabled)
        self.assertFalse(settings.tools_enabled)
        self.assertEqual(settings.tool_take_screenshot_policy, "allow")
        self.assertEqual(settings.tool_ocr_policy, "allow")
        self.assertEqual(settings.tool_web_search_policy, "allow")
        self.assertEqual(settings.tool_web_fetch_policy, "allow")
        self.assertEqual(settings.tool_add_memory_policy, "allow")
        self.assertEqual(settings.tool_read_memory_policy, "allow")
        self.assertEqual(settings.tool_change_memory_policy, "allow")

    def test_from_mapping_loads_tool_settings(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "tools_enabled": "true",
                "tool_take_screenshot_policy": "deny",
                "tool_ocr_policy": "deny",
                "tool_web_search_policy": "allow",
                "tool_web_fetch_policy": "deny",
                "tool_add_memory_policy": "deny",
                "tool_read_memory_policy": "deny",
                "tool_change_memory_policy": "deny",
            }
        )

        self.assertTrue(settings.tools_enabled)
        self.assertEqual(settings.tool_take_screenshot_policy, "deny")
        self.assertEqual(settings.tool_ocr_policy, "deny")
        self.assertEqual(settings.tool_web_search_policy, "allow")
        self.assertEqual(settings.tool_web_fetch_policy, "deny")
        self.assertEqual(settings.tool_add_memory_policy, "deny")
        self.assertEqual(settings.tool_read_memory_policy, "deny")
        self.assertEqual(settings.tool_change_memory_policy, "deny")

    def test_from_mapping_ignores_removed_tool_limit_settings(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "max_tool_steps_per_turn": 99,
                "max_tool_calls_per_turn": 0,
            }
        )

        self.assertFalse(hasattr(settings, "max_tool_steps_per_turn"))
        self.assertFalse(hasattr(settings, "max_tool_calls_per_turn"))

    def test_from_mapping_uses_transcription_defaults_when_values_missing(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        self.assertEqual(settings.transcription_base_url, "https://api.naga.ac/v1")
        self.assertEqual(settings.transcription_api_key, "")

    def test_default_audio_detection_is_balanced(self) -> None:
        self.assertEqual(AppSettings().audio_vad_threshold, 0.5)
        self.assertEqual(AppSettings().audio_endpoint_patience, "balanced")

    def test_from_mapping_ignores_removed_audio_threshold_settings(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "audio_turn_detection_mode": "threshold",
                "audio_activation_threshold": 0,
                "audio_silence_timeout_enabled": "false",
                "audio_silence_seconds": 0.1,
            }
        )

        self.assertFalse(hasattr(settings, "audio_turn_detection_mode"))
        self.assertFalse(hasattr(settings, "audio_activation_threshold"))
        self.assertFalse(hasattr(settings, "audio_silence_timeout_enabled"))
        self.assertFalse(hasattr(settings, "audio_silence_seconds"))
        self.assertNotIn("audio_turn_detection_mode", settings.to_dict())
        self.assertNotIn("audio_activation_threshold", settings.to_dict())
        self.assertNotIn("audio_silence_timeout_enabled", settings.to_dict())
        self.assertNotIn("audio_silence_seconds", settings.to_dict())

    def test_from_mapping_normalizes_keybinds_to_uppercase(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "live_keybind": "cmd+shift+l",
                "quick_keybind": "ctrl+alt+q",
                "ocr_keybind": "cmd+o",
                "open_glance_keybind": "cmd+shift+g",
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        self.assertEqual(settings.live_keybind, "CMD+SHIFT+L")
        self.assertEqual(settings.ocr_keybind, "CMD+O")
        self.assertEqual(settings.open_glance_keybind, "CMD+SHIFT+G")
        self.assertFalse(hasattr(settings, "quick_keybind"))
        self.assertNotIn("quick_keybind", settings.to_dict())

    def test_from_mapping_migrates_open_menu_keybind(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "open_menu_keybind": "cmd+alt+g",
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        self.assertEqual(settings.open_glance_keybind, "CMD+ALT+G")
        self.assertFalse(hasattr(settings, "open_menu_keybind"))
        self.assertNotIn("open_menu_keybind", settings.to_dict())

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

    def test_validate_rejects_invalid_audio_vad_settings(self) -> None:
        with self.assertRaises(ValidationError):
            AppSettings.from_mapping(
                {
                    "llm_base_url": "https://api.example.com/v1",
                    "tts_base_url": "https://tts.example.com/v1",
                    "audio_vad_threshold": 2,
                }
            )
        with self.assertRaises(ValidationError):
            AppSettings(
                llm_base_url="https://api.example.com/v1",
                tts_base_url="https://tts.example.com/v1",
                audio_endpoint_patience="rushed",
            ).validate()

    def test_validate_rejects_negative_audio_preroll(self) -> None:
        with self.assertRaises(ValidationError):
            AppSettings.from_mapping(
                {
                    "llm_base_url": "https://api.example.com/v1",
                    "llm_model_name": "model-a",
                    "tts_base_url": "https://tts.example.com/v1",
                    "audio_preroll_seconds": -0.2,
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

    def test_from_mapping_normalizes_curated_voice_name_to_voice_id(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "tts_voice_id": "Hope",
            }
        )

        self.assertEqual(settings.tts_voice_id, "tnSpp4vdxKPjI9w0GnoV")

    def test_from_mapping_normalizes_legacy_instant_reasoning_to_minimal(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "llm_reasoning": "instant",
            }
        )

        self.assertEqual(settings.llm_reasoning, "minimal")

    def test_from_mapping_coerces_reasoning_toggle_and_accent_color(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "llm_reasoning_enabled": "false",
                "accent_color": "F0B100",
            }
        )

        self.assertFalse(settings.llm_reasoning_enabled)
        self.assertEqual(settings.accent_color, DEFAULT_ACCENT_COLOR)

    def test_from_mapping_coerces_audio_timing_toggles(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "audio_wait_for_speech_enabled": False,
                "audio_max_turn_length_enabled": "0",
                "audio_preroll_enabled": True,
            }
        )

        self.assertFalse(settings.audio_wait_for_speech_enabled)
        self.assertFalse(settings.audio_max_turn_length_enabled)
        self.assertTrue(settings.audio_preroll_enabled)

    def test_from_mapping_persists_electron_window_size(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "electron_window_width": 1180,
                "electron_window_height": 820,
            }
        )

        self.assertEqual(settings.electron_window_width, 1180)
        self.assertEqual(settings.electron_window_height, 820)

    def test_from_mapping_clamps_tiny_electron_window_size(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "electron_window_width": 100,
                "electron_window_height": 100,
            }
        )

        self.assertEqual(settings.electron_window_width, MIN_ELECTRON_WINDOW_WIDTH)
        self.assertEqual(settings.electron_window_height, MIN_ELECTRON_WINDOW_HEIGHT)

    def test_from_mapping_uses_default_electron_window_size_for_bad_values(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "electron_window_width": "wide",
                "electron_window_height": None,
            }
        )

        self.assertEqual(settings.electron_window_width, DEFAULT_ELECTRON_WINDOW_WIDTH)
        self.assertEqual(
            settings.electron_window_height, DEFAULT_ELECTRON_WINDOW_HEIGHT
        )

    def test_from_mapping_loads_prompt_overrides(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "system_prompt_override": "Be crisp.",
                "text_prompt_override": "Text mode custom prompt.",
                "voice_prompt_override": "Voice mode custom prompt.",
                "voice_polish_prompt_override": "Voice polish custom prompt.",
                "transcription_prompt_override": ("Transcription custom prompt."),
            }
        )

        self.assertEqual(settings.system_prompt_override, "Be crisp.")
        self.assertEqual(settings.text_prompt_override, "Text mode custom prompt.")
        self.assertEqual(settings.voice_prompt_override, "Voice mode custom prompt.")
        self.assertEqual(
            settings.voice_polish_prompt_override,
            "Voice polish custom prompt.",
        )
        self.assertEqual(
            settings.transcription_prompt_override,
            "Transcription custom prompt.",
        )

    def test_from_mapping_normalizes_blank_prompt_fields_back_to_defaults(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "text_prompt_override": "   ",
                "voice_prompt_override": "",
                "voice_polish_prompt_override": "\n\n",
                "transcription_prompt_override": "  ",
            }
        )

        self.assertEqual(settings.text_prompt_override, DEFAULT_TEXT_REPLY_PROMPT)
        self.assertEqual(settings.voice_prompt_override, DEFAULT_VOICE_REPLY_PROMPT)
        self.assertEqual(
            settings.voice_polish_prompt_override,
            DEFAULT_TTS_PREPARATION_PROMPT,
        )
        self.assertEqual(
            settings.transcription_prompt_override,
            DEFAULT_TRANSCRIPTION_PROMPT,
        )

    def test_validate_rejects_invalid_accent_color(self) -> None:
        with self.assertRaises(ValidationError):
            AppSettings.from_mapping(
                {
                    "llm_base_url": "https://api.example.com/v1",
                    "llm_model_name": "model-a",
                    "tts_base_url": "https://tts.example.com/v1",
                    "accent_color": "#12zz34",
                }
            )


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
