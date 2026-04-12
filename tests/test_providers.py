import unittest

from src.services.providers import _extract_text_content


class ContentExtractionTests(unittest.TestCase):
    def test_extract_text_content_handles_plain_string(self) -> None:
        self.assertEqual(_extract_text_content("hello"), "hello")

    def test_extract_text_content_handles_part_list(self) -> None:
        content = [
            {"type": "text", "text": "hello"},
            {"type": "text", "text": {"value": "world"}},
        ]

        self.assertEqual(_extract_text_content(content), "hello\nworld")


if __name__ == "__main__":
    unittest.main()
