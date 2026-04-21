import unittest

try:
    from src.ui.qt_app import _cue_key_for_status_transition
except ImportError:  # pragma: no cover - optional GUI dependency.
    _cue_key_for_status_transition = None


@unittest.skipIf(
    _cue_key_for_status_transition is None,
    "PySide6 is not installed",
)
class LiveCueTransitionTests(unittest.TestCase):
    def test_no_speech_timeout_reuses_cancel_cue(self) -> None:
        self.assertEqual(
            _cue_key_for_status_transition(
                "listening",
                "Listening...",
                "idle",
                "No speech detected. Live is idle.",
            ),
            "cancel",
        )


if __name__ == "__main__":
    unittest.main()
