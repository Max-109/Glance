from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import Property, QTimer, QObject, Signal, Slot

from src.exceptions.app_exceptions import ValidationError
from src.models.settings import AppSettings
from src.services.history_manager import HistoryManager
from src.services.settings_manager import SettingsManager


class SettingsViewModel(QObject):
    settingsChanged = Signal()
    errorsChanged = Signal()
    dirtyChanged = Signal()
    savingChanged = Signal()
    statusChanged = Signal()
    currentSectionChanged = Signal()

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

    @Property("QStringList", constant=True)
    def themeOptions(self) -> list[str]:
        return ["dark", "light", "system"]

    @Property("QStringList", constant=True)
    def reasoningOptions(self) -> list[str]:
        return ["low", "medium", "high"]

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
            self._settings_manager.save(settings)
            self._baseline_map = settings.to_dict()
            self._settings_map = deepcopy(self._baseline_map)
            self._errors = {}
            self._set_status("Settings saved.", "success")
            self._dirty = False
            self.settingsChanged.emit()
            self.errorsChanged.emit()
            self.dirtyChanged.emit()
        finally:
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

    def _validate_current_settings(self) -> AppSettings | None:
        payload = deepcopy(self._settings_map)
        errors: dict[str, str] = {}

        self._require_url(payload, "llm_base_url", errors)
        self._require_text(payload, "llm_model_name", errors)
        self._require_url(payload, "tts_base_url", errors)
        self._require_text(payload, "tts_model", errors)
        self._require_text(payload, "tts_voice_id", errors)
        self._require_text(payload, "fallback_language", errors)
        self._require_text(payload, "live_keybind", errors)
        self._require_text(payload, "quick_keybind", errors)
        self._require_text(payload, "ocr_keybind", errors)
        self._coerce_positive_int(payload, "history_length", errors)
        self._coerce_positive_float(payload, "screenshot_interval", errors)
        self._coerce_positive_float(payload, "batch_window_duration", errors)
        self._coerce_ratio(payload, "screen_change_threshold", errors)
        self._coerce_theme(payload, "theme_preference", errors)

        if errors:
            self._errors = errors
            self.errorsChanged.emit()
            self._set_status("Fix the highlighted fields before saving.", "error")
            return None

        try:
            settings = AppSettings.from_mapping(payload)
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

    @staticmethod
    def _require_text(
        payload: dict[str, Any], field_name: str, errors: dict[str, str]
    ) -> None:
        value = str(payload.get(field_name, "")).strip()
        payload[field_name] = value
        if not value:
            errors[field_name] = "This field cannot be empty."

    def _require_url(
        self,
        payload: dict[str, Any],
        field_name: str,
        errors: dict[str, str],
    ) -> None:
        value = str(payload.get(field_name, "")).strip()
        payload[field_name] = value
        if not value:
            errors[field_name] = "Enter the full URL."
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
