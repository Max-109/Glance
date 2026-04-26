import json
import tempfile
import unittest
from pathlib import Path

from src.services.memory_manager import MemoryManager


class MemoryManagerTests(unittest.TestCase):
    def test_add_update_and_delete_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_file = Path(temp_dir) / "memories.json"
            manager = MemoryManager(memory_file)

            memory = manager.add_memory(
                title="New feature",
                description="Remember to add the new feature.",
                intent="Add it to the project.",
                source_text="I need to remember this.",
            )
            manager.update_memory(
                memory.entity_id,
                title="Updated feature",
                description="Remember to add the updated feature.",
                intent="Add it after the UI work.",
            )
            saved = MemoryManager(memory_file).list_memories()[0]
            manager.delete_memory(memory.entity_id)
            payload = json.loads(memory_file.read_text(encoding="utf-8"))

        self.assertEqual(saved.title, "Updated feature")
        self.assertEqual(saved.intent, "Add it after the UI work.")
        self.assertEqual(payload["memories"], [])

    def test_newest_memories_are_listed_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(title="First", description="First note")
            manager.add_memory(title="Second", description="Second note")

            titles = [
                memory.title for memory in manager.list_memories()
            ]

        self.assertEqual(titles, ["Second", "First"])

    def test_search_ranks_exact_title_match_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(
                title="Project cleanup",
                description="Remember to clean stale docs.",
            )
            manager.add_memory(
                title="Onboarding checklist",
                description="Add an intro flow later.",
            )

            result = manager.search_memories("onboarding checklist")

        self.assertEqual(result["status"], "matches")
        self.assertEqual(result["matches"][0]["title"], "Onboarding checklist")

    def test_search_matches_intent_description_and_source_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(
                title="Plain title",
                description="Need a better billing export.",
                intent="Fix invoices after settings work.",
                source_text="Please remind me about receipts.",
            )

            intent_result = manager.search_memories("invoices")
            description_result = manager.search_memories("billing export")
            source_result = manager.search_memories("receipts")

        self.assertEqual(intent_result["matches"][0]["title"], "Plain title")
        self.assertEqual(
            description_result["matches"][0]["title"], "Plain title"
        )
        self.assertEqual(source_result["matches"][0]["title"], "Plain title")

    def test_empty_query_returns_recent_titles_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(title="First", description="First note")
            manager.add_memory(title="Second", description="Second note")

            result = manager.search_memories("")

        self.assertEqual(result["status"], "titles")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["available_titles"], ["Second", "First"])

    def test_no_search_match_returns_recent_titles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(title="First", description="First note")

            result = manager.search_memories("unrelated spaceship")

        self.assertEqual(result["status"], "none")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["available_titles"], ["First"])


if __name__ == "__main__":
    unittest.main()
