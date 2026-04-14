import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agents.audio_capture_agent import AudioCaptureAgent
from src.agents.llm_agent import LLMAgent
from src.agents.ocr_agent import OCRAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.agents.screen_diff_agent import ScreenDiffAgent
from src.agents.tts_agent import TTSAgent
from src.agents.transcription_agent import TranscriptionAgent
from src.exceptions.app_exceptions import ValidationError
from src.factories.strategy_factory import ModeStrategyFactory
from src.services.clipboard import ClipboardService
from src.services.providers import (
    LiveSpeechReply,
    _detect_audio_format,
    _normalize_synthesized_audio,
    _speech_response_format,
    _wrap_pcm_file_as_wav,
)
from src.strategies.live_strategy import LiveStrategy
from src.strategies.ocr_strategy import OCRStrategy
from src.strategies.quick_strategy import QuickStrategy


class DummyProvider:
    def generate_reply(self, **kwargs):
        return "ok"

    def prepare_speech_text(self, text: str) -> LiveSpeechReply:
        return LiveSpeechReply(
            voice_id="UgBBYS2sOqTuMpoF3BR0",
            text=text,
        )

    def generate_live_speech_reply(
        self,
        *,
        transcript: str,
        conversation_history=None,
    ) -> LiveSpeechReply:
        return LiveSpeechReply(
            voice_id="UgBBYS2sOqTuMpoF3BR0",
            text=transcript,
        )

    def extract_text(self, image_path: str) -> str:
        return image_path

    def transcribe(self, audio_path: str) -> str:
        return audio_path

    def synthesize(
        self, text: str, output_path: Path, *, voice_id: str | None = None
    ) -> str:
        return str(output_path)


class ModeStrategyFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        provider = DummyProvider()
        self.factory = ModeStrategyFactory()
        self.dependencies = {
            "screen_capture_agent": ScreenCaptureAgent(),
            "screen_diff_agent": ScreenDiffAgent(),
            "audio_capture_agent": AudioCaptureAgent(),
            "transcription_agent": TranscriptionAgent(provider),
            "llm_agent": LLMAgent(provider),
            "ocr_agent": OCRAgent(provider),
            "tts_agent": TTSAgent(provider),
            "clipboard_service": ClipboardService(),
            "audio_dir": Path("."),
        }

    def test_create_returns_quick_strategy(self) -> None:
        strategy = self.factory.create(mode="quick", **self.dependencies)
        self.assertIsInstance(strategy, QuickStrategy)

    def test_create_returns_ocr_strategy(self) -> None:
        strategy = self.factory.create(mode="ocr", **self.dependencies)
        self.assertIsInstance(strategy, OCRStrategy)

    def test_create_returns_live_strategy(self) -> None:
        strategy = self.factory.create(mode="live", **self.dependencies)
        self.assertIsInstance(strategy, LiveStrategy)

    def test_create_rejects_unknown_mode(self) -> None:
        with self.assertRaises(ValidationError):
            self.factory.create(mode="bad-mode", **self.dependencies)


class SpeechProviderFormatTests(unittest.TestCase):
    def test_speech_response_format_matches_output_suffix(self) -> None:
        self.assertEqual(_speech_response_format(Path("reply.wav")), "wav")
        self.assertEqual(_speech_response_format(Path("reply.mp3")), "mp3")
        self.assertEqual(_speech_response_format(Path("reply")), "mp3")

    def test_detect_audio_format_recognizes_wav_and_mp3_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "reply.wav"
            mp3_path = Path(temp_dir) / "reply.mp3"
            wav_path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
            mp3_path.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

            self.assertEqual(_detect_audio_format(wav_path), "wav")
            self.assertEqual(_detect_audio_format(mp3_path), "mp3")

    def test_normalize_synthesized_audio_renames_mismatched_mp3_when_wav_conversion_unavailable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "reply.wav"
            output_path.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

            with patch(
                "src.services.providers._convert_audio_to_wav", return_value=None
            ):
                normalized_path = _normalize_synthesized_audio(output_path, "wav")

            self.assertEqual(normalized_path.suffix, ".mp3")
            self.assertTrue(normalized_path.exists())
            self.assertFalse(output_path.exists())

    def test_normalize_synthesized_audio_wraps_headerless_pcm_when_wav_requested(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "reply.wav"
            output_path.write_bytes((b"\x00\x00\x01\x00") * 128)

            normalized_path = _normalize_synthesized_audio(
                output_path,
                "wav",
                content_type="audio/wav",
            )

            self.assertEqual(normalized_path, output_path)
            self.assertEqual(_detect_audio_format(normalized_path), "wav")

    def test_wrap_pcm_file_as_wav_creates_riff_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "reply.wav"
            output_path.write_bytes((b"\x00\x00\x01\x00") * 64)

            wrapped_path = _wrap_pcm_file_as_wav(output_path)

            self.assertEqual(wrapped_path.read_bytes()[:4], b"RIFF")


if __name__ == "__main__":
    unittest.main()
