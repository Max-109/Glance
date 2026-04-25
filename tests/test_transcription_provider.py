import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.models.settings import AppSettings
from src.services.providers import NagaTranscriptionProvider


class TranscriptionProviderTests(unittest.TestCase):
    def test_whisper_model_uses_audio_transcriptions_api(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "transcription_model_name": "whisper-large-v3-turbo",
            },
            validate=False,
        )
        provider = NagaTranscriptionProvider.__new__(NagaTranscriptionProvider)
        provider._settings = settings
        transcriptions_create = Mock(
            return_value=SimpleNamespace(text="hello there")
        )
        provider._client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=transcriptions_create)
            ),
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=Mock(side_effect=AssertionError)
                )
            ),
        )

        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
            audio_file.write(b"audio")
            audio_file.flush()

            with patch(
                "src.services.providers._prepare_audio_upload_path",
                return_value=(Path(audio_file.name), lambda: None),
            ):
                result = provider.transcribe(audio_file.name)

        self.assertEqual(result, "hello there")
        transcriptions_create.assert_called_once()

    def test_whisper_model_prefers_mp3_upload_when_available(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "transcription_model_name": "whisper-large-v3-turbo",
            },
            validate=False,
        )
        provider = NagaTranscriptionProvider.__new__(NagaTranscriptionProvider)
        provider._settings = settings
        transcriptions_create = Mock(
            return_value=SimpleNamespace(text="hello there")
        )
        provider._client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=transcriptions_create)
            ),
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=Mock(side_effect=AssertionError)
                )
            ),
        )

        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as wav_file,
            tempfile.NamedTemporaryFile(suffix=".mp3") as mp3_file,
        ):
            wav_file.write(b"wav-audio")
            wav_file.flush()
            mp3_file.write(b"mp3-audio")
            mp3_file.flush()

            with patch(
                "src.services.providers._prepare_audio_upload_path",
                return_value=(Path(mp3_file.name), lambda: None),
            ):
                result = provider.transcribe(wav_file.name)

        self.assertEqual(result, "hello there")
        uploaded_file = transcriptions_create.call_args.kwargs["file"]
        self.assertTrue(uploaded_file.name.endswith(".mp3"))

    def test_chat_transcription_uses_mp3_input_audio_format_when_available(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "transcription_model_name": "gemini-3.1-flash-lite-preview",
            },
            validate=False,
        )
        provider = NagaTranscriptionProvider.__new__(NagaTranscriptionProvider)
        provider._settings = settings
        completions_create = Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="hello there")
                    )
                ]
            )
        )
        provider._client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(
                    create=Mock(side_effect=AssertionError)
                )
            ),
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=completions_create)
            ),
        )

        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as wav_file,
            tempfile.NamedTemporaryFile(suffix=".mp3") as mp3_file,
        ):
            wav_file.write(b"wav-audio")
            wav_file.flush()
            mp3_file.write(b"mp3-audio")
            mp3_file.flush()

            with patch(
                "src.services.providers._prepare_audio_upload_path",
                return_value=(Path(mp3_file.name), lambda: None),
            ):
                result = provider.transcribe(wav_file.name)

        self.assertEqual(result, "hello there")
        audio_part = completions_create.call_args.kwargs["messages"][1][
            "content"
        ][1]
        self.assertEqual(audio_part["input_audio"]["format"], "mp3")


if __name__ == "__main__":
    unittest.main()
