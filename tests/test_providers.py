import unittest
from unittest.mock import patch

from src.models.settings import AppSettings
from src.services.providers import (
    NagaTranscriptionProvider,
    OpenAICompatibleProvider,
    _extract_text_content,
)


class ContentExtractionTests(unittest.TestCase):
    def test_extract_text_content_handles_plain_string(self) -> None:
        self.assertEqual(_extract_text_content("hello"), "hello")

    def test_extract_text_content_handles_part_list(self) -> None:
        content = [
            {"type": "text", "text": "hello"},
            {"type": "text", "text": {"value": "world"}},
        ]

        self.assertEqual(_extract_text_content(content), "hello\nworld")


class ProviderReasoningToggleTests(unittest.TestCase):
    def test_llm_reasoning_kwargs_are_omitted_when_toggle_is_off(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_api_key": "secret",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "llm_reasoning_enabled": False,
                "llm_reasoning": "high",
            }
        )

        with patch.object(
            OpenAICompatibleProvider, "_build_client", return_value=object()
        ):
            provider = OpenAICompatibleProvider(settings)

        self.assertEqual(provider._llm_reasoning_kwargs(), {})
        self.assertEqual(provider._llm_reasoning_label(), "off")

    def test_transcription_reasoning_kwargs_are_omitted_when_toggle_is_off(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "transcription_api_key": "secret",
                "transcription_reasoning_enabled": False,
                "transcription_reasoning": "high",
            }
        )

        with patch.object(
            NagaTranscriptionProvider, "_build_client", return_value=object()
        ):
            provider = NagaTranscriptionProvider(settings)

        self.assertEqual(provider._transcription_reasoning_kwargs(), {})
        self.assertEqual(provider._transcription_reasoning_label(), "off")


if __name__ == "__main__":
    unittest.main()
