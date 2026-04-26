import tempfile
import unittest
from pathlib import Path

from src.models.settings import AppSettings
from src.services.memory_manager import MemoryManager
from src.tools import runtime as runtime_module
from src.tools import (
    RuntimeToolRegistry,
    ToolCallRequest,
    ToolExecutor,
    short_site_name,
)
from src.services.ocr import OCRService


class FakeScreenCaptureAgent:
    def __init__(self) -> None:
        self.called = False

    def run(self, *, image_path=None, output_path=None):
        self.called = True
        path = Path(output_path or image_path or "capture.png")
        path.write_bytes(b"fake-png")
        return str(path)


class FakeOCRAgent:
    def __init__(self, text: str = "Visible text") -> None:
        self.text = text
        self.image_paths: list[str] = []
        self.instructions: list[str] = []

    def run(self, *, image_path, instruction=""):
        self.image_paths.append(image_path)
        self.instructions.append(instruction)
        return self.text


class FakeClipboardService:
    def __init__(self) -> None:
        self.last_copied_text = ""

    def copy_text(self, text: str) -> None:
        self.last_copied_text = text


def _tool_settings(**overrides) -> AppSettings:
    values = {
        "llm_base_url": "https://api.example.com/v1",
        "llm_model_name": "model-a",
        "tts_base_url": "https://tts.example.com/v1",
        "tools_enabled": True,
    }
    values.update(overrides)
    return AppSettings.from_mapping(values)


