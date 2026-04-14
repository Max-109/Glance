from __future__ import annotations

from pathlib import Path
from threading import Event, Lock
import wave

from src.exceptions.app_exceptions import ProviderError
from src.services.audio_devices import AudioDeviceService

try:
    from PySide6.QtCore import (
        QByteArray,
        QBuffer,
        QIODevice,
        QObject,
        QTimer,
        QUrl,
        Signal,
        Slot,
    )
    from PySide6.QtMultimedia import (
        QAudio,
        QAudioFormat,
        QAudioOutput,
        QAudioSink,
        QMediaPlayer,
    )
except ImportError:  # pragma: no cover - optional in test environments.
    QByteArray = None
    QBuffer = None
    QIODevice = None
    QObject = object
    QTimer = None
    QUrl = None
    Signal = None
    Slot = None
    QAudio = None
    QAudioFormat = None
    QAudioOutput = None
    QAudioSink = None
    QMediaPlayer = None

if Slot is None:  # pragma: no cover - used only without Qt.

    def Slot(*_args, **_kwargs):
        def decorator(function):
            return function

        return decorator


class QtAudioPlaybackService(QObject):
    _PLAYBACK_COMPLETION_GRACE_MS = 250
    _PLAYBACK_COMPLETION_TIMEOUT_MS = 1000

    if Signal is not None:
        _play_requested = Signal(int, str)
        _stop_requested = Signal()

    def __init__(
        self,
        *,
        device_service: AudioDeviceService | None = None,
        output_device_id: str = "default",
    ) -> None:
        if Signal is None:
            raise ProviderError("Qt multimedia playback is unavailable.")
        if QMediaPlayer is None and QAudioSink is None and QAudioOutput is None:
            raise ProviderError("Qt multimedia playback is unavailable.")
        super().__init__()
        self._device_service = device_service or AudioDeviceService()
        self._output_device_id = output_device_id

        self._player = None
        self._output = None
        if QMediaPlayer is not None and QAudioOutput is not None:
            self._player = QMediaPlayer(self)
            self._output = QAudioOutput(self)
            self._player.setAudioOutput(self._output)

        self._audio_sink = None
        self._audio_buffer = None
        self._audio_bytes = None
        self._audio_sink_state_connected = False
        self._playback_backend = ""

        self._lock = Lock()
        self._completion_event: Event | None = None
        self._completion_playback_id: int | None = None
        self._error_message = ""
        self._playback_sequence = 0
        self._active_playback_id: int | None = None
        self._playback_started = False
        self._end_of_media_seen = False
        self._stopped_after_playback = False
        self._position_ms = 0
        self._duration_ms = 0
        self._finish_timer_playback_id: int | None = None
        self._finish_timer_delay_ms: int | None = None
        self._finish_timer = None
        if QTimer is not None:
            self._finish_timer = QTimer(self)
            self._finish_timer.setSingleShot(True)
            self._finish_timer.timeout.connect(self._on_finish_timer_timeout)

        self._play_requested.connect(self._play_on_main_thread)
        self._stop_requested.connect(self._stop_on_main_thread)
        if self._player is not None:
            self._player.mediaStatusChanged.connect(self._on_media_status_changed)
            playback_state_changed = getattr(self._player, "playbackStateChanged", None)
            if playback_state_changed is not None:
                playback_state_changed.connect(self._on_playback_state_changed)
            position_changed = getattr(self._player, "positionChanged", None)
            if position_changed is not None:
                position_changed.connect(self._on_position_changed)
            duration_changed = getattr(self._player, "durationChanged", None)
            if duration_changed is not None:
                duration_changed.connect(self._on_duration_changed)
            self._player.errorOccurred.connect(self._on_error)
        self.set_output_device_id(output_device_id)

    def set_output_device_id(self, output_device_id: str) -> None:
        self._output_device_id = output_device_id or "default"
        if self._output is None:
            return
        device = self._device_service.resolve_output_device(self._output_device_id)
        set_device = getattr(self._output, "setDevice", None)
        if callable(set_device) and device is not None:
            set_device(device)

    def play_blocking(self, audio_path: str, stop_event: Event | None = None) -> str:
        if not Path(audio_path).exists():
            raise ProviderError(f"Speech file does not exist: {audio_path}")

        completion_event = Event()
        with self._lock:
            self._playback_sequence += 1
            playback_id = self._playback_sequence
            self._completion_event = completion_event
            self._completion_playback_id = playback_id
            self._error_message = ""
        self._play_requested.emit(playback_id, audio_path)

        while not completion_event.wait(0.1):
            if stop_event and stop_event.is_set():
                self.stop()
                break

        if self._error_message:
            raise ProviderError(self._error_message)
        return audio_path

    def stop(self) -> None:
        self._stop_requested.emit()

    @Slot(int, str)
    def _play_on_main_thread(self, playback_id: int, audio_path: str) -> None:
        self._stop_active_playback(interrupted=True)
        self._active_playback_id = playback_id
        self._reset_playback_tracking()

        if self._should_use_audio_sink(audio_path):
            self._playback_backend = "sink"
            try:
                self._start_wav_playback(audio_path)
            except Exception as exc:
                self._error_message = str(exc) or "Audio playback failed."
                self._finish_playback(playback_id)
            return

        if self._player is None or QUrl is None:
            self._error_message = "Audio playback is unavailable for this file format."
            self._finish_playback(playback_id)
            return

        self._playback_backend = "media"
        self._player.setSource(QUrl.fromLocalFile(audio_path))
        self._player.play()

    @Slot()
    def _stop_on_main_thread(self) -> None:
        self._stop_active_playback(interrupted=True)
        self._finish_playback()

    @Slot(object)
    def _on_media_status_changed(self, status) -> None:
        if self._playback_backend != "media" or self._player is None:
            return
        playback_id = self._active_playback_id
        if playback_id is None:
            return
        if status == QMediaPlayer.EndOfMedia:
            self._end_of_media_seen = True
            self._maybe_schedule_finish(playback_id)
        elif status == QMediaPlayer.InvalidMedia:
            self._error_message = (
                "Audio playback failed because the media file was invalid."
            )
            self._finish_playback(playback_id)

    @Slot(object)
    def _on_playback_state_changed(self, state) -> None:
        if self._playback_backend != "media" or self._player is None:
            return
        playback_id = self._active_playback_id
        if playback_id is None:
            return
        if state == QMediaPlayer.PlayingState:
            self._playback_started = True
            self._cancel_finish_timer()
        elif state == QMediaPlayer.StoppedState and self._playback_started:
            self._stopped_after_playback = True
            self._maybe_schedule_finish(playback_id)

    @Slot(int)
    def _on_position_changed(self, position: int) -> None:
        if self._playback_backend != "media":
            return
        playback_id = self._active_playback_id
        if playback_id is None:
            return
        self._position_ms = max(0, int(position))
        if self._position_ms > 0:
            self._playback_started = True
        self._maybe_schedule_finish(playback_id)

    @Slot(int)
    def _on_duration_changed(self, duration: int) -> None:
        if self._playback_backend != "media":
            return
        playback_id = self._active_playback_id
        if playback_id is None:
            return
        self._duration_ms = max(0, int(duration))
        self._maybe_schedule_finish(playback_id)

    @Slot(object, str)
    def _on_error(self, error, error_string: str) -> None:
        del error
        if self._playback_backend != "media":
            return
        playback_id = self._active_playback_id
        self._error_message = error_string or "Audio playback failed."
        self._finish_playback(playback_id)

    @Slot(object)
    def _on_audio_sink_state_changed(self, state) -> None:
        if self._playback_backend != "sink":
            return
        playback_id = self._active_playback_id
        if playback_id is None:
            return
        idle_state = _qaudio_enum("IdleState")
        stopped_state = _qaudio_enum("StoppedState")
        no_error = _qaudio_enum("NoError")
        if state == idle_state:
            self._drain_audio_sink_and_finish(playback_id)
            return
        if state != stopped_state or self._audio_sink is None:
            return
        error = None
        get_error = getattr(self._audio_sink, "error", None)
        if callable(get_error):
            error = get_error()
        if error not in (None, no_error):
            self._error_message = "WAV audio playback failed."
            self._finish_playback(playback_id)

    @Slot()
    def _on_finish_timer_timeout(self) -> None:
        playback_id = self._finish_timer_playback_id
        self._finish_timer_playback_id = None
        self._finish_timer_delay_ms = None
        if playback_id is None or playback_id != self._active_playback_id:
            return
        if not self._playback_completion_candidate_detected():
            return
        self._finish_playback(playback_id)

    def _finish_playback(self, playback_id: int | None = None) -> None:
        self._cancel_finish_timer()
        if playback_id is None or playback_id == self._active_playback_id:
            if self._playback_backend == "sink":
                self._teardown_audio_sink(interrupted=False)
            self._playback_backend = ""
            self._active_playback_id = None
            self._reset_playback_tracking()
        with self._lock:
            if (
                playback_id is not None
                and self._completion_playback_id is not None
                and playback_id != self._completion_playback_id
            ):
                return
            completion_event = self._completion_event
            self._completion_event = None
            self._completion_playback_id = None
        if completion_event is not None:
            completion_event.set()

    def _stop_active_playback(self, *, interrupted: bool) -> None:
        self._cancel_finish_timer()
        self._active_playback_id = None
        self._reset_playback_tracking()
        self._playback_backend = ""
        if self._player is not None:
            self._player.stop()
        self._teardown_audio_sink(interrupted=interrupted)

    def _maybe_schedule_finish(self, playback_id: int) -> None:
        if playback_id != self._active_playback_id:
            return
        if not self._playback_started:
            return
        if not self._playback_completion_candidate_detected():
            return
        delay_ms = self._completion_delay_ms()
        if delay_ms is None:
            return
        self._schedule_finish_playback(playback_id, delay_ms)

    def _schedule_finish_playback(
        self,
        playback_id: int,
        delay_ms: int,
    ) -> None:
        if QTimer is None or self._finish_timer is None:
            self._finish_playback(playback_id)
            return
        if (
            self._finish_timer_playback_id == playback_id
            and self._finish_timer_delay_ms == delay_ms
            and self._finish_timer.isActive()
        ):
            return
        self._finish_timer.stop()
        self._finish_timer_playback_id = playback_id
        self._finish_timer_delay_ms = delay_ms
        self._finish_timer.start(delay_ms)

    def _cancel_finish_timer(self) -> None:
        if self._finish_timer is not None:
            self._finish_timer.stop()
        self._finish_timer_playback_id = None
        self._finish_timer_delay_ms = None

    def _playback_completion_candidate_detected(self) -> bool:
        return self._end_of_media_seen or self._stopped_after_playback

    def _completion_delay_ms(self) -> int | None:
        if not self._playback_completion_candidate_detected():
            return None
        if self._duration_ms > 0:
            remaining_ms = max(0, self._duration_ms - self._position_ms)
            return min(
                self._PLAYBACK_COMPLETION_TIMEOUT_MS,
                remaining_ms + self._PLAYBACK_COMPLETION_GRACE_MS,
            )
        if self._end_of_media_seen:
            return self._PLAYBACK_COMPLETION_GRACE_MS
        return None

    def _reset_playback_tracking(self) -> None:
        self._playback_started = False
        self._end_of_media_seen = False
        self._stopped_after_playback = False
        self._position_ms = 0
        self._duration_ms = 0

    def _drain_audio_sink_and_finish(self, playback_id: int) -> None:
        if playback_id != self._active_playback_id or self._audio_sink is None:
            return
        self._disconnect_audio_sink_state_changed(self._audio_sink)
        stop_audio = getattr(self._audio_sink, "stop", None)
        if callable(stop_audio):
            stop_audio()
        self._finish_playback(playback_id)

    def _disconnect_audio_sink_state_changed(self, audio_sink) -> None:
        if not self._audio_sink_state_connected:
            return
        state_changed = getattr(audio_sink, "stateChanged", None)
        disconnect = getattr(state_changed, "disconnect", None)
        if callable(disconnect):
            try:
                disconnect(self._on_audio_sink_state_changed)
            except Exception:  # pragma: no cover - defensive runtime cleanup.
                pass
        self._audio_sink_state_connected = False

    def _should_use_audio_sink(self, audio_path: str) -> bool:
        return self._wav_playback_available() and _is_riff_wave_file(Path(audio_path))

    def _wav_playback_available(self) -> bool:
        return all(
            dependency is not None
            for dependency in (
                QByteArray,
                QAudioFormat,
                QAudioSink,
                QBuffer,
                QIODevice,
            )
        )

    def _start_wav_playback(self, audio_path: str) -> None:
        audio_format, audio_frames = self._load_wav_frames(Path(audio_path))
        self._audio_bytes = QByteArray(audio_frames)
        self._audio_buffer = QBuffer(self)
        self._audio_buffer.setData(self._audio_bytes)
        if not self._audio_buffer.open(QIODevice.ReadOnly):
            raise ProviderError(
                "WAV audio playback could not open the decoded audio buffer."
            )

        device = self._device_service.resolve_output_device(self._output_device_id)
        if device is None:
            self._audio_sink = QAudioSink(audio_format, self)
        else:
            self._audio_sink = QAudioSink(device, audio_format, self)
        self._audio_sink.stateChanged.connect(self._on_audio_sink_state_changed)
        self._audio_sink_state_connected = True
        self._playback_started = True
        self._audio_sink.start(self._audio_buffer)

    def _load_wav_frames(self, audio_path: Path):
        if QAudioFormat is None:
            raise ProviderError("WAV audio playback is unavailable.")
        with wave.open(str(audio_path), "rb") as wav_file:
            if wav_file.getcomptype() != "NONE":
                raise ProviderError("Compressed WAV playback is unsupported.")
            audio_format = QAudioFormat()
            audio_format.setChannelCount(wav_file.getnchannels())
            audio_format.setSampleRate(wav_file.getframerate())
            self._configure_wav_sample_format(audio_format, wav_file.getsampwidth())
            return audio_format, wav_file.readframes(wav_file.getnframes())

    def _configure_wav_sample_format(
        self, audio_format, sample_width_bytes: int
    ) -> None:
        if hasattr(audio_format, "setSampleFormat"):
            sample_format = _resolve_sample_format(sample_width_bytes)
            if sample_format is None:
                raise ProviderError(
                    f"Unsupported WAV sample width: {sample_width_bytes * 8} bits."
                )
            audio_format.setSampleFormat(sample_format)
            return
        set_sample_size = getattr(audio_format, "setSampleSize", None)
        set_codec = getattr(audio_format, "setCodec", None)
        set_byte_order = getattr(audio_format, "setByteOrder", None)
        set_sample_type = getattr(audio_format, "setSampleType", None)
        if not all(
            callable(method) for method in (set_sample_size, set_codec, set_sample_type)
        ):
            raise ProviderError(
                "WAV audio playback could not configure the output format."
            )
        set_sample_size(sample_width_bytes * 8)
        set_codec("audio/pcm")
        little_endian = getattr(QAudioFormat, "LittleEndian", None)
        if callable(set_byte_order) and little_endian is not None:
            set_byte_order(little_endian)
        sample_type = _resolve_legacy_sample_type(sample_width_bytes)
        if sample_type is None:
            raise ProviderError(
                f"Unsupported WAV sample width: {sample_width_bytes * 8} bits."
            )
        set_sample_type(sample_type)

    def _teardown_audio_sink(self, *, interrupted: bool) -> None:
        audio_sink = self._audio_sink
        audio_buffer = self._audio_buffer
        self._audio_sink = None
        self._audio_buffer = None
        self._audio_bytes = None
        if audio_sink is not None:
            self._disconnect_audio_sink_state_changed(audio_sink)
            if interrupted:
                reset_audio = getattr(audio_sink, "reset", None)
                if callable(reset_audio):
                    reset_audio()
                else:
                    stop_audio = getattr(audio_sink, "stop", None)
                    if callable(stop_audio):
                        stop_audio()
            delete_later = getattr(audio_sink, "deleteLater", None)
            if callable(delete_later):
                delete_later()
        if audio_buffer is not None:
            close_buffer = getattr(audio_buffer, "close", None)
            if callable(close_buffer):
                close_buffer()
            delete_later = getattr(audio_buffer, "deleteLater", None)
            if callable(delete_later):
                delete_later()


