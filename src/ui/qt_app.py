from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QByteArray, QCoreApplication, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from src.core.orchestrator import build_orchestrator_with_dependencies
from src.services.app_paths import build_app_paths
from src.services.app_logging import configure_app_logging
from src.services.audio_playback import QtAudioPlaybackService
from src.services.audio_recording import ThresholdAudioRecorder
from src.services.audio_signal import AudioTestSignalService
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
from src.ui.electron_bridge import SettingsBridgeServer
from src.ui.electron_window import ElectronShellController
from src.ui.settings_viewmodel import SettingsViewModel


class LiveStatusBridge(QObject):
    statusChanged = Signal(str, str)


class TrayIconController(QObject):
    _ANIMATION_INTERVAL_MS = {
        "listening": 420,
        "processing": 560,
        "speaking": 420,
        "ready": 420,
    }
    _ERROR_FLASH_MS = 1400
    _READY_FLASH_MS = 520

    def __init__(self, tray: QSystemTrayIcon, app: QApplication) -> None:
        super().__init__(tray)
        self._tray = tray
        self._base_state = "idle"
        self._override_state: str | None = None
        self._frame = 0
        self._color_scheme = app.styleHints().colorScheme()

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._advance_frame)

        self._ready_timer = QTimer(self)
        self._ready_timer.setSingleShot(True)
        self._ready_timer.timeout.connect(self._clear_ready_override)

        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(self._clear_override)

        app.styleHints().colorSchemeChanged.connect(self._handle_color_scheme_changed)
        self._refresh_animation()
        self._apply_icon()

    def set_state(self, state: str) -> None:
        normalized_state = _normalize_tray_state(state)
        if normalized_state == self._base_state and self._override_state is None:
            return
        previous_state = self._base_state
        self._base_state = normalized_state

        if self._override_state == "ready" and normalized_state != "listening":
            self._clear_ready_override()

        if previous_state == "speaking" and normalized_state == "listening":
            self._start_ready_override()
            return

        if self._override_state is None:
            self._frame = 0
            self._refresh_animation()
            self._apply_icon()

    def flash_error(self) -> None:
        self._ready_timer.stop()
        self._override_state = "error"
        self._frame = 0
        self._animation_timer.stop()
        self._apply_icon()
        self._error_timer.start(self._ERROR_FLASH_MS)

    def _start_ready_override(self) -> None:
        self._override_state = "ready"
        self._frame = 0
        self._refresh_animation()
        self._apply_icon()
        self._ready_timer.start(self._READY_FLASH_MS)

    def _clear_ready_override(self) -> None:
        if self._override_state != "ready":
            self._ready_timer.stop()
            return
        self._ready_timer.stop()
        self._override_state = None
        self._frame = 0
        self._refresh_animation()
        self._apply_icon()

    def _advance_frame(self) -> None:
        self._frame = 1 - self._frame
        self._apply_icon()

    def _clear_override(self) -> None:
        self._ready_timer.stop()
        self._override_state = None
        self._frame = 0
        self._refresh_animation()
        self._apply_icon()

    def _handle_color_scheme_changed(self, color_scheme) -> None:
        self._color_scheme = color_scheme
        self._apply_icon()

    def _refresh_animation(self) -> None:
        interval = self._ANIMATION_INTERVAL_MS.get(self._effective_state())
        if interval is None:
            self._animation_timer.stop()
            self._frame = 0
            return
        if self._animation_timer.interval() != interval:
            self._animation_timer.setInterval(interval)
        if not self._animation_timer.isActive():
            self._animation_timer.start()

    def _effective_state(self) -> str:
        return self._override_state or self._base_state

    def _apply_icon(self) -> None:
        self._tray.setIcon(
            _create_tray_icon(
                color_scheme=self._color_scheme,
                state=self._effective_state(),
                frame=self._frame,
            )
        )


