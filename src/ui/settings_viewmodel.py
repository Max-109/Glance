from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import Property, QCoreApplication, QTimer, QObject, Signal, Slot

from src.exceptions.app_exceptions import ValidationError
from src.models.settings import AppSettings
from src.services.history_manager import HistoryManager
from src.services.keybinds import (
    keybinds_are_unique,
    normalize_keybind,
    qt_event_to_keybind,
)
from src.services.settings_manager import SettingsManager


class SettingsViewModel(QObject):
    settingsChanged = Signal()
    savedSettingsChanged = Signal()
    errorsChanged = Signal()
    dirtyChanged = Signal()
    savingChanged = Signal()
    statusChanged = Signal()
    currentSectionChanged = Signal()
    bindingChanged = Signal()

    def __init__(
        self,
        settings_manager: SettingsManager,
        history_manager: HistoryManager,
    ) -> None:
        super().__init__()
        self._settings_manager = settings_manager
        self._history_manager = history_manager
        current_settings = settings_manager.load()
        self._baseline_map = current_settings.to_dict()
        self._settings_map = deepcopy(self._baseline_map)
        self._errors: dict[str, str] = {}
        self._dirty = False
        self._saving = False
        self._status_message = "Settings loaded from your local config."
        self._status_kind = "neutral"
        self._current_section = "llm"
        self._binding_field = ""

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

    @Property(str, notify=currentSectionChanged)
    def currentSection(self) -> str:
        return self._current_section

    @Property(str, notify=bindingChanged)
    def bindingField(self) -> str:
        return self._binding_field

    @Property(bool, notify=bindingChanged)
    def bindingActive(self) -> bool:
        return bool(self._binding_field)

    @Property("QStringList", constant=True)
    def themeOptions(self) -> list[str]:
        return ["dark", "light", "system"]

    @Property("QStringList", constant=True)
    def reasoningOptions(self) -> list[str]:
        return ["low", "medium", "high"]

    @Property("QStringList", constant=True)
    def transcriptionReasoningOptions(self) -> list[str]:
        return ["minimal", "low", "medium", "high"]

    @Property("QStringList", constant=True)
    def ttsModelOptions(self) -> list[str]:
        return ["eleven-v3"]

    @Property("QStringList", constant=True)
    def voiceOptions(self) -> list[str]:
        return ["alloy"]

    @Property("QStringList", constant=True)
    def languageOptions(self) -> list[str]:
        return ["en", "lt", "fr", "de", "es"]

    @Property("QStringList", constant=True)
    def audioDeviceOptions(self) -> list[str]:
        return ["default"]

    @Slot(str)
    def setCurrentSection(self, section: str) -> None:
        if section == self._current_section:
            return
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

    @Slot()
    def save(self) -> None:
        settings = self._validate_current_settings()
        if settings is None:
            return
        self._set_saving(True)
        try:
            self._settings_manager.save(settings, validate=False)
            self._baseline_map = settings.to_dict()
            self._settings_map = deepcopy(self._baseline_map)
            self._errors = {}
            self._set_status("Settings saved.", "success")
            self._dirty = False
            self.savedSettingsChanged.emit()
            self.settingsChanged.emit()
            self.errorsChanged.emit()
            self.dirtyChanged.emit()
        finally:
            if QCoreApplication.instance() is None:
                self._clear_saving()
            else:
                QTimer.singleShot(350, self._clear_saving)

    @Slot()
    def reset(self) -> None:
        self._settings_map = deepcopy(self._baseline_map)
        self._errors = {}
        self._dirty = False
        self._set_status("Changes reset.", "neutral")
        self.settingsChanged.emit()
        self.errorsChanged.emit()
        self.dirtyChanged.emit()

    @Slot()
    def validateDraft(self) -> None:
        settings = self._validate_current_settings()
        if settings is None:
            return
        del settings
        self._set_status(
            "These settings look valid. Save them to use them next time Glance starts.",
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

    def _validate_current_settings(self) -> AppSettings | None:
        payload = deepcopy(self._settings_map)
        errors: dict[str, str] = {}

        self._validate_optional_url(payload, "llm_base_url", errors)
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
            self._set_status("Fix the highlighted fields before saving.", "error")
            return None

        try:
            settings = AppSettings.from_mapping(payload, validate=False)
        except (ValidationError, ValueError) as exc:
            self._errors = {"general": str(exc)}
            self.errorsChanged.emit()
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
        self._status_message = message
        self._status_kind = kind
        self.statusChanged.emit()

    def _set_saving(self, value: bool) -> None:
        if self._saving == value:
            return
        self._saving = value
        self.savingChanged.emit()

    def _clear_saving(self) -> None:
        self._set_saving(False)

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
        self.savedSettingsChanged.emit()

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
