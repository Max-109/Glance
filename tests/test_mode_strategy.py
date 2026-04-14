import unittest

from src.strategies.mode_strategy import force_pause_at_end_for_tts


class ForcePauseAtEndForTtsTests(unittest.TestCase):
    def test_appends_three_dots_once(self) -> None:
        self.assertEqual(force_pause_at_end_for_tts("Hello there!"), "Hello there!...")

    def test_keeps_existing_trailing_ellipsis(self) -> None:
        self.assertEqual(force_pause_at_end_for_tts("Hello there..."), "Hello there...")


if __name__ == "__main__":
    unittest.main()
