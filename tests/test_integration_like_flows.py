import tempfile
import unittest
from pathlib import Path

from src.core.orchestrator import Orchestrator
from src.factories.strategy_factory import ModeStrategyFactory
from src.models.settings import AppSettings
from src.services.app_paths import AppPaths
from src.services.history_manager import HistoryManager
from src.storage.json_storage import JsonHistoryRepository


class FakeScreenCaptureAgent:
    def run(self, *, image_path=None, output_path=None):
        return image_path or output_path or "capture.png"


class FakeScreenDiffAgent:
    def run(self, *, previous_path, current_path):
        return previous_path != current_path


class FakeAudioCaptureAgent:
    def run(self, *, transcript):
        return transcript.strip()


class FakeLLMAgent:
    def run(
        self,
        *,
        user_prompt,
        image_paths=None,
        transcript=None,
        match_user_language=False,
    ):
        if transcript:
            return f"live:{transcript}:{len(image_paths or [])}"
        return f"quick:{user_prompt}:{len(image_paths or [])}"

    def prepare_speech_text(self, *, text):
        return text


class FakeOCRAgent:
    def run(self, *, image_path):
        return f"ocr:{image_path}"


class FakeTTSAgent:
    def run(self, *, text, output_path):
        return output_path


class FakeClipboardService:
    def __init__(self):
        self.last_copied_text = ""

    def copy_text(self, text):
        self.last_copied_text = text


class OrchestratorFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        history_repo = JsonHistoryRepository(temp_path / "history.json")
        history_manager = HistoryManager(history_repo, history_limit=5)
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )
        self.clipboard = FakeClipboardService()
        self.orchestrator = Orchestrator(
            settings=settings,
            history_manager=history_manager,
            strategy_factory=ModeStrategyFactory(),
            screen_capture_agent=FakeScreenCaptureAgent(),
            screen_diff_agent=FakeScreenDiffAgent(),
            audio_capture_agent=FakeAudioCaptureAgent(),
            llm_agent=FakeLLMAgent(),
            ocr_agent=FakeOCRAgent(),
            tts_agent=FakeTTSAgent(),
            clipboard_service=self.clipboard,
            audio_dir=temp_path,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_quick_mode_records_history(self) -> None:
        interaction = self.orchestrator.run_mode(
            "quick",
            image_path="sample.png",
            question="Explain this",
        )

        self.assertEqual(interaction.answer, "quick:Explain this:1")
        self.assertEqual(len(self.orchestrator.list_history()), 1)

    def test_ocr_mode_copies_text(self) -> None:
        interaction = self.orchestrator.run_mode("ocr", image_path="sample.png")

        self.assertEqual(interaction.extracted_text, "ocr:sample.png")
        self.assertEqual(self.clipboard.last_copied_text, "ocr:sample.png")

    def test_live_mode_filters_duplicate_frames(self) -> None:
        interaction = self.orchestrator.run_mode(
            "live",
            transcript="Need help",
            image_paths=["a.png", "a.png", "b.png"],
        )

        self.assertEqual(interaction.frame_paths, ["a.png", "b.png"])
        self.assertEqual(interaction.response, "live:Need help:2")


if __name__ == "__main__":
    unittest.main()
