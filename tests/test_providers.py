import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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


class ProviderAudioUploadTests(unittest.TestCase):
    def test_multimodal_live_uses_mp3_audio_format_when_available(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "tts_voice_id": "UgBBYS2sOqTuMpoF3BR0",
            },
            validate=False,
        )
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider._settings = settings
        completions_create = unittest.mock.Mock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="hello there"))]
            )
        )
        provider._client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=completions_create))
        )

        with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file, tempfile.NamedTemporaryFile(
            suffix=".mp3"
        ) as mp3_file:
            wav_file.write(b"wav-audio")
            wav_file.flush()
            mp3_file.write(b"mp3-audio")
            mp3_file.flush()

            with patch(
                "src.services.providers._prepare_audio_upload_path",
                return_value=(Path(mp3_file.name), lambda: None),
            ):
                reply = provider.generate_live_speech_reply_from_audio(
                    audio_path=wav_file.name,
                )

        self.assertEqual(reply.text, "hello there")
        audio_part = completions_create.call_args.kwargs["messages"][1]["content"][1]
        self.assertEqual(audio_part["input_audio"]["format"], "mp3")


if __name__ == "__main__":
    unittest.main()
