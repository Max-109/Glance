import unittest

from src.ui.qt_app import (
    RuntimeErrorNoticeController,
    _summarize_runtime_error_notice,
)


class RuntimeErrorNoticeTests(unittest.TestCase):
    def test_input_audio_error_becomes_actionable_notice(self) -> None:
        notice = _summarize_runtime_error_notice(
            "Live failed: Tool-capable live request failed: "
            "Error code: 404 - {'error': {'message': "
            "'No endpoints found that support input audio', 'code': 404}}"
        )

        self.assertEqual(
            notice,
            "Live failed: the selected model does not support input audio. "
            "Choose an audio-capable live model in Providers.",
        )

    def test_wrapped_provider_error_is_shortened(self) -> None:
        notice = _summarize_runtime_error_notice(
            "Live failed: Tool-capable live request failed: "
            "Missing LLM API key."
        )

        self.assertEqual(notice, "Live failed: Missing LLM API key.")

    def test_unknown_live_failure_keeps_readable_reason(self) -> None:
        notice = _summarize_runtime_error_notice(
            "Live failed: Provider exploded before returning a response."
        )

        self.assertEqual(
            notice,
            "Live failed: Provider exploded before returning a response.",
        )

    def test_repeated_runtime_error_notice_is_suppressed(self) -> None:
        notifier = RuntimeErrorNoticeController()
        message = (
            "Live failed: Tool-capable live request failed: "
            "Missing LLM API key."
        )

        first_notice = notifier.maybe_notice(message, now_ms=1_000)
        repeated_notice = notifier.maybe_notice(message, now_ms=30_000)
        later_notice = notifier.maybe_notice(message, now_ms=61_000)

        self.assertEqual(first_notice, "Live failed: Missing LLM API key.")
        self.assertEqual(repeated_notice, "")
        self.assertEqual(later_notice, "Live failed: Missing LLM API key.")

    def test_different_runtime_error_notice_is_allowed(self) -> None:
        notifier = RuntimeErrorNoticeController()

        first_notice = notifier.maybe_notice(
            "Live failed: Missing LLM API key.", now_ms=1_000
        )
        second_notice = notifier.maybe_notice(
            "Live failed: Audio playback is unavailable.", now_ms=2_000
        )

        self.assertEqual(first_notice, "Live failed: Missing LLM API key.")
        self.assertEqual(
            second_notice, "Live failed: Audio playback is unavailable."
        )


if __name__ == "__main__":
    unittest.main()
