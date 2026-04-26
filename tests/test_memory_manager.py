import json
import tempfile
import time
import unittest
from pathlib import Path

from src.exceptions.app_exceptions import ValidationError
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

    def test_change_memory_partially_updates_existing_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory = manager.add_memory(
                title="Original title",
                description="Original note",
                intent="Original intent",
                source_text="Original source",
            )
            created_at = memory.created_at
            time.sleep(0.001)

            result = manager.change_memory(
                memory_id=memory.entity_id,
                description="Updated note",
            )
            saved = manager.list_memories()[0]

        self.assertEqual(result["status"], "updated")
        self.assertEqual(saved.title, "Original title")
        self.assertEqual(saved.description, "Updated note")
        self.assertEqual(saved.intent, "Original intent")
        self.assertEqual(saved.source_text, "Original source")
        self.assertEqual(saved.created_at, created_at)
        self.assertGreater(saved.updated_at, created_at)

    def test_change_memory_unknown_id_raises_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(title="First", description="First note")

            with self.assertRaisesRegex(
                ValidationError, "Memory was not found"
            ):
                manager.change_memory(
                    memory_id="missing",
                    description="Updated note",
                )

    def test_change_memory_query_updates_single_clear_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(
                title="Billing export",
                description="Remember CSV export for invoices.",
            )
            manager.add_memory(
                title="Onboarding",
                description="Add a first-run checklist.",
            )

            result = manager.change_memory(
                query="onboarding",
                intent="Help new users start faster.",
            )
            saved = manager.search_memories("onboarding")["matches"][0]

        self.assertEqual(result["status"], "updated")
        self.assertEqual(saved["title"], "Onboarding")
        self.assertEqual(saved["intent"], "Help new users start faster.")

    def test_change_memory_ambiguous_query_returns_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            manager.add_memory(
                title="Billing export",
                description="Remember billing CSV export.",
            )
            manager.add_memory(
                title="Billing reminder",
                description="Remember billing email follow-up.",
            )

            result = manager.change_memory(
                query="billing",
                description="Updated billing note.",
            )
            memories = manager.list_memories()

        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(
            [memory.description for memory in memories],
            [
                "Remember billing email follow-up.",
                "Remember billing CSV export.",
            ],
        )

    def test_change_memory_requires_update_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory = manager.add_memory(
                title="First", description="First note"
            )

            with self.assertRaisesRegex(
                ValidationError, "Tell me what to change"
            ):
                manager.change_memory(memory_id=memory.entity_id)


if __name__ == "__main__":
    unittest.main()