class LiveCueController:
    def __init__(
        self,
        *,
        audio_dir: Path,
        output_device_id: str,
        logger: logging.Logger,
        signal_service: AudioTestSignalService | None = None,
    ) -> None:
        self._logger = logger
        self._playback_service = QtAudioPlaybackService(
            output_device_id=output_device_id,
        )
        self._cue_paths = (signal_service or AudioTestSignalService()).write_live_mode_cues(
            audio_dir / "live-cues"
        )
        self._previous_state: str | None = None
        self._enabled = True

    def set_output_device(self, output_device_id: str) -> None:
        self._playback_service.set_output_device_id(output_device_id)

    def stop(self) -> None:
        self._enabled = False
        self._playback_service.stop()

    def handle_status(self, state: str, message: str) -> None:
        if not self._enabled:
            return
        normalized_state = _normalize_tray_state(state)
        previous_state = self._previous_state
        self._previous_state = normalized_state
        if previous_state is None:
            return

        cue_key = ""
        if previous_state == "idle" and normalized_state == "listening":
            cue_key = "start"
        elif previous_state == "processing" and normalized_state == "speaking":
            cue_key = "reply_ready"
        elif normalized_state == "idle" and message == "Live stopped.":
            cue_key = "cancel"
        if not cue_key:
            return

        cue_path = self._cue_paths.get(cue_key)
        if cue_path is None or not cue_path.exists():
            return

        Thread(
            target=self._play_cue,
            args=(cue_key, cue_path),
            name=f"glance-live-cue-{cue_key}",
            daemon=True,
        ).start()

    def _play_cue(self, cue_key: str, cue_path: Path) -> None:
        try:
            self._playback_service.play_blocking(str(cue_path))
        except Exception as exc:
            self._logger.warning("Live cue '%s' failed: %s", cue_key, exc)


def run_settings_app() -> int:
    QCoreApplication.setAttribute(Qt.AA_MacDontSwapCtrlAndMeta, True)
    app = QApplication(sys.argv)
    app.setApplicationName("Glance")
    app.setOrganizationName("Glance")
    app.setQuitOnLastWindowClosed(False)

    app_icon = _load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    paths = build_app_paths()
    log_file = configure_app_logging(paths.root_dir)
    logger = logging.getLogger("glance.ui")
    logger.info("================ launch pid=%s ================", os.getpid())
    logger.info("Log file: %s", log_file)
    settings_manager = SettingsManager(store=JsonSettingsStore(paths.config_file))
    settings = settings_manager.load()
    history_manager = HistoryManager(
        JsonHistoryRepository(paths.history_file),
        history_limit=settings.history_length,
    )
    controller = SettingsViewModel(
        settings_manager,
        history_manager,
        audio_dir=paths.audio_dir,
    )
    settings_bridge = SettingsBridgeServer(controller)
    live_controller = _build_live_controller(
        settings_manager=settings_manager,
        history_manager=history_manager,
        paths=paths,
    )
    live_cue_controller = _build_live_cue_controller(
        paths=paths,
        output_device_id=settings.audio_output_device,
        logger=logger,
    )
    settings_window = _build_settings_window(
        bridge_url=settings_bridge.url,
        logger=logger,
    )
    tray = _build_tray_icon(
        app,
        settings_window,
        controller,
        live_controller,
        live_cue_controller,
        settings_bridge,
        log_file,
    )
    tray.show()
    if _env_flag_enabled("GLANCE_AUTO_OPEN"):
        QTimer.singleShot(
            0, lambda: _toggle_window(settings_window, force_show=True)
        )
    hotkey_manager = GlobalHotkeyManager(
        callbacks={
            "live": live_controller.toggle,
            "quick": lambda: tray.showMessage(
                "Glance",
                "Quick Ask keybind is saved, but Quick Ask isn't available yet.",
            ),
            "ocr": lambda: tray.showMessage(
                "Glance",
                "Read Screen keybind is saved, but Read Screen isn't available yet.",
            ),
        }
    )
    runtime_refresh_timer = QTimer(app)
    runtime_refresh_timer.setSingleShot(True)
    pending_hotkey_refresh = False

    def refresh_runtime() -> None:
        persisted_settings = settings_manager.reload()
        logger.info("Refreshing runtime from saved settings")
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
            live_controller.set_output_device(persisted_settings.audio_output_device)
            if live_cue_controller is not None:
                live_cue_controller.set_output_device(
                    persisted_settings.audio_output_device
                )
        except Exception as exc:
            live_controller.set_orchestrator(None)
            live_controller.set_recorder(None)
            logger.exception("Live runtime unavailable during refresh")
            tray.showMessage("Glance", f"Live unavailable: {exc}")
        try:
            hotkey_manager.update_bindings(persisted_settings)
            hotkey_manager.set_enabled(True)
        except Exception as exc:
            logger.exception("Hotkeys unavailable during refresh")
            tray.showMessage("Glance", f"Hotkeys unavailable: {exc}")

    runtime_refresh_timer.timeout.connect(refresh_runtime)

    def schedule_runtime_refresh(delay_ms: int = 0) -> None:
        runtime_refresh_timer.stop()
        runtime_refresh_timer.start(delay_ms)

    def schedule_hotkey_refresh_when_window_hides() -> None:
        nonlocal pending_hotkey_refresh
        pending_hotkey_refresh = True

    def restore_hotkeys_if_pending() -> None:
        nonlocal pending_hotkey_refresh
        if not pending_hotkey_refresh or settings_window.isVisible():
            return
        pending_hotkey_refresh = False
        logger.info("Settings window hidden; scheduling hotkey refresh")
        schedule_runtime_refresh(300)

    def handle_binding_change() -> None:
        if controller.bindingActive:
            logger.info(
                "Suspending hotkeys for keybind capture: %s", controller.bindingField
            )
            hotkey_manager.set_enabled(False)
            runtime_refresh_timer.stop()
            return
        logger.info("Keybind capture ended; waiting for window hide before refresh")
        schedule_hotkey_refresh_when_window_hides()

    controller.savedSettingsChanged.connect(schedule_runtime_refresh)
    controller.bindingChanged.connect(handle_binding_change)
    settings_window.visibleChanged.connect(restore_hotkeys_if_pending)
    app.aboutToQuit.connect(hotkey_manager.stop)
    if live_cue_controller is not None:
        app.aboutToQuit.connect(live_cue_controller.stop)
    app.aboutToQuit.connect(live_controller.stop)
    app.aboutToQuit.connect(controller.stopVoicePreview)
    app.aboutToQuit.connect(controller.stopAudioInputTest)
    app.aboutToQuit.connect(controller.stopSpeakerTest)
    app.aboutToQuit.connect(settings_bridge.close)
    app.aboutToQuit.connect(settings_window.close)
    refresh_runtime()

    return app.exec()


