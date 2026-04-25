import tempfile
import unittest
from pathlib import Path

from src.exceptions.app_exceptions import StorageError
from src.models.interactions import (
    LiveInteraction,
    QuickInteraction,
    SessionRecord,
    ToolCallRecord,
)
from src.storage.json_storage import SessionDirectoryRepository


class SessionDirectoryRepositoryTests(unittest.TestCase):
    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo = SessionDirectoryRepository(temp_path / "sessions")
            image_path = temp_path / "capture.png"
            image_path.write_bytes(b"image")
            session = SessionRecord(mode="quick")
            session.add_interaction(
                QuickInteraction(
                    mode="quick",
                    question="Question",
                    answer="Answer",
                    image_path=str(image_path),
                )
            )

            repo.save([session])
            loaded = repo.load()
            session_dirs = list((temp_path / "sessions").iterdir())

            self.assertEqual(len(loaded), 1)
            self.assertEqual(
                loaded[0].interactions[0].summary(), "Legacy: Question"
            )
            self.assertEqual(len(session_dirs), 1)
            self.assertTrue((session_dirs[0] / "session.json").exists())
            self.assertTrue((session_dirs[0] / "conversation.md").exists())
            self.assertTrue(
                Path(loaded[0].interactions[0].image_path).exists()
            )

    def test_load_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "sessions" / "bad-session"
            session_dir.mkdir(parents=True)
            (session_dir / "session.json").write_text(
                "not-json", encoding="utf-8"
            )
            repo = SessionDirectoryRepository(Path(temp_dir) / "sessions")

            with self.assertRaises(StorageError):
                repo.load()

    def test_live_interaction_round_trip_preserves_recording_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo = SessionDirectoryRepository(temp_path / "sessions")
            recording_path = temp_path / "turn.wav"
            speech_path = temp_path / "reply.mp3"
            recording_path.write_bytes(b"audio")
            speech_path.write_bytes(b"speech")
            session = SessionRecord(mode="live")
            session.add_interaction(
                LiveInteraction(
                    mode="live",
                    recording_path=str(recording_path),
                    transcript="hello",
                    response="hi there",
                    speech_path=str(speech_path),
                )
            )

            repo.save([session])
            loaded = repo.load()
            interaction = loaded[0].interactions[0]
            self.assertTrue(
                interaction.recording_path.endswith("turn-001-user.wav")
            )
            self.assertTrue(
                interaction.speech_path.endswith("turn-001-assistant.mp3")
            )
            self.assertTrue(Path(interaction.recording_path).exists())
            self.assertTrue(Path(interaction.speech_path).exists())

    def test_live_tool_calls_are_saved_in_session_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo = SessionDirectoryRepository(temp_path / "sessions")
            recording_path = temp_path / "turn.wav"
            speech_path = temp_path / "reply.wav"
            result_path = temp_path / "result.md"
            artifact_path = temp_path / "screen.png"
            recording_path.write_bytes(b"audio")
            speech_path.write_bytes(b"speech")
            result_path.write_text("tool result", encoding="utf-8")
            artifact_path.write_bytes(b"png")
            session = SessionRecord(mode="live")
            session.add_interaction(
                LiveInteraction(
                    mode="live",
                    recording_path=str(recording_path),
                    transcript="what is on screen",
                    response="There is code on screen.",
                    speech_path=str(speech_path),
                    tool_calls=[
                        ToolCallRecord(
                            call_id="call-1",
                            tool_name="take_screenshot",
                            status="success",
                            arguments_summary="screen context",
                            result_preview="Screenshot captured.",
                            result_path=str(result_path),
                            artifact_paths=[str(artifact_path)],
                        )
                    ],
                )
            )

            repo.save([session])
            loaded = repo.load()
            session_dir = next((temp_path / "sessions").iterdir())
            saved_payload = (session_dir / "session.json").read_text(
                encoding="utf-8"
            )
            markdown = (session_dir / "conversation.md").read_text(
                encoding="utf-8"
            )
            loaded_tool_call = loaded[0].interactions[0].tool_calls[0]

            self.assertIn('"tool_calls"', saved_payload)
            self.assertIn("take_screenshot", saved_payload)
            self.assertIn("Tool calls:", markdown)
            self.assertIn("take_screenshot: success", markdown)
            self.assertTrue(Path(loaded_tool_call.result_path).exists())
            self.assertTrue(Path(loaded_tool_call.artifact_paths[0]).exists())


if __name__ == "__main__":
    unittest.main()
