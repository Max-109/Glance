import tempfile
import unittest
from pathlib import Path

from src.core.orchestrator import Orchestrator
from src.factories.strategy_factory import ModeStrategyFactory
from src.models.settings import AppSettings
from src.services.app_paths import AppPaths
from src.services.history_manager import HistoryManager
from src.services.providers import LiveSpeechReply
from src.storage.json_storage import SessionDirectoryRepository


class FakeScreenCaptureAgent:
    def run(self, *, image_path=None, output_path=None):
        return image_path or output_path or "capture.png"


class FakeScreenDiffAgent:
    def run(self, *, previous_path, current_path):
        return previous_path != current_path


class FakeAudioCaptureAgent:
    def run(self, *, transcript):
        return transcript.strip()


class FakeTranscriptionAgent:
    def run(self, *, audio_path):
        return f"transcribed:{Path(audio_path).name}"


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
        return LiveSpeechReply(
            voice_id="UgBBYS2sOqTuMpoF3BR0",
            text=text,
        )

    def generate_live_speech_reply(self, *, transcript, conversation_history=None):
        return LiveSpeechReply(
            voice_id="UgBBYS2sOqTuMpoF3BR0",
            text=f"live:{transcript}:history={len(conversation_history or [])}",
        )


class FakeOCRAgent:
    def run(self, *, image_path):
        return f"ocr:{image_path}"


class FakeTTSAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def run(self, *, text, output_path, voice_id=None):
        self.calls.append((text, output_path, voice_id))
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
        history_repo = SessionDirectoryRepository(temp_path / "sessions")
        history_manager = HistoryManager(history_repo, history_limit=5)
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )
        self.clipboard = FakeClipboardService()
        self.tts_agent = FakeTTSAgent()
        self.orchestrator = Orchestrator(
            settings=settings,
            history_manager=history_manager,
            strategy_factory=ModeStrategyFactory(),
            screen_capture_agent=FakeScreenCaptureAgent(),
            screen_diff_agent=FakeScreenDiffAgent(),
            audio_capture_agent=FakeAudioCaptureAgent(),
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=FakeLLMAgent(),
            ocr_agent=FakeOCRAgent(),
            tts_agent=self.tts_agent,
            clipboard_service=self.clipboard,
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
        self.assertTrue(interaction.speech_path.endswith(".wav"))
        self.assertEqual(self.tts_agent.calls[0][0], "quick:Explain this:1...")
        self.assertEqual(len(self.orchestrator.list_history()), 1)

    def test_ocr_mode_copies_text(self) -> None:
        interaction = self.orchestrator.run_mode("ocr", image_path="sample.png")

        self.assertEqual(interaction.extracted_text, "ocr:sample.png")
        self.assertEqual(self.clipboard.last_copied_text, "ocr:sample.png")

    def test_live_mode_transcribes_audio_and_generates_reply(self) -> None:
        recording_path = Path(self.temp_dir.name) / "turn.wav"
        recording_path.write_bytes(b"audio")
        interaction = self.orchestrator.run_mode(
            "live", recording_path=str(recording_path)
        )

        self.assertTrue(interaction.recording_path.endswith("turn-001-user.wav"))
        self.assertEqual(interaction.transcript, "transcribed:turn.wav")
        self.assertEqual(interaction.response, "live:transcribed:turn.wav:history=0")
        self.assertTrue(interaction.speech_path.endswith(".wav"))
        self.assertEqual(
            self.tts_agent.calls[0][0],
            "live:transcribed:turn.wav:history=0...",
        )

    def test_live_mode_reuses_same_session_when_provided(self) -> None:
        recording_path = Path(self.temp_dir.name) / "turn.wav"
        recording_path.write_bytes(b"audio")
        session = self.orchestrator.open_session("live")

        self.orchestrator.run_mode(
            "live", session=session, recording_path=str(recording_path)
        )
        second_interaction = self.orchestrator.run_mode(
            "live", session=session, recording_path=str(recording_path)
        )

        history = self.orchestrator.list_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(len(history[0].interactions), 2)
        self.assertEqual(
            second_interaction.response,
            "live:transcribed:turn.wav:history=2",
        )

    def test_live_mode_does_not_reuse_context_across_sessions(self) -> None:
        recording_path = Path(self.temp_dir.name) / "turn.wav"
        recording_path.write_bytes(b"audio")

        first_session = self.orchestrator.open_session("live")
        self.orchestrator.run_mode(
            "live", session=first_session, recording_path=str(recording_path)
        )

        second_session = self.orchestrator.open_session("live")
        interaction = self.orchestrator.run_mode(
            "live", session=second_session, recording_path=str(recording_path)
        )

        self.assertEqual(interaction.response, "live:transcribed:turn.wav:history=0")


if __name__ == "__main__":
    unittest.main()
