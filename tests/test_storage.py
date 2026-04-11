import tempfile
import unittest
from pathlib import Path

from src.exceptions.app_exceptions import StorageError
from src.models.interactions import QuickInteraction, SessionRecord
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


if __name__ == "__main__":
    unittest.main()