class RuntimeToolTests(unittest.TestCase):
    def test_screenshot_tool_saves_artifact_and_returns_image_context(
        self,
    ) -> None:
        screen_capture_agent = FakeScreenCaptureAgent()
        registry = RuntimeToolRegistry(
            _tool_settings(),
            screen_capture_agent=screen_capture_agent,
        )
        executor = ToolExecutor(registry)

        record, result = executor.execute(
            ToolCallRequest(
                call_id="call-1",
                name="take_screenshot",
                arguments={"reason": "read code"},
            )
        )

        self.assertTrue(screen_capture_agent.called)
        self.assertEqual(record.status, "success")
        self.assertEqual(record.tool_name, "take_screenshot")
        self.assertEqual(len(result.images), 1)
        self.assertTrue(Path(result.images[0].path).exists())
        self.assertEqual(result.artifact_paths, [result.images[0].path])
        self.assertEqual(result.metadata, {"reason": "read code"})

    def test_short_site_name_prefers_human_source_names(self) -> None:
        self.assertEqual(
            short_site_name("https://platform.openai.com/docs"), "OpenAI"
        )
        self.assertEqual(
            short_site_name("https://weather.com/weather/today"), "Weather.com"
        )
        self.assertEqual(
            short_site_name(
                "https://very-long-dashed-source-name.example.com/page"
            ),
            "",
        )

    def test_web_search_writes_result_artifact(self) -> None:
        original_read_url = runtime_module._read_url
        try:
            runtime_module._read_url = lambda *args, **kwargs: (
                '<a class="result__a" href="https://example.com/page">'
                "Example result</a>"
            )

            result = runtime_module._web_search({"query": "example"})
        finally:
            runtime_module._read_url = original_read_url

        result_path = Path(result.result_path)
        self.assertTrue(result_path.exists())
        self.assertEqual(result_path.suffix, ".json")
        self.assertIn("Example result", result.content)
        self.assertEqual(
            result.metadata["results"][0]["url"], "https://example.com/page"
        )
        result_path.unlink(missing_ok=True)

    def test_html_text_extractor_treats_br_as_boundary(self) -> None:
        extractor = runtime_module._TextExtractor()

        extractor.feed("<span>First</span><br><span>Second</span>")

        self.assertEqual(extractor.parts, ["First", "\n", "Second"])

    def test_disabled_tool_is_not_exposed_and_does_not_execute(self) -> None:
        screen_capture_agent = FakeScreenCaptureAgent()
        registry = RuntimeToolRegistry(
            _tool_settings(tool_take_screenshot_policy="deny"),
            screen_capture_agent=screen_capture_agent,
        )
        executor = ToolExecutor(registry)

        exposed_names = {
            definition.name for definition in registry.enabled_definitions
        }
        record, result = executor.execute(
            ToolCallRequest(
                call_id="call-1",
                name="take_screenshot",
                arguments={},
            )
        )

        self.assertNotIn("take_screenshot", exposed_names)
        self.assertFalse(screen_capture_agent.called)
        self.assertEqual(record.status, "error")
        self.assertIn("disabled", result.content)

    def test_live_control_tool_is_internal_and_can_end_when_tools_are_off(
        self,
    ) -> None:
        registry = RuntimeToolRegistry(
            _tool_settings(tools_enabled=False),
            include_live_control_tools=True,
        )
        executor = ToolExecutor(registry)

        exposed_names = [
            definition.name for definition in registry.enabled_definitions
        ]
        record, result = executor.execute(
            ToolCallRequest(
                call_id="call-end",
                name="end_live_session",
                arguments={"reason": "user said no"},
            )
        )

        self.assertEqual(exposed_names, ["end_live_session"])
        self.assertEqual(record.status, "success")
        self.assertEqual(record.tool_name, "end_live_session")
        self.assertEqual(result.content, "Live ended.")
        self.assertEqual(result.metadata["end_live_session"], True)

    def test_add_memory_tool_saves_json_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-memory",
                    name="add_memory",
                    arguments={
                        "title": "Add dashboard feature",
                        "description": (
                            "Remember to add a new dashboard feature to the "
                            "project."
                        ),
                        "intent": "Add a new feature later.",
                        "source_text": (
                            "I need to remember to add a new feature."
                        ),
                    },
                )
            )

            memories = memory_manager.list_memories()

        self.assertEqual(record.status, "success")
        self.assertEqual(record.tool_name, "add_memory")
        self.assertEqual(
            record.arguments_summary, "title: Add dashboard feature"
        )
        self.assertIn("Memory saved", result.content)
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].title, "Add dashboard feature")
        self.assertEqual(
            memories[0].source_text,
            "I need to remember to add a new feature.",
        )

    def test_disabled_add_memory_tool_does_not_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            registry = RuntimeToolRegistry(
                _tool_settings(tool_add_memory_policy="deny"),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            exposed_names = {
                definition.name for definition in registry.enabled_definitions
            }
            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-memory",
                    name="add_memory",
                    arguments={
                        "title": "Save me",
                        "description": "Remember this.",
                    },
                )
            )
            memories = memory_manager.list_memories()

        self.assertNotIn("add_memory", exposed_names)
        self.assertEqual(record.status, "error")
        self.assertIn("disabled", result.content)
        self.assertEqual(memories, [])

    def test_read_memory_tool_returns_compact_ranked_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory_manager.add_memory(
                title="Billing export",
                description="Remember to add CSV export for invoices.",
                intent="Improve admin billing workflow.",
            )
            memory_manager.add_memory(
                title="Onboarding",
                description="Add a first-run checklist.",
                intent="Help new users start faster.",
            )
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            exposed_names = {
                definition.name for definition in registry.enabled_definitions
            }
            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-read-memory",
                    name="read_memory",
                    arguments={
                        "query": "what was the billing invoice thing",
                        "max_results": 5,
                    },
                )
            )

        self.assertIn("read_memory", exposed_names)
        self.assertEqual(record.status, "success")
        self.assertEqual(record.tool_name, "read_memory")
        self.assertEqual(
            record.arguments_summary,
            "query: what was the billing invoice thing",
        )
        self.assertIn("Matching memories:", result.content)
        self.assertIn("Billing export", result.content)
        self.assertIn("Memory ID:", result.content)
        self.assertIn(result.metadata["matches"][0]["id"], result.content)
        self.assertIn("Description:", result.content)
        self.assertNotIn("Note:", result.content)
        self.assertNotIn('"memories"', result.content)

    def test_read_memory_tool_returns_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-read-memory",
                    name="read_memory",
                    arguments={"query": "anything"},
                )
            )

        self.assertEqual(record.status, "success")
        self.assertEqual(result.content, "No memories saved yet.")

    def test_disabled_read_memory_tool_does_not_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory_manager.add_memory(
                title="Private thing",
                description="Do not expose when disabled.",
            )
            registry = RuntimeToolRegistry(
                _tool_settings(tool_read_memory_policy="deny"),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            exposed_names = {
                definition.name for definition in registry.enabled_definitions
            }
            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-read-memory",
                    name="read_memory",
                    arguments={"query": "private"},
                )
            )

        self.assertNotIn("read_memory", exposed_names)
        self.assertEqual(record.status, "error")
        self.assertIn("disabled", result.content)

    def test_change_memory_tool_updates_memory_by_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory = memory_manager.add_memory(
                title="Onboarding",
                description="Add a first-run checklist.",
                intent="Help new users.",
            )
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            exposed_names = {
                definition.name for definition in registry.enabled_definitions
            }
            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-change-memory",
                    name="change_memory",
                    arguments={
                        "memory_id": memory.entity_id,
                        "description": "Add a first-run checklist and tips.",
                    },
                )
            )
            saved = memory_manager.list_memories()[0]

        self.assertIn("change_memory", exposed_names)
        self.assertEqual(record.status, "success")
        self.assertEqual(record.tool_name, "change_memory")
        self.assertEqual(
            record.arguments_summary,
            f"memory: {memory.entity_id}",
        )
        self.assertIn("Memory updated", result.content)
        self.assertEqual(saved.title, "Onboarding")
        self.assertEqual(
            saved.description,
            "Add a first-run checklist and tips.",
        )

    def test_change_memory_tool_accepts_note_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory = memory_manager.add_memory(
                title="Computer Architecture Assignment",
                description="User needs to do the assignment.",
            )
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-change-memory",
                    name="change_memory",
                    arguments={
                        "memory_id": memory.entity_id,
                        "note": (
                            "Computer architecture assignment due April 5th."
                        ),
                    },
                )
            )
            saved = memory_manager.list_memories()[0]

        self.assertEqual(record.status, "success")
        self.assertIn("Memory updated", result.content)
        self.assertEqual(
            saved.description,
            "Computer architecture assignment due April 5th.",
        )

    def test_change_memory_tool_updates_single_query_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory_manager.add_memory(
                title="Billing export",
                description="Remember CSV export for invoices.",
            )
            memory_manager.add_memory(
                title="Onboarding",
                description="Add a first-run checklist.",
            )
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-change-memory",
                    name="change_memory",
                    arguments={
                        "query": "onboarding",
                        "intent": "Help new users start faster.",
                    },
                )
            )
            saved = memory_manager.search_memories("onboarding")["matches"][0]

        self.assertEqual(record.status, "success")
        self.assertIn("Memory updated", result.content)
        self.assertEqual(saved["intent"], "Help new users start faster.")

    def test_change_memory_tool_refuses_ambiguous_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory_manager.add_memory(
                title="Billing export",
                description="Remember billing CSV export.",
            )
            memory_manager.add_memory(
                title="Billing reminder",
                description="Remember billing email follow-up.",
            )
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-change-memory",
                    name="change_memory",
                    arguments={
                        "query": "billing",
                        "description": "Updated billing note.",
                    },
                )
            )
            memories = memory_manager.list_memories()

        self.assertEqual(record.status, "success")
        self.assertIn("could not tell which memory", result.content)
        self.assertIn("Billing export", result.content)
        self.assertIn("Billing reminder", result.content)
        self.assertNotIn('"memories"', result.content)
        self.assertEqual(
            [memory.description for memory in memories],
            [
                "Remember billing email follow-up.",
                "Remember billing CSV export.",
            ],
        )

    def test_change_memory_tool_returns_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            registry = RuntimeToolRegistry(
                _tool_settings(),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-change-memory",
                    name="change_memory",
                    arguments={
                        "query": "anything",
                        "description": "Updated note.",
                    },
                )
            )

        self.assertEqual(record.status, "success")
        self.assertEqual(result.content, "No memories saved yet.")

    def test_disabled_change_memory_tool_does_not_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory = memory_manager.add_memory(
                title="Private thing",
                description="Do not change when disabled.",
            )
            registry = RuntimeToolRegistry(
                _tool_settings(tool_change_memory_policy="deny"),
                memory_manager=memory_manager,
            )
            executor = ToolExecutor(registry)

            exposed_names = {
                definition.name for definition in registry.enabled_definitions
            }
            record, result = executor.execute(
                ToolCallRequest(
                    call_id="call-change-memory",
                    name="change_memory",
                    arguments={
                        "memory_id": memory.entity_id,
                        "description": "Changed.",
                    },
                )
            )
            saved = memory_manager.list_memories()[0]

        self.assertNotIn("change_memory", exposed_names)
        self.assertEqual(record.status, "error")
        self.assertIn("disabled", result.content)
        self.assertEqual(saved.description, "Do not change when disabled.")

    def test_ocr_tool_extracts_screen_text_and_copies_clipboard(self) -> None:
        screen_capture_agent = FakeScreenCaptureAgent()
        ocr_agent = FakeOCRAgent("```text\nInvoice\nTotal $20\n```")
        clipboard_service = FakeClipboardService()
        registry = RuntimeToolRegistry(
            _tool_settings(),
            screen_capture_agent=screen_capture_agent,
            ocr_service=OCRService(ocr_agent, clipboard_service),
        )
        executor = ToolExecutor(registry)

        record, result = executor.execute(
            ToolCallRequest(
                call_id="call-ocr",
                name="ocr_screen",
                arguments={
                    "instruction": "Extract only the invoice total.",
                    "reason": "read text",
                },
            )
        )

        self.assertTrue(screen_capture_agent.called)
        self.assertEqual(record.status, "success")
        self.assertEqual(record.tool_name, "ocr_screen")
        self.assertEqual(result.content, "Invoice\nTotal $20")
        self.assertEqual(
            clipboard_service.last_copied_text, "Invoice\nTotal $20"
        )
        self.assertEqual(
            ocr_agent.instructions, ["Extract only the invoice total."]
        )
        self.assertEqual(len(result.images), 1)
        self.assertEqual(result.artifact_paths, [result.images[0].path])
        self.assertEqual(
            result.metadata["instruction"],
            "Extract only the invoice total.",
        )

    def test_ocr_tool_description_covers_copy_text_from_image_requests(
        self,
    ) -> None:
        registry = RuntimeToolRegistry(_tool_settings())
        descriptions = {
            definition.name: definition.description
            for definition in registry.enabled_definitions
        }
        ocr_payload = next(
            definition.provider_payload()
            for definition in registry.enabled_definitions
            if definition.name == "ocr_screen"
        )
        instruction_description = ocr_payload["function"]["parameters"][
            "properties"
        ]["instruction"]["description"]

        self.assertIn("copy, read, extract", descriptions["ocr_screen"])
        self.assertIn("image", descriptions["ocr_screen"])
        self.assertIn("screenshot", descriptions["ocr_screen"])
        self.assertIn(
            "The user does not need to say OCR",
            descriptions["ocr_screen"],
        )
        self.assertIn("copy this text from the image", instruction_description)

    def test_ocr_tool_rejects_missing_instruction_before_capture(self) -> None:
        screen_capture_agent = FakeScreenCaptureAgent()
        clipboard_service = FakeClipboardService()
        registry = RuntimeToolRegistry(
            _tool_settings(),
            screen_capture_agent=screen_capture_agent,
            ocr_service=OCRService(FakeOCRAgent(), clipboard_service),
        )
        executor = ToolExecutor(registry)

        record, result = executor.execute(
            ToolCallRequest(
                call_id="call-ocr",
                name="ocr_screen",
                arguments={"reason": "read headline"},
            )
        )

        self.assertFalse(screen_capture_agent.called)
        self.assertEqual(clipboard_service.last_copied_text, "")
        self.assertEqual(record.status, "error")
        self.assertIn("instruction", result.content)

    def test_disabled_ocr_tool_does_not_capture_or_copy(self) -> None:
        screen_capture_agent = FakeScreenCaptureAgent()
        clipboard_service = FakeClipboardService()
        registry = RuntimeToolRegistry(
            _tool_settings(tool_ocr_policy="deny"),
            screen_capture_agent=screen_capture_agent,
            ocr_service=OCRService(FakeOCRAgent(), clipboard_service),
        )
        executor = ToolExecutor(registry)

        exposed_names = {
            definition.name for definition in registry.enabled_definitions
        }
        record, result = executor.execute(
            ToolCallRequest(
                call_id="call-ocr",
                name="ocr_screen",
                arguments={},
            )
        )

        self.assertNotIn("ocr_screen", exposed_names)
        self.assertFalse(screen_capture_agent.called)
        self.assertEqual(clipboard_service.last_copied_text, "")
        self.assertEqual(record.status, "error")
        self.assertIn("disabled", result.content)

    def test_invalid_arguments_do_not_execute_tool(self) -> None:
        screen_capture_agent = FakeScreenCaptureAgent()
        registry = RuntimeToolRegistry(
            _tool_settings(),
            screen_capture_agent=screen_capture_agent,
        )
        executor = ToolExecutor(registry)

        record, result = executor.execute(
            ToolCallRequest(
                call_id="call-1",
                name="take_screenshot",
                arguments={"unexpected": True},
            )
        )

        self.assertFalse(screen_capture_agent.called)
        self.assertEqual(record.status, "error")
        self.assertIn("Unexpected argument", result.content)


if __name__ == "__main__":
    unittest.main()
