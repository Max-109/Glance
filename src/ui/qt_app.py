from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from src.core.orchestrator import build_orchestrator_with_dependencies
from src.services.app_paths import build_app_paths
from src.services.app_logging import configure_app_logging
from src.services.audio_playback import QtAudioPlaybackService
from src.services.audio_recording import ThresholdAudioRecorder
from src.services.global_hotkeys import GlobalHotkeyManager
from src.services.history_manager import HistoryManager
from src.services.live_session import LiveSessionController
from src.services.providers import (
    NagaSpeechProvider,
    NagaTranscriptionProvider,
    OpenAICompatibleProvider,
)
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import JsonHistoryRepository, JsonSettingsStore
from src.ui.qt_icons import IconLibrary
from src.ui.settings_viewmodel import SettingsViewModel


QQuickStyle.setStyle("Basic")


class LiveStatusBridge(QObject):
    statusChanged = Signal(str, str)


def run_settings_app() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Glance")
    app.setOrganizationName("Glance")
    app.setQuitOnLastWindowClosed(False)

    paths = build_app_paths()
    log_file = configure_app_logging(paths.root_dir)
    logger = logging.getLogger("glance.ui")
    settings_manager = SettingsManager(store=JsonSettingsStore(paths.config_file))
    settings = settings_manager.load()
    history_manager = HistoryManager(
        JsonHistoryRepository(paths.history_file),
        history_limit=settings.history_length,
    )
    controller = SettingsViewModel(settings_manager, history_manager)
    icon_library = IconLibrary()
    live_controller = _build_live_controller(
        settings_manager=settings_manager,
        history_manager=history_manager,
        paths=paths,
    )

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
    tray = _build_tray_icon(app, root_window, controller, live_controller, log_file)
    tray.show()
    hotkey_manager = GlobalHotkeyManager(
        callbacks={
            "live": live_controller.toggle,
            "quick": lambda: tray.showMessage(
                "Glance",
                "Quick mode hotkey is saved, but Quick mode is not wired into the tray runtime yet.",
            ),
            "ocr": lambda: tray.showMessage(
                "Glance",
                "OCR mode hotkey is saved, but OCR mode is not wired into the tray runtime yet.",
            ),
        }
    )

    def refresh_runtime() -> None:
        persisted_settings = settings_manager.reload()
        history_manager.set_history_limit(persisted_settings.history_length)
        try:
            live_controller.set_orchestrator(
                _build_runtime_orchestrator(
                    settings_manager=settings_manager,
                    history_manager=history_manager,
                    paths=paths,
                )
            )
            live_controller.set_recorder(ThresholdAudioRecorder(persisted_settings))
        except Exception as exc:
            live_controller.set_orchestrator(None)
            live_controller.set_recorder(None)
            logger.exception("Live runtime unavailable during refresh")
            tray.showMessage("Glance", f"Live mode unavailable: {exc}")
        try:
            hotkey_manager.update_bindings(persisted_settings)
        except Exception as exc:
            logger.exception("Hotkeys unavailable during refresh")
            tray.showMessage("Glance", f"Hotkeys unavailable: {exc}")

    controller.savedSettingsChanged.connect(refresh_runtime)
    app.aboutToQuit.connect(hotkey_manager.stop)
    app.aboutToQuit.connect(live_controller.stop)
    refresh_runtime()

    return app.exec()


def _build_tray_icon(
    app,
    root_window,
    controller: SettingsViewModel,
    live_controller: LiveSessionController,
    log_file: Path,
) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(_create_tray_icon(), app)
    tray.setToolTip("Glance")

    menu = QMenu()
    menu.setFont(QFont("SF Pro Text", 13))

    show_action = QAction("Open Glance", menu)
    show_action.triggered.connect(lambda: _toggle_window(root_window, force_show=True))
    menu.addAction(show_action)

    menu.addSeparator()

    live_state_action = QAction("Live status: idle", menu)
    live_state_action.setEnabled(False)
    menu.addAction(live_state_action)

    menu.addSeparator()

    live_action = QAction("Live: --", menu)
    live_action.triggered.connect(live_controller.toggle)
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

    def update_live_status(state: str, message: str) -> None:
        live_state_action.setText(f"Live status: {state}")
        tray.setToolTip(f"Glance\n{message}")
        if any(
            token in message.lower() for token in {"failed", "unavailable", "error"}
        ):
            tray.showMessage("Glance", f"{message}\nSee log: {log_file}")

    status_bridge = LiveStatusBridge(tray)
    status_bridge.statusChanged.connect(update_live_status)
    live_controller.set_status_callback(status_bridge.statusChanged.emit)
    update_live_status(live_controller.state, "Live session idle.")

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


def _build_runtime_orchestrator(
    *,
    settings_manager: SettingsManager,
    history_manager: HistoryManager,
    paths,
):
    settings = settings_manager.current()
    return build_orchestrator_with_dependencies(
        settings=settings,
        paths=paths,
        history_manager=history_manager,
        llm_provider=OpenAICompatibleProvider(settings),
        transcription_provider=NagaTranscriptionProvider(settings),
        tts_provider=NagaSpeechProvider(settings),
    )


def _build_live_controller(
    *,
    settings_manager: SettingsManager,
    history_manager: HistoryManager,
    paths,
) -> LiveSessionController:
    settings = settings_manager.current()
    try:
        orchestrator = _build_runtime_orchestrator(
            settings_manager=settings_manager,
            history_manager=history_manager,
            paths=paths,
        )
        recorder = ThresholdAudioRecorder(settings)
    except Exception:
        orchestrator = None
        recorder = None
    return LiveSessionController(
        orchestrator=orchestrator,
        recorder=recorder,
        playback_service=QtAudioPlaybackService(),
        audio_dir=paths.audio_dir,
    )