def _resolve_sample_format(sample_width_bytes: int):
    sample_format_enum = getattr(QAudioFormat, "SampleFormat", None)
    if sample_width_bytes == 1:
        return _enum_value(sample_format_enum, QAudioFormat, "UInt8")
    if sample_width_bytes == 2:
        return _enum_value(sample_format_enum, QAudioFormat, "Int16")
    if sample_width_bytes == 4:
        return _enum_value(sample_format_enum, QAudioFormat, "Int32")
    return None


def _resolve_legacy_sample_type(sample_width_bytes: int):
    if sample_width_bytes == 1:
        return getattr(QAudioFormat, "UnSignedInt", None)
    if sample_width_bytes in (2, 4):
        return getattr(QAudioFormat, "SignedInt", None)
    return None


def _enum_value(enum_type, owner, name: str):
    if enum_type is not None and hasattr(enum_type, name):
        return getattr(enum_type, name)
    return getattr(owner, name, None)


def _qaudio_enum(name: str):
    audio_state_enum = getattr(QAudio, "State", None)
    audio_error_enum = getattr(QAudio, "Error", None)
    if audio_state_enum is not None and hasattr(audio_state_enum, name):
        return getattr(audio_state_enum, name)
    if audio_error_enum is not None and hasattr(audio_error_enum, name):
        return getattr(audio_error_enum, name)
    return getattr(QAudio, name, None)


def _is_riff_wave_file(audio_path: Path) -> bool:
    try:
        header = audio_path.read_bytes()[:12]
    except OSError:
        return False
    return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
