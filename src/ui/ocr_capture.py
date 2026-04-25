from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

from src.core.orchestrator import Orchestrator


logger = logging.getLogger("glance.ocr_capture")
_MIN_SELECTION_SIZE = 8


class OCRCaptureController(QObject):
    _start_requested = Signal()
    _completed = Signal(str)
    _failed = Signal(str)
    _canceled = Signal(str)

    def __init__(
        self,
        *,
        orchestrator_factory,
        on_message,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._orchestrator_factory = orchestrator_factory
        self._on_message = on_message
        self._overlay: OCRSelectionOverlay | None = None
        self._busy = False
        self._start_requested.connect(self._start)
        self._completed.connect(
            lambda message: self._finish(message, "success")
        )
        self._failed.connect(lambda message: self._finish(message, "error"))
        self._canceled.connect(
            lambda message: self._finish(message, "neutral")
        )

    def start(self) -> None:
        self._start_requested.emit()

    def _start(self) -> None:
        if self._busy:
            self._on_message("OCR is already running.", "neutral")
            return
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self._on_message(
                "OCR unavailable: primary display was not found.", "error"
            )
            return
        self._busy = True
        self._overlay = OCRSelectionOverlay(
            screen_geometry=screen.geometry(),
            on_selected=lambda rect: self._capture_selection(screen, rect),
            on_canceled=lambda: self._canceled.emit("OCR selection canceled."),
        )
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.activateWindow()

    def stop(self) -> None:
        overlay = self._overlay
        self._overlay = None
        self._busy = False
        if overlay is not None:
            overlay.close()

    def _capture_selection(self, screen, rect: QRect) -> None:
        overlay = self._overlay
        self._overlay = None
        if overlay is not None:
            overlay.hide()
            overlay.deleteLater()
        QTimer.singleShot(120, lambda: self._grab_and_run(screen, rect))

    def _grab_and_run(self, screen, rect: QRect) -> None:
        if (
            rect.width() < _MIN_SELECTION_SIZE
            or rect.height() < _MIN_SELECTION_SIZE
        ):
            self._canceled.emit("OCR selection was too small.")
            return
        geometry = screen.geometry()
        local_rect = QRect(
            rect.x() - geometry.x(),
            rect.y() - geometry.y(),
            rect.width(),
            rect.height(),
        )
        pixmap = screen.grabWindow(
            0,
            local_rect.x(),
            local_rect.y(),
            local_rect.width(),
            local_rect.height(),
        )
        if pixmap.isNull():
            self._failed.emit(
                "OCR capture failed. Check macOS screen recording permission."
            )
            return
        temp_file = tempfile.NamedTemporaryFile(
            prefix="glance-ocr-selection-",
            suffix=".png",
            delete=False,
        )
        image_path = Path(temp_file.name)
        temp_file.close()
        if not pixmap.save(str(image_path), "PNG"):
            self._failed.emit("OCR capture failed while saving the selection.")
            return
        Thread(
            target=self._run_ocr,
            args=(str(image_path),),
            name="glance-ocr-selection",
            daemon=True,
        ).start()

    def _run_ocr(self, image_path: str) -> None:
        try:
            orchestrator: Orchestrator = self._orchestrator_factory()
            interaction = orchestrator.run_mode("ocr", image_path=image_path)
        except Exception as exc:  # pragma: no cover - runtime integration.
            logger.exception("OCR selection failed")
            self._failed.emit(f"OCR failed: {exc}")
            return
        copied_count = len(interaction.extracted_text)
        if copied_count == 0:
            self._completed.emit(
                "OCR found no visible text. Clipboard cleared."
            )
            return
        self._completed.emit(
            f"OCR copied {copied_count} characters to clipboard."
        )

    def _finish(self, message: str, kind: str) -> None:
        self._busy = False
        self._on_message(message, kind)


class OCRSelectionOverlay(QWidget):
    def __init__(
        self,
        *,
        screen_geometry: QRect,
        on_selected,
        on_canceled,
    ) -> None:
        super().__init__(None)
        self._screen_geometry = QRect(screen_geometry)
        self._on_selected = on_selected
        self._on_canceled = on_canceled
        self._origin: QPoint | None = None
        self._selection = QRect()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setGeometry(self._screen_geometry)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.grabKeyboard()
        self.grabMouse()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def closeEvent(self, event) -> None:
        self.releaseKeyboard()
        self.releaseMouse()
        super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self._on_canceled()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._origin = event.position().toPoint()
        self._selection = QRect(self._origin, self._origin)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._origin is None:
            return
        self._selection = QRect(
            self._origin, event.position().toPoint()
        ).normalized()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        self.releaseKeyboard()
        self.releaseMouse()
        selection = self._selection.normalized()
        self._origin = None
        self.close()
        self._on_selected(
            selection.translated(self._screen_geometry.topLeft())
        )

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 28))
        if self._selection.isNull():
            return
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Clear
        )
        painter.fillRect(self._selection, Qt.GlobalColor.transparent)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        painter.setPen(QPen(QColor("#f0b100"), 2))
        painter.drawRect(self._selection.adjusted(0, 0, -1, -1))
