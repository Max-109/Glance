import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

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
        transcriptions_create = Mock(return_value=SimpleNamespace(text="hello there"))
        provider._client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=transcriptions_create)
            ),
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(side_effect=AssertionError))
            ),
        )

        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
            audio_file.write(b"audio")
            audio_file.flush()

            result = provider.transcribe(audio_file.name)

        self.assertEqual(result, "hello there")
        transcriptions_create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
