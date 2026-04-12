from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from src.services.app_paths import build_app_paths
from src.services.history_manager import HistoryManager
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import JsonHistoryRepository, JsonSettingsStore
from src.ui.qt_icons import IconLibrary
from src.ui.settings_viewmodel import SettingsViewModel


QQuickStyle.setStyle("Basic")


def run_settings_app(env_file: Path | None = None) -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Glance")
    app.setOrganizationName("Glance")
    app.setQuitOnLastWindowClosed(False)

    paths = build_app_paths()
    settings_manager = SettingsManager(
        store=JsonSettingsStore(paths.config_file),
        env_file=env_file or Path(".env"),
    )
    history_manager = HistoryManager(
        JsonHistoryRepository(paths.history_file),
        history_limit=settings_manager.load().history_length,
    )
    controller = SettingsViewModel(settings_manager, history_manager)
    icon_library = IconLibrary()

    qml_dir = Path(__file__).resolve().parent / "qml"
    engine = QQmlApplicationEngine()
    engine.setInitialProperties(
        {
            "settingsController": controller,
            "iconLibrary": icon_library,
        }
    )
    engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))

    if not engine.rootObjects():
        raise RuntimeError("Could not load the QML settings interface.")

    root_window = engine.rootObjects()[0]
    tray = _build_tray_icon(app, root_window, controller)
    tray.show()

    return app.exec()


def _build_tray_icon(
    app, root_window, controller: SettingsViewModel
) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(_create_tray_icon(), app)
    tray.setToolTip("Glance")

    menu = QMenu()
    menu.setFont(QFont("SF Pro Text", 13))

    show_action = QAction("Open Glance", menu)
    show_action.triggered.connect(lambda: _toggle_window(root_window, force_show=True))
    menu.addAction(show_action)

    menu.addSeparator()

    live_action = QAction("Live: --", menu)
    live_action.setEnabled(False)
    menu.addAction(live_action)

    quick_action = QAction("Quick: --", menu)
    quick_action.setEnabled(False)
    menu.addAction(quick_action)

    ocr_action = QAction("OCR: --", menu)
    ocr_action.setEnabled(False)
    menu.addAction(ocr_action)

    def update_keybind_actions() -> None:
        settings = controller.settings
        live_action.setText(f"Live: {settings.get('live_keybind', '--')}")
        quick_action.setText(f"Quick: {settings.get('quick_keybind', '--')}")
        ocr_action.setText(f"OCR: {settings.get('ocr_keybind', '--')}")

    update_keybind_actions()
    controller.settingsChanged.connect(update_keybind_actions)

    menu.addSeparator()

    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    def on_activated(reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            _toggle_window(root_window)

    tray.activated.connect(on_activated)
    return tray


def _toggle_window(root_window, force_show: bool = False) -> None:
    if root_window.isVisible() and not force_show:
        root_window.hide()
        return

    cursor_pos = QCursor.pos()
    width = int(root_window.width())
    height = int(root_window.height())
    root_window.setX(cursor_pos.x() - width + 24)
    root_window.setY(cursor_pos.y() + 18)
    root_window.show()
    root_window.raise_()
    root_window.requestActivate()


def _create_tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#1a1a1f"))
    painter.setPen(QColor("#c9c3bf"))
    painter.drawRoundedRect(8, 8, 48, 48, 14, 14)
    painter.setPen(QColor("#f0ebe7"))
    font = QFont("SF Pro Display", 28)
    font.setWeight(QFont.DemiBold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "G")
    painter.end()

    return QIcon(pixmap)
