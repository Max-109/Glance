from __future__ import annotations

from pathlib import Path
from threading import Event, Lock

from src.exceptions.app_exceptions import ProviderError
from src.services.audio_devices import AudioDeviceService

try:
    from PySide6.QtCore import QObject, QUrl, Signal, Slot
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # pragma: no cover - optional in test environments.
    QObject = object
    QUrl = None
    Signal = None
    Slot = None
    QAudioOutput = None
    QMediaPlayer = None

if Slot is None:  # pragma: no cover - used only without Qt.

    def Slot(*_args, **_kwargs):
        def decorator(function):
            return function

        return decorator


class QtAudioPlaybackService(QObject):
    if Signal is not None:
        _play_requested = Signal(str)
        _stop_requested = Signal()

    def __init__(
        self,
        *,
        device_service: AudioDeviceService | None = None,
        output_device_id: str = "default",
    ) -> None:
        if QMediaPlayer is None or QAudioOutput is None or Signal is None:
            raise ProviderError("Qt multimedia playback is unavailable.")
        super().__init__()
        self._device_service = device_service or AudioDeviceService()
        self._output_device_id = output_device_id
        self._player = QMediaPlayer(self)
        self._output = QAudioOutput(self)
        self._player.setAudioOutput(self._output)
        self._lock = Lock()
        self._completion_event: Event | None = None
        self._error_message = ""

        self._play_requested.connect(self._play_on_main_thread)
        self._stop_requested.connect(self._stop_on_main_thread)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_error)
        self.set_output_device_id(output_device_id)

    def set_output_device_id(self, output_device_id: str) -> None:
        self._output_device_id = output_device_id or "default"
        device = self._device_service.resolve_output_device(self._output_device_id)
        set_device = getattr(self._output, "setDevice", None)
        if callable(set_device) and device is not None:
            set_device(device)

    def play_blocking(self, audio_path: str, stop_event: Event | None = None) -> str:
        if not Path(audio_path).exists():
            raise ProviderError(f"Speech file does not exist: {audio_path}")

        completion_event = Event()
        with self._lock:
            self._completion_event = completion_event
            self._error_message = ""
        self._play_requested.emit(audio_path)

        while not completion_event.wait(0.1):
            if stop_event and stop_event.is_set():
                self.stop()
                break

        if self._error_message:
            raise ProviderError(self._error_message)
        return audio_path

    def stop(self) -> None:
        self._stop_requested.emit()

    @Slot(str)
    def _play_on_main_thread(self, audio_path: str) -> None:
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(audio_path))
        self._player.play()

    @Slot()
    def _stop_on_main_thread(self) -> None:
        self._player.stop()
        self._finish_playback()

    @Slot(object)
    def _on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia:
            self._finish_playback()
        elif status == QMediaPlayer.InvalidMedia:
            self._error_message = (
                "Audio playback failed because the media file was invalid."
            )
            self._finish_playback()

    @Slot(object, str)
    def _on_error(self, error, error_string: str) -> None:
        del error
        self._error_message = error_string or "Audio playback failed."
        self._finish_playback()

    def _finish_playback(self) -> None:
        with self._lock:
            completion_event = self._completion_event
            self._completion_event = None
        if completion_event is not None:
            completion_event.set()