def _env_flag_enabled(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_settings_window(
    *,
    bridge_url: str,
    logger: logging.Logger,
):
    window = ElectronShellController(
        project_root=Path(__file__).resolve().parents[2],
        bridge_url=bridge_url,
        logger=logger,
    )
    logger.info("Using Electron settings shell.")
    return window


def _build_tray_icon(
    app,
    settings_window,
    controller: SettingsViewModel,
    live_controller: LiveSessionController,
    live_cue_controller: LiveCueController | None,
    settings_bridge: SettingsBridgeServer,
    log_file: Path,
) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(
        _create_tray_icon(app.styleHints().colorScheme(), state="idle"),
        app,
    )
    tray.setToolTip("Glance")
    tray_icon_controller = TrayIconController(tray, app)

    menu = QMenu()
    menu.setFont(QFont("SF Pro Text", 13))

    show_action = QAction("Open Glance", menu)
    show_action.triggered.connect(
        lambda: _toggle_window(settings_window, force_show=True)
    )
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
        tray_icon_controller.set_state(state)
        settings_bridge.set_runtime_status(state, message)
        if live_cue_controller is not None:
            live_cue_controller.handle_status(state, message)
        live_state_action.setText(f"Live status: {state}")
        tray.setToolTip(f"Glance\n{message}")
        if any(
            token in message.lower() for token in {"failed", "unavailable", "error"}
        ):
            tray_icon_controller.flash_error()
            tray.showMessage("Glance", f"{message}\nSee log: {log_file}")

    status_bridge = LiveStatusBridge(tray)
    status_bridge.statusChanged.connect(update_live_status)
    live_controller.set_status_callback(status_bridge.statusChanged.emit)
    update_live_status(live_controller.state, "Live is idle.")

    menu.addSeparator()

    def request_quit() -> None:
        try:
            settings_window.close()
        finally:
            app.quit()

    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(request_quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    def on_activated(reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            _toggle_window(settings_window)

    tray.activated.connect(on_activated)
    return tray


def _toggle_window(settings_window, force_show: bool = False) -> None:
    if settings_window.isVisible() and not force_show:
        settings_window.hide()
        return

    cursor_pos = QCursor.pos()
    width = int(settings_window.width())
    height = int(settings_window.height())
    settings_window.setX(cursor_pos.x() - width + 24)
    settings_window.setY(cursor_pos.y() + 18)
    settings_window.show()
    settings_window.raise_()
    settings_window.requestActivate()


def _create_tray_icon(
    color_scheme: Qt.ColorScheme | None = None,
    *,
    state: str = "idle",
    frame: int = 0,
) -> QIcon:
    icon = QIcon()
    color = QColor(_tray_icon_color(color_scheme))
    for size in (18, 36, 72):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        _paint_square_frame_symbol(
            painter,
            size,
            foreground=color,
            segment_opacities=_tray_segment_opacities(state, frame),
        )
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def _load_app_icon() -> QIcon:
    icon = _load_svg_icon(
        _asset_path("glance_app_icon.svg"),
        sizes=(64, 128, 256, 512, 1024),
    )
    if icon.isNull():
        return _create_fallback_app_icon()
    return icon


def _asset_path(filename: str) -> Path:
    return Path(__file__).resolve().with_name(filename)


def _load_svg_icon(
    asset_path: Path,
    *,
    sizes: tuple[int, ...],
) -> QIcon:
    try:
        svg_markup = asset_path.read_text(encoding="utf-8")
    except OSError:
        return QIcon()

    renderer = QSvgRenderer(QByteArray(svg_markup.encode("utf-8")))
    if not renderer.isValid():
        return QIcon()

    icon = QIcon()
    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def _tray_icon_color(color_scheme: Qt.ColorScheme | None) -> str:
    if color_scheme == Qt.ColorScheme.Light:
        return "#111111"
    return "#FFFFFF"


def _normalize_tray_state(state: str) -> str:
    if state in {"listening", "processing", "speaking", "ready"}:
        return state
    if state == "error":
        return state
    return "idle"


def _tray_segment_opacities(state: str, frame: int) -> tuple[float, float, float, float]:
    pulse_alpha = 1.0 if frame else 0.38
    completed_alpha = 0.9
    idle_alpha = 0.56
    inactive_alpha = 0.24

    if state == "listening":
        return pulse_alpha, inactive_alpha, inactive_alpha, inactive_alpha
    if state == "processing":
        return completed_alpha, pulse_alpha, inactive_alpha, inactive_alpha
    if state == "speaking":
        return completed_alpha, completed_alpha, pulse_alpha, inactive_alpha
    if state == "ready":
        return completed_alpha, completed_alpha, completed_alpha, pulse_alpha
    if state == "error":
        return 1.0, 1.0, 1.0, 1.0
    return idle_alpha, idle_alpha, idle_alpha, idle_alpha


def _paint_square_frame_symbol(
    painter: QPainter,
    size: int,
    *,
    foreground: QColor,
    segment_opacities: tuple[float, float, float, float],
) -> None:
    painter.setPen(Qt.NoPen)

    outer = max(8, round(size * 0.78))
    thickness = max(2, round(size * 0.14))
    gap = max(1, round(size * 0.06))
    left = (size - outer) // 2
    top = (size - outer) // 2
    span = max(1, outer - (2 * (thickness + gap)))

    segment_specs = (
        (left, top + thickness + gap, thickness, span),
        (left + thickness + gap, top, span, thickness),
        (left + outer - thickness, top + thickness + gap, thickness, span),
        (left + thickness + gap, top + outer - thickness, span, thickness),
    )

    for alpha, (x, y, width, height) in zip(segment_opacities, segment_specs):
        color = QColor(foreground)
        color.setAlphaF(alpha)
        painter.setBrush(color)
        painter.drawRect(x, y, width, height)


def _create_fallback_app_icon() -> QIcon:
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor("#6F696A"))
    painter.setBrush(QColor("#433E40"))
    painter.drawRoundedRect(16, 16, 224, 224, 62, 62)
    _paint_square_frame_symbol(
        painter,
        256,
        foreground=QColor("#F1ECEC"),
        segment_opacities=(1.0, 1.0, 1.0, 1.0),
    )
    painter.end()

    return QIcon(pixmap)


def _create_fallback_tray_icon() -> QIcon:
    return _create_tray_icon(Qt.ColorScheme.Dark, state="idle")


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
        playback_service=QtAudioPlaybackService(
            output_device_id=settings.audio_output_device,
        ),
        audio_dir=paths.audio_dir,
    )


def _build_live_cue_controller(
    *,
    paths,
    output_device_id: str,
    logger: logging.Logger,
) -> LiveCueController | None:
    try:
        return LiveCueController(
            audio_dir=paths.audio_dir,
            output_device_id=output_device_id,
            logger=logger,
        )
    except Exception as exc:
        logger.warning("Live cues unavailable: %s", exc)
        return None
