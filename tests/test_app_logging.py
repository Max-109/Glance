import logging
import tempfile
import unittest
from pathlib import Path

from src.services import app_logging


class ConsoleLoggingTests(unittest.TestCase):
    def test_console_formatter_styles_multiline_message(self) -> None:
        formatter = app_logging._ConsoleLogFormatter(
            accent_color="#a7ffde",
            use_color=True,
        )
        record = logging.makeLogRecord(
            {
                "name": "glance.live",
                "levelno": logging.INFO,
                "levelname": "INFO",
                "msg": "live turn completed\ncapture    7012.3 ms\ntotal      18260.4 ms",
                "args": (),
            }
        )

        formatted = formatter.format(record)

        self.assertIn("\033[38;2;", formatted)
        self.assertIn("live", formatted)
        self.assertIn("capture", formatted)
        self.assertIn("7012.3 ms", formatted)
        self.assertIn("\n  ", formatted)

    def test_update_console_logging_accent_rebuilds_palette(self) -> None:
        logger = logging.getLogger("glance")
        original_handlers = list(logger.handlers)
        original_level = logger.level
        original_propagate = logger.propagate

        for handler in list(logger.handlers):
            logger.removeHandler(handler)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                log_file = app_logging.configure_app_logging(
                    Path(temp_dir), accent_color="#a7ffde"
                )
                console_handler = app_logging._get_handler(
                    logger, app_logging._CONSOLE_HANDLER_NAME
                )
                self.assertIsNotNone(console_handler)
                if console_handler is None:
                    self.fail("Console handler was not configured.")

                original_info_color = console_handler.formatter._palette.info
                app_logging.update_console_logging_accent("#ff8844")
                updated_info_color = console_handler.formatter._palette.info

                self.assertEqual(log_file, Path(temp_dir) / "glance.log")
                self.assertNotEqual(original_info_color, updated_info_color)
        finally:
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                if handler not in original_handlers:
                    handler.close()
            for handler in original_handlers:
                logger.addHandler(handler)
            logger.setLevel(original_level)
            logger.propagate = original_propagate


if __name__ == "__main__":
    unittest.main()
