import tempfile
import unittest
from pathlib import Path

from src.exceptions.app_exceptions import StorageError
from src.models.interactions import LiveInteraction, QuickInteraction, SessionRecord
from src.storage.json_storage import JsonHistoryRepository


class JsonHistoryRepositoryTests(unittest.TestCase):
    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = JsonHistoryRepository(Path(temp_dir) / "history.json")
            session = SessionRecord(mode="quick")
            session.add_interaction(
                QuickInteraction(
                    mode="quick",
                    question="Question",
                    answer="Answer",
                    image_path="capture.png",
                )
            )

            repo.save([session])
            loaded = repo.load()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].interactions[0].summary(), "Quick: Question")

    def test_load_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "history.json"
            file_path.write_text("not-json", encoding="utf-8")
            repo = JsonHistoryRepository(file_path)

            with self.assertRaises(StorageError):
                repo.load()

    def test_live_interaction_round_trip_preserves_recording_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = JsonHistoryRepository(Path(temp_dir) / "history.json")
            session = SessionRecord(mode="live")
            session.add_interaction(
                LiveInteraction(
                    mode="live",
                    recording_path="turn.wav",
                    transcript="hello",
                    response="hi there",
                    speech_path="reply.mp3",
                )
            )

            repo.save([session])
            loaded = repo.load()

        interaction = loaded[0].interactions[0]
        self.assertEqual(interaction.recording_path, "turn.wav")
        self.assertEqual(interaction.speech_path, "reply.mp3")


if __name__ == "__main__":
    unittest.main()
