from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from threading import Event, Thread
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from PySide6.QtCore import Property, QCoreApplication, QTimer, QObject, Signal, Slot

from src.exceptions.app_exceptions import ValidationError
from src.models.settings import (
    AUTO_TTS_VOICE_ID,
    AppSettings,
    ELEVEN_V3_VOICES,
    TTS_VOICE_OPTIONS,
    get_tts_voice,
    get_tts_voice_label,
)
from src.services.audio_devices import AudioDeviceOption, AudioDeviceService
from src.services.audio_monitor import AudioMonitorService
from src.services.audio_playback import QtAudioPlaybackService
from src.services.audio_signal import AudioTestSignalService
from src.services.history_manager import HistoryManager
from src.services.keybinds import (
    keybinds_are_unique,
    normalize_keybind,
    qt_event_to_keybind,
)
from src.services.providers import NagaSpeechProvider
from src.services.settings_manager import SettingsManager


class SettingsViewModel(QObject):
    _AUTOSAVE_DELAY_MS = 350
    _SUCCESS_STATUS_DURATION_MS = 2200
    _TRANSIENT_INFO_STATUS_DURATION_MS = 2200
    _STATUS_REPLACE_DELAY_MS = 180
    _IMMEDIATE_AUTOSAVE_FIELDS = {
        "llm_reasoning",
        "transcription_reasoning",
        "tts_model",
        "tts_voice_id",
        "fallback_language",
        "audio_input_device",
        "audio_output_device",
        "theme_preference",
    }

    settingsChanged = Signal()
    savedSettingsChanged = Signal()
    errorsChanged = Signal()
    dirtyChanged = Signal()
    savingChanged = Signal()
    statusChanged = Signal()
    audioDevicesChanged = Signal()
    audioTestChanged = Signal()
    currentSectionChanged = Signal()
    bindingChanged = Signal()
    previewChanged = Signal()
    _previewStatusRequested = Signal(str, str)
    _previewStarted = Signal(str)
    _previewFinished = Signal(str)
    _audioLevelRequested = Signal(float)
    _audioInputTestFinished = Signal()
    _speakerTestFinished = Signal()

    def __init__(
        self,
        settings_manager: SettingsManager,
        history_manager: HistoryManager,
        audio_dir: Path | None = None,
        audio_device_service: AudioDeviceService | None = None,
        audio_monitor_factory: Callable[[AppSettings], AudioMonitorService]
        | None = None,
        audio_signal_service: AudioTestSignalService | None = None,
        playback_service_factory: Callable[[], QtAudioPlaybackService] | None = None,
    ) -> None:
        super().__init__()
        self._settings_manager = settings_manager
        self._history_manager = history_manager
        self._audio_dir = audio_dir
        self._audio_device_service = audio_device_service or AudioDeviceService()
        self._audio_monitor_factory = audio_monitor_factory or (
            lambda settings: AudioMonitorService(
                settings,
                device_service=self._audio_device_service,
            )
        )
        self._audio_signal_service = audio_signal_service or AudioTestSignalService()
        self._playback_service_factory = playback_service_factory or (
            lambda: QtAudioPlaybackService(device_service=self._audio_device_service)
        )
        current_settings = settings_manager.load()
        self._baseline_map = current_settings.to_dict()
        self._settings_map = deepcopy(self._baseline_map)
        self._errors: dict[str, str] = {}
        self._dirty = False
        self._saving = False
        self._status_message = ""
        self._status_kind = "neutral"
        self._status_revision = 0
        self._current_section = "api"
        self._binding_field = ""
        self._previewing_voice = ""
        self._preview_thread: Thread | None = None
        self._preview_stop_event: Event | None = None
        self._preview_playback_service: QtAudioPlaybackService | None = None
        self._audio_input_options = ["default"]
        self._audio_output_options = ["default"]
        self._audio_input_labels = {"default": "System Default Input"}
        self._audio_output_labels = {"default": "System Default Output"}
        self._audio_device_status = ""
        self._audio_input_level = 0.0
        self._audio_input_test_thread: Thread | None = None
        self._audio_input_test_stop_event: Event | None = None
        self._speaker_test_thread: Thread | None = None
        self._speaker_test_stop_event: Event | None = None
        self._previewStatusRequested.connect(self._apply_status_update)
        self._previewStarted.connect(self._handle_preview_started)
        self._previewFinished.connect(self._handle_preview_finished)
        self._audioLevelRequested.connect(self._apply_audio_level)
        self._audioInputTestFinished.connect(self._handle_audio_input_test_finished)
        self._speakerTestFinished.connect(self._handle_speaker_test_finished)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._apply_autosave)
        self.refreshAudioDevices()
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self) -> dict[str, Any]:
        return dict(self._settings_map)

    @Property("QVariantMap", notify=errorsChanged)
    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(bool, notify=savingChanged)
    def saving(self) -> bool:
        return self._saving

    @Property(str, notify=statusChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=statusChanged)
    def statusKind(self) -> str:
        return self._status_kind

    @Property("QStringList", notify=audioDevicesChanged)
    def audioDeviceOptions(self) -> list[str]:
        return list(self._audio_input_options)

    @Property("QStringList", notify=audioDevicesChanged)
    def audioInputDeviceOptions(self) -> list[str]:
        return list(self._audio_input_options)

    @Property("QVariantMap", notify=audioDevicesChanged)
    def audioInputDeviceLabels(self) -> dict[str, str]:
        return dict(self._audio_input_labels)

    @Property("QStringList", notify=audioDevicesChanged)
    def audioOutputDeviceOptions(self) -> list[str]:
        return list(self._audio_output_options)

    @Property("QVariantMap", notify=audioDevicesChanged)
    def audioOutputDeviceLabels(self) -> dict[str, str]:
        return dict(self._audio_output_labels)

    @Property(str, notify=audioDevicesChanged)
    def audioDeviceStatusMessage(self) -> str:
        return self._audio_device_status

    @Property(float, notify=audioTestChanged)
    def audioInputLevel(self) -> float:
        return self._audio_input_level

    @Property(bool, notify=audioTestChanged)
    def audioInputTestActive(self) -> bool:
        return self._audio_input_test_thread is not None

    @Property(bool, notify=audioTestChanged)
    def speakerTestActive(self) -> bool:
        return self._speaker_test_thread is not None

    @Property(str, notify=currentSectionChanged)
    def currentSection(self) -> str:
        return self._current_section

    @Property(str, notify=bindingChanged)
    def bindingField(self) -> str:
        return self._binding_field

    @Property(bool, notify=bindingChanged)
    def bindingActive(self) -> bool:
        return bool(self._binding_field)

    @Property(str, notify=previewChanged)
    def previewingVoice(self) -> str:
        return self._previewing_voice

    @Property(bool, notify=previewChanged)
    def previewActive(self) -> bool:
        return bool(self._previewing_voice)

    @Property("QStringList", constant=True)
    def themeOptions(self) -> list[str]:
        return ["dark", "light", "system"]

    @Property("QStringList", constant=True)
    def reasoningOptions(self) -> list[str]:
        return ["minimal", "low", "medium", "high"]

    @Property("QStringList", constant=True)
    def transcriptionReasoningOptions(self) -> list[str]:
        return ["minimal", "low", "medium", "high"]

    @Property("QStringList", constant=True)
    def ttsModelOptions(self) -> list[str]:
        return ["eleven-v3"]

    @Property("QStringList", constant=True)
    def voiceOptions(self) -> list[str]:
        return TTS_VOICE_OPTIONS

    @Property("QVariantMap", constant=True)
    def voiceOptionLabels(self) -> dict[str, str]:
        return {
            voice_id: get_tts_voice_label(voice_id) for voice_id in TTS_VOICE_OPTIONS
        }

    @Property("QStringList", constant=True)
    def languageOptions(self) -> list[str]:
        return ["en", "lt", "fr", "de", "es"]

    @Slot(str)
    def setCurrentSection(self, section: str) -> None:
        if section == self._current_section:
            return
        if section != "voice":
            self.stopVoicePreview()
        if section != "audio":
            self.stopAudioInputTest()
            self.stopSpeakerTest()
        self._current_section = section
        self.currentSectionChanged.emit()

    @Slot(str, "QVariant")
    def setField(self, field_name: str, value: Any) -> None:
        if field_name not in self._settings_map:
            return
        normalized_value = value
        if isinstance(value, str):
            normalized_value = value
        if field_name.endswith("_keybind"):
            normalized_value = normalize_keybind(str(value))
        if self._settings_map[field_name] == normalized_value:
            return
        self._settings_map[field_name] = normalized_value
        if field_name in self._errors:
            self._errors.pop(field_name, None)
            self.errorsChanged.emit()
        self._recompute_dirty()
        self.settingsChanged.emit()
        if field_name.endswith("_keybind"):
            return
        self._schedule_autosave(field_name)

    @Slot()
    def save(self) -> None:
        self._autosave_timer.stop()
        settings = self._validate_current_settings()
        if settings is None:
            return
        self._set_saving(True)
        try:
            self._persist_settings(settings, status_message="Settings saved.")
        finally:
            if QCoreApplication.instance() is None:
                self._clear_saving()
            else:
                QTimer.singleShot(350, self._clear_saving)

    @Slot()
    def reset(self) -> None:
        self._autosave_timer.stop()
        self._settings_map = deepcopy(self._baseline_map)
        self._errors = {}
        self._dirty = False
        self._set_status("Changes reset.", "neutral")
        self.settingsChanged.emit()
        self.errorsChanged.emit()
        self.dirtyChanged.emit()

    @Slot()
    def validateDraft(self) -> None:
        self._autosave_timer.stop()
        settings = self._validate_current_settings()
        if settings is None:
            return
        del settings
        self._set_status(
            "These settings look valid and will be used the next time Glance starts.",
            "success",
        )

    @Slot()
    def clearHistory(self) -> None:
        self._history_manager.clear()
        self._set_status("Saved history cleared.", "success")

    @Slot(str)
    def startKeybindCapture(self, field_name: str) -> None:
        if field_name not in {"live_keybind", "quick_keybind", "ocr_keybind"}:
            return
        self._binding_field = field_name
        self.bindingChanged.emit()
        self._set_status("Press a new shortcut now. Press Escape to cancel.", "neutral")

    @Slot()
    def cancelKeybindCapture(self) -> None:
        if not self._binding_field:
            return
        self._binding_field = ""
        self.bindingChanged.emit()
        self._set_status("Shortcut capture cancelled.", "neutral")

    @Slot(int, int, str)
    def captureKeybind(self, key: int, modifiers: int, text: str) -> None:
        if not self._binding_field:
            return
        keybind = qt_event_to_keybind(key, modifiers, text)
        if keybind is None:
            return
        if keybind == "ESC":
            self.cancelKeybindCapture()
            return
        field_name = self._binding_field
        conflicts_with = self._find_keybind_conflict(field_name, keybind)
        if conflicts_with is not None:
            self._errors[field_name] = f"Already used by {conflicts_with}."
            self.errorsChanged.emit()
            self._set_status(
                "Choose a different shortcut so every mode stays unique.", "error"
            )
            return
        self._binding_field = ""
        self.bindingChanged.emit()
        self.setField(field_name, keybind)
        self._persist_keybind_change(field_name, keybind)
        self._set_status(
            f"{self._binding_label(field_name)} shortcut set to {keybind}.", "success"
        )

    @Slot(str, str)
    def assignKeybind(self, field_name: str, keybind: str) -> None:
        if field_name not in {"live_keybind", "quick_keybind", "ocr_keybind"}:
            return
        try:
            normalized_keybind = normalize_keybind(keybind)
        except ValidationError as exc:
            self._errors[field_name] = str(exc)
            self.errorsChanged.emit()
            self._set_status(str(exc), "error")
            return

        conflicts_with = self._find_keybind_conflict(field_name, normalized_keybind)
        if conflicts_with is not None:
            self._errors[field_name] = f"Already used by {conflicts_with}."
            self.errorsChanged.emit()
            self._set_status(
                "Choose a different shortcut so every mode stays unique.", "error"
            )
            return

        if self._binding_field:
            self._binding_field = ""
            self.bindingChanged.emit()
        self.setField(field_name, normalized_keybind)
        self._persist_keybind_change(field_name, normalized_keybind)
        self._set_status(
            f"{self._binding_label(field_name)} shortcut set to {normalized_keybind}.",
            "success",
        )

    @Slot(str)
    def previewVoice(self, voice_name: str) -> None:
        if self._previewing_voice == voice_name:
            self.stopVoicePreview()
            return

        preview_settings = self._build_preview_settings(voice_name)
        if preview_settings is None:
            return

        try:
            self.stopSpeakerTest()
            self._prepare_preview_playback_service(preview_settings.audio_output_device)
        except Exception as exc:
            self._set_status(f"Voice preview unavailable: {exc}", "error")
            return

        self.stopVoicePreview()
        stop_event = Event()
        self._preview_stop_event = stop_event
        preview_thread = Thread(
            target=self._run_voice_preview,
            args=(preview_settings, voice_name, stop_event),
            name="glance-voice-preview",
            daemon=True,
        )
        self._preview_thread = preview_thread
        self._previewStarted.emit(voice_name)
        preview_thread.start()

    @Slot()
    def stopVoicePreview(self) -> None:
        stop_event = self._preview_stop_event
        if stop_event is not None:
            stop_event.set()
        if self._preview_playback_service is not None:
            self._preview_playback_service.stop()

    @Slot()
    def refreshAudioDevices(self) -> None:
        try:
            input_options = self._audio_device_service.list_input_devices()
            output_options = self._audio_device_service.list_output_devices()
        except Exception as exc:
            self._audio_input_options = ["default"]
            self._audio_output_options = ["default"]
            self._audio_input_labels = {"default": "System Default Input"}
            self._audio_output_labels = {"default": "System Default Output"}
            self._audio_device_status = f"Device list unavailable: {exc}"
            self.audioDevicesChanged.emit()
            return

        (
            self._audio_input_options,
            self._audio_input_labels,
        ) = self._build_audio_option_state(
            input_options,
            str(self._settings_map.get("audio_input_device", "default")),
            "Saved input device unavailable",
        )
        (
            self._audio_output_options,
            self._audio_output_labels,
        ) = self._build_audio_option_state(
            output_options,
            str(self._settings_map.get("audio_output_device", "default")),
            "Saved output device unavailable",
        )

        discovered_inputs = max(0, len(input_options) - 1)
        discovered_outputs = max(0, len(output_options) - 1)
        if discovered_inputs == 0 and discovered_outputs == 0:
            self._audio_device_status = "Using system default audio devices."
        else:
            self._audio_device_status = f"{discovered_inputs} input device(s) and {discovered_outputs} output device(s) available."
        self.audioDevicesChanged.emit()

    @Slot()
    def startAudioInputTest(self) -> None:
        if self._audio_input_test_thread is not None:
            return
        settings = self._build_runtime_settings("Audio input test unavailable")
        if settings is None:
            return
        self.stopVoicePreview()
        self.stopSpeakerTest()
        stop_event = Event()
        self._audio_input_test_stop_event = stop_event
        self._audio_input_level = 0.0
        thread = Thread(
            target=self._run_audio_input_test,
            args=(settings, stop_event),
            name="glance-audio-input-test",
            daemon=True,
        )
        self._audio_input_test_thread = thread
        self.audioTestChanged.emit()
        self._set_status("Monitoring microphone input.", "neutral")
        thread.start()

    @Slot()
    def stopAudioInputTest(self) -> None:
        stop_event = self._audio_input_test_stop_event
        if stop_event is not None:
            stop_event.set()

    @Slot()
    def playSpeakerTest(self) -> None:
        if self._speaker_test_thread is not None:
            return
        settings = self._build_runtime_settings("Speaker test unavailable")
        if settings is None:
            return
        try:
            self.stopAudioInputTest()
            self.stopVoicePreview()
            self._prepare_preview_playback_service(settings.audio_output_device)
        except Exception as exc:
            self._set_status(f"Speaker test unavailable: {exc}", "error")
            return

        stop_event = Event()
        self._speaker_test_stop_event = stop_event
        thread = Thread(
            target=self._run_speaker_test,
            args=(stop_event,),
            name="glance-speaker-test",
            daemon=True,
        )
        self._speaker_test_thread = thread
        self.audioTestChanged.emit()
        self._set_status("Playing speaker test.", "neutral")
        thread.start()

    @Slot()
    def stopSpeakerTest(self) -> None:
        stop_event = self._speaker_test_stop_event
        if stop_event is not None:
            stop_event.set()
        if self._preview_playback_service is not None:
            self._preview_playback_service.stop()

    @Slot()
    def resetAudioDefaults(self) -> None:
        defaults = AppSettings()
        audio_fields = (
            "audio_input_device",
            "audio_output_device",
            "audio_activation_threshold",
            "audio_silence_seconds",
            "audio_max_wait_seconds",
            "audio_max_record_seconds",
            "audio_preroll_seconds",
        )
        updated = False
        for field_name in audio_fields:
            default_value = getattr(defaults, field_name)
            if self._settings_map.get(field_name) == default_value:
                continue
            self._settings_map[field_name] = default_value
            updated = True
            self._errors.pop(field_name, None)
        if not updated:
            self._set_transient_status(
                "Audio settings are already using the defaults.", "neutral"
            )
            return
        self.stopAudioInputTest()
        self.stopSpeakerTest()
        self.refreshAudioDevices()
        self._recompute_dirty()
        self.settingsChanged.emit()
        self.errorsChanged.emit()
        self._schedule_autosave("audio_output_device")
        self._set_status("Audio settings reset to the defaults.", "success")

    def _validate_current_settings(
        self, *, show_status: bool = True
    ) -> AppSettings | None:
        payload = deepcopy(self._settings_map)
        errors: dict[str, str] = {}

        self._validate_optional_url(payload, "llm_base_url", errors)
        self._validate_optional_url(payload, "transcription_base_url", errors)
        self._require_text(payload, "llm_model_name", errors)
        self._validate_optional_url(payload, "tts_base_url", errors)
        self._require_text(payload, "tts_model", errors)
        self._require_text(payload, "tts_voice_id", errors)
        self._require_text(payload, "fallback_language", errors)
        self._require_text(payload, "live_keybind", errors)
        self._require_text(payload, "quick_keybind", errors)
        self._require_text(payload, "ocr_keybind", errors)
        self._require_text(payload, "transcription_model_name", errors)
        self._coerce_positive_int(payload, "history_length", errors)
        self._coerce_positive_float(payload, "screenshot_interval", errors)
        self._coerce_positive_float(payload, "batch_window_duration", errors)
        self._coerce_ratio(payload, "screen_change_threshold", errors)
        self._coerce_ratio(payload, "audio_activation_threshold", errors)
        self._coerce_positive_float(payload, "audio_silence_seconds", errors)
        self._coerce_positive_float(payload, "audio_max_wait_seconds", errors)
        self._coerce_positive_float(payload, "audio_max_record_seconds", errors)
        self._coerce_non_negative_float(payload, "audio_preroll_seconds", errors)
        self._coerce_theme(payload, "theme_preference", errors)

        for keybind_field in ("live_keybind", "quick_keybind", "ocr_keybind"):
            if keybind_field not in errors:
                try:
                    payload[keybind_field] = normalize_keybind(payload[keybind_field])
                except ValidationError as exc:
                    errors[keybind_field] = str(exc)

        if not errors and not keybinds_are_unique(
            [
                payload["live_keybind"],
                payload["quick_keybind"],
                payload["ocr_keybind"],
            ]
        ):
            duplicate_message = "Each shortcut must be unique."
            errors["live_keybind"] = duplicate_message
            errors["quick_keybind"] = duplicate_message
            errors["ocr_keybind"] = duplicate_message

        if errors:
            self._errors = errors
            self.errorsChanged.emit()
            if show_status:
                self._set_status("Fix the highlighted fields before saving.", "error")
            return None

        try:
            settings = AppSettings.from_mapping(payload, validate=False)
        except (ValidationError, ValueError) as exc:
            self._errors = {"general": str(exc)}
            self.errorsChanged.emit()
            if show_status:
                self._set_status(str(exc), "error")
            return None

        self._errors = {}
        self.errorsChanged.emit()
        return settings

    def _recompute_dirty(self) -> None:
        new_dirty = self._settings_map != self._baseline_map
        if new_dirty == self._dirty:
            return
        self._dirty = new_dirty
        self.dirtyChanged.emit()

    def _set_status(self, message: str, kind: str) -> None:
        self._status_revision += 1
        duration_ms = (
            self._SUCCESS_STATUS_DURATION_MS if message and kind == "success" else None
        )
        self._apply_status(message, kind, duration_ms)

    def _set_transient_status(self, message: str, kind: str = "neutral") -> None:
        self._status_revision += 1
        revision = self._status_revision
        if self._status_message:
            self._clear_status()
            QTimer.singleShot(
                self._STATUS_REPLACE_DELAY_MS,
                lambda: self._apply_deferred_transient_status(
                    revision,
                    message,
                    kind,
                    self._TRANSIENT_INFO_STATUS_DURATION_MS,
                ),
            )
            return
        self._apply_deferred_transient_status(
            revision,
            message,
            kind,
            self._TRANSIENT_INFO_STATUS_DURATION_MS,
        )

    def _apply_deferred_transient_status(
        self,
        revision: int,
        message: str,
        kind: str,
        duration_ms: int,
    ) -> None:
        if revision != self._status_revision:
            return
        self._apply_status(message, kind, duration_ms)

    def _apply_status(
        self,
        message: str,
        kind: str,
        duration_ms: int | None,
    ) -> None:
        self._status_message = message
        self._status_kind = kind if message else "neutral"
        if message and duration_ms is not None:
            self._status_timer.start(duration_ms)
        else:
            self._status_timer.stop()
        self.statusChanged.emit()

    def _clear_status(self) -> None:
        self._status_timer.stop()
        if not self._status_message:
            return
        self._status_message = ""
        self._status_kind = "neutral"
        self.statusChanged.emit()

    def _set_saving(self, value: bool) -> None:
        if self._saving == value:
            return
        self._saving = value
        self.savingChanged.emit()

    def _clear_saving(self) -> None:
        self._set_saving(False)

    @Slot(str, str)
    def _apply_status_update(self, message: str, kind: str) -> None:
        self._set_status(message, kind)

    @Slot(float)
    def _apply_audio_level(self, level: float) -> None:
        self._audio_input_level = level
        self.audioTestChanged.emit()

    @Slot(str)
    def _handle_preview_started(self, voice_name: str) -> None:
        self._previewing_voice = voice_name
        self.previewChanged.emit()
        self._set_status(
            f"Previewing {self._voice_preview_label(voice_name)}.", "neutral"
        )

    @Slot(str)
    def _handle_preview_finished(self, voice_name: str) -> None:
        if self._previewing_voice != voice_name:
            return
        self._previewing_voice = ""
        self._preview_stop_event = None
        self._preview_thread = None
        self.previewChanged.emit()

    @Slot()
    def _handle_audio_input_test_finished(self) -> None:
        self._audio_input_test_stop_event = None
        self._audio_input_test_thread = None
        self._audio_input_level = 0.0
        self.audioTestChanged.emit()

    @Slot()
    def _handle_speaker_test_finished(self) -> None:
        self._speaker_test_stop_event = None
        self._speaker_test_thread = None
        self.audioTestChanged.emit()

    def _find_keybind_conflict(self, current_field: str, value: str) -> str | None:
        for field_name in ("live_keybind", "quick_keybind", "ocr_keybind"):
            if field_name == current_field:
                continue
            if normalize_keybind(str(self._settings_map.get(field_name, ""))) == value:
                return self._binding_label(field_name)
        return None

    @staticmethod
    def _binding_label(field_name: str) -> str:
        labels = {
            "live_keybind": "Live",
            "quick_keybind": "Quick",
            "ocr_keybind": "OCR",
        }
        return labels.get(field_name, field_name)

    def _persist_keybind_change(self, field_name: str, value: str) -> None:
        persisted_payload = deepcopy(self._baseline_map)
        persisted_payload[field_name] = value
        settings = AppSettings.from_mapping(persisted_payload, validate=False)
        self._settings_manager.save(settings, validate=False)
        self._baseline_map[field_name] = value
        self._recompute_dirty()

    def _build_preview_settings(self, voice_name: str) -> AppSettings | None:
        if voice_name == AUTO_TTS_VOICE_ID:
            self._set_status("Choose a fixed voice to preview.", "error")
            return None
        if get_tts_voice(voice_name) is None:
            self._set_status("Choose a valid voice to preview.", "error")
            return None

        settings = self._build_runtime_settings("Voice preview failed")
        if settings is None:
            return None

        payload = settings.to_dict()
        payload["tts_voice_id"] = voice_name
        missing_fields: list[str] = []
        for field_name, label in (
            ("tts_base_url", "speech base URL"),
            ("tts_api_key", "speech API key"),
            ("tts_model", "speech model"),
        ):
            if not str(payload.get(field_name, "")).strip():
                missing_fields.append(label)
        if missing_fields:
            self._set_status(
                f"Voice preview needs {', '.join(missing_fields)}.", "error"
            )
            return None

        try:
            return AppSettings.from_mapping(payload, validate=False)
        except (ValidationError, ValueError) as exc:
            self._set_status(f"Voice preview failed: {exc}", "error")
            return None

    def _ensure_preview_playback_service(self) -> QtAudioPlaybackService:
        if self._audio_dir is None:
            raise ValidationError("audio output is not available in settings")
        if self._preview_playback_service is None:
            self._preview_playback_service = self._playback_service_factory()
        return self._preview_playback_service

    def _prepare_preview_playback_service(
        self, output_device_id: str
    ) -> QtAudioPlaybackService:
        playback_service = self._ensure_preview_playback_service()
        set_output_device = getattr(playback_service, "set_output_device_id", None)
        if callable(set_output_device):
            set_output_device(output_device_id)
        return playback_service

    def _run_voice_preview(
        self, settings: AppSettings, voice_name: str, stop_event: Event
    ) -> None:
        output_path = self._audio_dir / f"voice-preview-{uuid4().hex}.wav"
        try:
            provider = NagaSpeechProvider(settings)
            provider.synthesize(
                text=(
                    f"Hello, I am {self._voice_preview_label(voice_name)}. "
                    "This is how I sound in Glance."
                ),
                output_path=output_path,
            )
            if stop_event.is_set():
                return
            playback_service = self._ensure_preview_playback_service()
            playback_service.play_blocking(str(output_path), stop_event=stop_event)
            if not stop_event.is_set():
                self._previewStatusRequested.emit(
                    f"Previewed {self._voice_preview_label(voice_name)}.",
                    "success",
                )
        except Exception as exc:
            if not stop_event.is_set():
                self._previewStatusRequested.emit(
                    f"Voice preview failed: {exc}", "error"
                )
        finally:
            self._previewFinished.emit(voice_name)

    @staticmethod
    def _voice_preview_label(voice_name: str) -> str:
        voice = get_tts_voice(voice_name)
        if voice is None:
            return get_tts_voice_label(voice_name)
        return voice.name

    @staticmethod
    def _build_audio_option_state(
        options: list[AudioDeviceOption],
        current_value: str,
        missing_label: str,
    ) -> tuple[list[str], dict[str, str]]:
        values = [option.value for option in options]
        labels = {option.value: option.label for option in options}
        normalized_current_value = current_value or "default"
        if normalized_current_value not in labels:
            values.append(normalized_current_value)
            labels[normalized_current_value] = missing_label
        return values, labels

    def _build_runtime_settings(self, error_prefix: str) -> AppSettings | None:
        try:
            return AppSettings.from_mapping(
                deepcopy(self._settings_map), validate=False
            )
        except (ValidationError, ValueError) as exc:
            self._set_status(f"{error_prefix}: {exc}", "error")
            return None

    def _run_audio_input_test(self, settings: AppSettings, stop_event: Event) -> None:
        try:
            monitor = self._audio_monitor_factory(settings)
            monitor.monitor_levels(
                lambda level: self._audioLevelRequested.emit(level),
                stop_event=stop_event,
            )
        except Exception as exc:
            if not stop_event.is_set():
                self._previewStatusRequested.emit(
                    f"Audio input test failed: {exc}",
                    "error",
                )
        finally:
            self._audioInputTestFinished.emit()

    def _run_speaker_test(self, stop_event: Event) -> None:
        output_path = self._audio_dir / f"speaker-test-{uuid4().hex}.wav"
        try:
            self._audio_signal_service.write_test_tone(output_path)
            if stop_event.is_set():
                return
            playback_service = self._ensure_preview_playback_service()
            playback_service.play_blocking(str(output_path), stop_event=stop_event)
            if not stop_event.is_set():
                self._previewStatusRequested.emit("Speaker test completed.", "success")
        except Exception as exc:
            if not stop_event.is_set():
                self._previewStatusRequested.emit(
                    f"Speaker test failed: {exc}",
                    "error",
                )
        finally:
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._speakerTestFinished.emit()

    def _schedule_autosave(self, field_name: str) -> None:
        if self._settings_map == self._baseline_map:
            self._autosave_timer.stop()
            return
        if (
            QCoreApplication.instance() is None
            or field_name in self._IMMEDIATE_AUTOSAVE_FIELDS
        ):
            self._autosave_timer.stop()
            self._apply_autosave()
            return
        self._autosave_timer.start(self._AUTOSAVE_DELAY_MS)

    def _apply_autosave(self) -> None:
        settings = self._validate_current_settings(show_status=False)
        if settings is None or self._settings_map == self._baseline_map:
            return
        self._persist_settings(settings, status_message="Settings updated.")

    def _persist_settings(self, settings: AppSettings, *, status_message: str) -> None:
        self._settings_manager.save(settings, validate=False)
        self._baseline_map = settings.to_dict()
        self._settings_map = deepcopy(self._baseline_map)
        self._errors = {}
        self._set_status(status_message, "success")
        self._dirty = False
        self.savedSettingsChanged.emit()
        self.settingsChanged.emit()
        self.errorsChanged.emit()
        self.dirtyChanged.emit()

    @staticmethod
    def _require_text(
        payload: dict[str, Any], field_name: str, errors: dict[str, str]
    ) -> None:
        value = str(payload.get(field_name, "")).strip()
        payload[field_name] = value
        if not value:
            errors[field_name] = "This field cannot be empty."

    def _validate_optional_url(
        self,
        payload: dict[str, Any],
        field_name: str,
        errors: dict[str, str],
    ) -> None:
        value = str(payload.get(field_name, "")).strip()
        payload[field_name] = value
        if not value:
            return
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors[field_name] = (
                "Enter a valid URL, for example https://api.example.com/v1."
            )

    @staticmethod
    def _coerce_positive_int(
        payload: dict[str, Any],
        field_name: str,
        errors: dict[str, str],
    ) -> None:
        raw_value = payload.get(field_name, "")
        try:
            payload[field_name] = int(str(raw_value).strip())
        except ValueError:
            errors[field_name] = "Enter a whole positive number."
            return
        if payload[field_name] <= 0:
            errors[field_name] = "Value must be greater than zero."

    @staticmethod
    def _coerce_positive_float(
        payload: dict[str, Any],
        field_name: str,
        errors: dict[str, str],
    ) -> None:
        raw_value = payload.get(field_name, "")
        try:
            payload[field_name] = float(str(raw_value).strip())
        except ValueError:
            errors[field_name] = "Enter a positive number."
            return
        if payload[field_name] <= 0:
            errors[field_name] = "Value must be greater than zero."

    @staticmethod
    def _coerce_non_negative_float(
        payload: dict[str, Any],
        field_name: str,
        errors: dict[str, str],
    ) -> None:
        raw_value = payload.get(field_name, "")
        try:
            payload[field_name] = float(str(raw_value).strip())
        except ValueError:
            errors[field_name] = "Enter zero or a positive number."
            return
        if payload[field_name] < 0:
            errors[field_name] = "Value cannot be negative."

    @staticmethod
    def _coerce_ratio(
        payload: dict[str, Any],
        field_name: str,
        errors: dict[str, str],
    ) -> None:
        raw_value = payload.get(field_name, "")
        try:
            payload[field_name] = float(str(raw_value).strip())
        except ValueError:
            errors[field_name] = "Enter a value between 0 and 1."
            return
        if not 0 < payload[field_name] <= 1:
            errors[field_name] = "Use a value between 0 and 1."

    @staticmethod
    def _coerce_theme(
        payload: dict[str, Any],
        field_name: str,
        errors: dict[str, str],
    ) -> None:
        value = str(payload.get(field_name, "dark")).strip().lower()
        payload[field_name] = value
        if value not in {"dark", "light", "system"}:
            errors[field_name] = "Choose dark, light, or system."
