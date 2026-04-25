import threading
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication

from src.ui.ocr_capture import OCRCaptureController


class OCRCaptureControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QCoreApplication.instance() or QCoreApplication([])

    def test_start_from_worker_thread_defers_qt_work_to_main_thread(
        self,
    ) -> None:
        main_thread_id = threading.get_ident()
        primary_screen_thread_ids: list[int] = []

        controller = OCRCaptureController(
            orchestrator_factory=lambda: None,
            on_message=lambda _message, _kind: None,
        )

        def record_primary_screen_call():
            primary_screen_thread_ids.append(threading.get_ident())
            return None

        with patch(
            "src.ui.ocr_capture.QGuiApplication.primaryScreen",
            side_effect=record_primary_screen_call,
        ):
            worker = threading.Thread(
                target=controller.start,
                name="glance-test-hotkey-thread",
            )
            worker.start()
            worker.join(timeout=1.0)

            self.assertFalse(worker.is_alive())
            self.assertEqual(primary_screen_thread_ids, [])

            self._app.processEvents()

        self.assertEqual(primary_screen_thread_ids, [main_thread_id])


if __name__ == "__main__":
    unittest.main()
