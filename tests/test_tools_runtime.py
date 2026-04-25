import unittest
from pathlib import Path

from src.models.settings import AppSettings
from src.tools import RuntimeToolRegistry, ToolCallRequest, ToolExecutor


class FakeScreenCaptureAgent:
    def __init__(self) -> None:
        self.called = False

    def run(self, *, image_path=None, output_path=None):
        self.called = True
        path = Path(output_path or image_path or "capture.png")
        path.write_bytes(b"fake-png")
        return str(path)


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
    def test_screenshot_tool_saves_artifact_and_returns_image_context(self) -> None:
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

    def test_disabled_tool_is_not_exposed_and_does_not_execute(self) -> None:
        screen_capture_agent = FakeScreenCaptureAgent()
        registry = RuntimeToolRegistry(
            _tool_settings(tool_take_screenshot_policy="deny"),
            screen_capture_agent=screen_capture_agent,
        )
        executor = ToolExecutor(registry)

        exposed_names = {definition.name for definition in registry.enabled_definitions}
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
