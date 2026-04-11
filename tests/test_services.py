import unittest
from pathlib import Path

from src.agents.audio_capture_agent import AudioCaptureAgent
from src.agents.llm_agent import LLMAgent
from src.agents.ocr_agent import OCRAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.agents.screen_diff_agent import ScreenDiffAgent
from src.agents.tts_agent import TTSAgent
from src.exceptions.app_exceptions import ValidationError
from src.factories.strategy_factory import ModeStrategyFactory
from src.services.clipboard import ClipboardService
from src.strategies.live_strategy import LiveStrategy
from src.strategies.ocr_strategy import OCRStrategy
from src.strategies.quick_strategy import QuickStrategy


class DummyProvider:
    def generate_reply(self, **kwargs):
        return "ok"

    def prepare_speech_text(self, text: str) -> str:
        return text

    def extract_text(self, image_path: str) -> str:
        return image_path

    def synthesize(self, text: str, output_path: Path) -> str:
        return str(output_path)


class ModeStrategyFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        provider = DummyProvider()
        self.factory = ModeStrategyFactory()
        self.dependencies = {
            "screen_capture_agent": ScreenCaptureAgent(),
            "screen_diff_agent": ScreenDiffAgent(),
            "audio_capture_agent": AudioCaptureAgent(),
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


if __name__ == "__main__":
    unittest.main()
