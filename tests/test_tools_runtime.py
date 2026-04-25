import unittest
from pathlib import Path

from src.models.settings import AppSettings
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
