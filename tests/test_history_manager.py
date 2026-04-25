import tempfile
import unittest
from pathlib import Path

from src.models.interactions import QuickInteraction, SessionRecord
from src.services.history_manager import HistoryManager
from src.storage.json_storage import SessionDirectoryRepository


def build_session(index: int) -> SessionRecord:
    session = SessionRecord(mode="quick")
    session.add_interaction(
        QuickInteraction(
            mode="quick",
            question=f"Question {index}",
            answer=f"Answer {index}",
            image_path=f"capture-{index}.png",
        )
    )
    return session


class HistoryManagerTests(unittest.TestCase):
    def test_retention_trims_oldest_sessions_on_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = SessionDirectoryRepository(
                Path(temp_dir) / "sessions"
            )
            sessions = [build_session(index) for index in range(4)]
            repository.save(sessions)

            manager = HistoryManager(repository, history_limit=2)

            retained_ids = [
                session.entity_id for session in manager.list_sessions()
            ]
            self.assertEqual(
                retained_ids, [session.entity_id for session in sessions[-2:]]
            )
            self.assertEqual(len(repository.load()), 2)

    def test_retention_can_be_paused(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = SessionDirectoryRepository(
                Path(temp_dir) / "sessions"
            )
            sessions = [build_session(index) for index in range(4)]
            repository.save(sessions)

            manager = HistoryManager(
                repository,
                history_limit=2,
                retention_enabled=False,
            )

            self.assertEqual(len(manager.list_sessions()), 4)
            self.assertEqual(len(repository.load()), 4)

    def test_enabling_policy_cleans_existing_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = SessionDirectoryRepository(
                Path(temp_dir) / "sessions"
            )
            sessions = [build_session(index) for index in range(5)]
            repository.save(sessions)
            manager = HistoryManager(
                repository,
                history_limit=5,
                retention_enabled=False,
            )

            manager.set_history_policy(history_limit=3, retention_enabled=True)

            retained_ids = [
                session.entity_id for session in manager.list_sessions()
            ]
            self.assertEqual(
                retained_ids, [session.entity_id for session in sessions[-3:]]
            )
            self.assertEqual(len(repository.load()), 3)


if __name__ == "__main__":
    unittest.main()
