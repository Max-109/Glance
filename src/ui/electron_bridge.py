from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Lock, Thread
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from src.ui.runtime_visual import coerce_runtime_status, default_runtime_status
from src.ui.settings_viewmodel import SettingsViewModel


class _UiThreadExecutor(QObject):
    _executeRequested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._executeRequested.connect(self._execute)

    def call(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if QThread.currentThread() is self.thread():
            return callback(*args, **kwargs)

        completed = Event()
        result_holder: dict[str, Any] = {}
        self._executeRequested.emit((callback, args, kwargs, result_holder, completed))
        completed.wait()
        error = result_holder.get("error")
        if error is not None:
            raise error
        return result_holder.get("result")

    @Slot(object)
    def _execute(self, payload: object) -> None:
        callback, args, kwargs, result_holder, completed = payload
        try:
            result_holder["result"] = callback(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - surfaced to caller.
            result_holder["error"] = exc
        finally:
            completed.set()


def _build_state_snapshot(viewmodel: SettingsViewModel) -> dict[str, Any]:
    return {
        "settings": viewmodel.settings,
        "errors": viewmodel.errors,
        "dirty": viewmodel.dirty,
        "manualSaveDirty": viewmodel.manualSaveDirty,
        "saving": viewmodel.saving,
        "statusMessage": viewmodel.statusMessage,
        "statusKind": viewmodel.statusKind,
        "audioInputDeviceOptions": viewmodel.audioInputDeviceOptions,
        "audioInputDeviceLabels": viewmodel.audioInputDeviceLabels,
        "audioOutputDeviceOptions": viewmodel.audioOutputDeviceOptions,
        "audioOutputDeviceLabels": viewmodel.audioOutputDeviceLabels,
        "audioDeviceStatusMessage": viewmodel.audioDeviceStatusMessage,
        "audioInputLevel": viewmodel.audioInputLevel,
        "audioInputTestActive": viewmodel.audioInputTestActive,
        "speakerTestActive": viewmodel.speakerTestActive,
        "currentSection": viewmodel.currentSection,
        "bindingField": viewmodel.bindingField,
        "bindingActive": viewmodel.bindingActive,
        "previewingVoice": viewmodel.previewingVoice,
        "previewActive": viewmodel.previewActive,
        "themeOptions": viewmodel.themeOptions,
        "reasoningOptions": viewmodel.reasoningOptions,
        "transcriptionReasoningOptions": viewmodel.transcriptionReasoningOptions,
        "ttsModelOptions": viewmodel.ttsModelOptions,
        "voiceOptions": viewmodel.voiceOptions,
        "voiceOptionLabels": viewmodel.voiceOptionLabels,
        "promptDefaults": viewmodel.promptDefaults,
        "historyPreview": viewmodel.buildHistoryPreview(),
        "historyStats": viewmodel.buildHistoryStats(),
    }


def _build_audio_state_snapshot(viewmodel: SettingsViewModel) -> dict[str, Any]:
    return {
        "audioInputLevel": viewmodel.audioInputLevel,
        "audioInputTestActive": viewmodel.audioInputTestActive,
        "audioDeviceStatusMessage": viewmodel.audioDeviceStatusMessage,
    }


class SettingsBridgeServer:
    def __init__(self, viewmodel: SettingsViewModel) -> None:
        self._viewmodel = viewmodel
        self._executor = _UiThreadExecutor()
        self._state_lock = Lock()
        self._state_revision = 0
        self._runtime_lock = Lock()
        self._runtime_status = default_runtime_status()
        self._register_state_change_signals()
        server = ThreadingHTTPServer(("127.0.0.1", 0), self._build_handler())
        server.bridge = self  # type: ignore[attr-defined]
        self._server = server
        self._thread = Thread(
            target=server.serve_forever,
            name="glance-settings-bridge",
            daemon=True,
        )
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def snapshot(self) -> dict[str, Any]:
        snapshot = self._executor.call(_build_state_snapshot, self._viewmodel)
        with self._state_lock:
            snapshot["stateRevision"] = self._state_revision
        with self._runtime_lock:
            snapshot.update(self._runtime_status)
        return snapshot

    def audio_state(self) -> dict[str, Any]:
        return self._executor.call(_build_audio_state_snapshot, self._viewmodel)

    def set_runtime_status(self, status: dict[str, Any]) -> None:
        next_status = coerce_runtime_status(status)
        with self._runtime_lock:
            if self._runtime_status == next_status:
                return
            self._runtime_status = next_status
        self._bump_state_revision()

    def set_section(self, section: str) -> dict[str, Any]:
        self._executor.call(self._viewmodel.setCurrentSection, section)
        return self.snapshot()

    def set_field(self, field_name: str, value: Any) -> dict[str, Any]:
        self._executor.call(self._viewmodel.setField, field_name, value)
        return self.snapshot()

    def assign_keybind(self, field_name: str, keybind: str) -> dict[str, Any]:
        self._executor.call(self._viewmodel.assignKeybind, field_name, keybind)
        return self.snapshot()

    def run_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        action_map: dict[str, Callable[[], None]] = {
            "save": self._viewmodel.save,
            "reset": self._viewmodel.reset,
            "validateDraft": self._viewmodel.validateDraft,
            "clearHistory": self._viewmodel.clearHistory,
            "stopVoicePreview": self._viewmodel.stopVoicePreview,
            "refreshAudioDevices": self._viewmodel.refreshAudioDevices,
            "startAudioInputTest": self._viewmodel.startAudioInputTest,
            "stopAudioInputTest": self._viewmodel.stopAudioInputTest,
            "playSpeakerTest": self._viewmodel.playSpeakerTest,
            "stopSpeakerTest": self._viewmodel.stopSpeakerTest,
            "resetAudioDefaults": self._viewmodel.resetAudioDefaults,
            "cancelKeybindCapture": self._viewmodel.cancelKeybindCapture,
        }

        if action == "previewVoice":
            voice_name = str(payload.get("voiceName", "")).strip()
            self._executor.call(self._viewmodel.previewVoice, voice_name)
            return self.snapshot()

        if action == "startKeybindCapture":
            field_name = str(payload.get("fieldName", "")).strip()
            self._executor.call(self._viewmodel.startKeybindCapture, field_name)
            return self.snapshot()

        handler = action_map.get(action)
        if handler is None:
            raise ValueError(f"Unknown bridge action: {action}")
        self._executor.call(handler)
        return self.snapshot()

    def _register_state_change_signals(self) -> None:
        for signal in (
            self._viewmodel.settingsChanged,
            self._viewmodel.savedSettingsChanged,
            self._viewmodel.errorsChanged,
            self._viewmodel.dirtyChanged,
            self._viewmodel.savingChanged,
            self._viewmodel.statusChanged,
            self._viewmodel.audioDevicesChanged,
            self._viewmodel.audioTestChanged,
            self._viewmodel.currentSectionChanged,
            self._viewmodel.bindingChanged,
            self._viewmodel.previewChanged,
        ):
            signal.connect(self._bump_state_revision)

    def _bump_state_revision(self) -> None:
        with self._state_lock:
            self._state_revision += 1

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(HTTPStatus.NO_CONTENT)
                self._send_common_headers()
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/api/state":
                    self._send_json({"ok": True, "state": bridge.snapshot()})
                    return
                if self.path == "/api/audio-state":
                    self._send_json({"ok": True, "state": bridge.audio_state()})
                    return
                self._send_error(HTTPStatus.NOT_FOUND, "Unknown route.")

            def do_POST(self) -> None:  # noqa: N802
                try:
                    payload = self._read_payload()
                    if self.path == "/api/field":
                        state = bridge.set_field(
                            str(payload.get("fieldName", "")),
                            payload.get("value"),
                        )
                    elif self.path == "/api/section":
                        state = bridge.set_section(str(payload.get("section", "")))
                    elif self.path == "/api/keybind":
                        state = bridge.assign_keybind(
                            str(payload.get("fieldName", "")),
                            str(payload.get("keybind", "")),
                        )
                    elif self.path == "/api/action":
                        state = bridge.run_action(
                            str(payload.get("action", "")),
                            payload,
                        )
                    else:
                        self._send_error(HTTPStatus.NOT_FOUND, "Unknown route.")
                        return
                except ValueError as exc:
                    self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                except Exception as exc:  # pragma: no cover - surfaced to UI.
                    self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
                    return

                self._send_json({"ok": True, "state": state})

            def log_message(self, format: str, *args: object) -> None:
                del format, args

            def _read_payload(self) -> dict[str, Any]:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0:
                    return {}
                raw_body = self.rfile.read(content_length)
                if not raw_body:
                    return {}
                try:
                    return json.loads(raw_body.decode("utf-8"))
                except json.JSONDecodeError as exc:  # pragma: no cover - input guard.
                    raise ValueError("Could not decode the request body.") from exc

            def _send_common_headers(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Cache-Control", "no-store")

            def _send_json(self, payload: dict[str, Any]) -> None:
                response = json.dumps(payload).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self._send_common_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def _send_error(self, status: HTTPStatus, message: str) -> None:
                response = json.dumps({"ok": False, "error": message}).encode("utf-8")
                self.send_response(status)
                self._send_common_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        return Handler
