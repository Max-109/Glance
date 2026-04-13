from __future__ import annotations

from src.models.settings import AppSettings
from src.storage.json_storage import JsonSettingsStore


class SettingsManager:
    def __init__(self, store: JsonSettingsStore) -> None:
        self._store = store
        self._settings: AppSettings | None = None

    def load(self) -> AppSettings:
        persisted_values = self._migrate_legacy_transcription_settings(
            self._store.load()
        )
        settings = AppSettings.from_mapping(persisted_values, validate=False)
        self._store.save(settings)
        self._settings = settings
        return settings

    def save(self, settings: AppSettings, *, validate: bool = True) -> None:
        if validate:
            settings.validate()
        self._store.save(settings)
        self._settings = settings

    def current(self) -> AppSettings:
        if self._settings is None:
            return self.load()
        return self._settings

    def reload(self) -> AppSettings:
        self._settings = None
        return self.load()

    @staticmethod
    def _migrate_legacy_transcription_settings(values: dict) -> dict:
        migrated = dict(values)
        if "transcription_base_url" not in migrated and migrated.get("tts_base_url"):
            migrated["transcription_base_url"] = migrated["tts_base_url"]
        if "transcription_api_key" not in migrated and "tts_api_key" in migrated:
            migrated["transcription_api_key"] = migrated["tts_api_key"]
        return migrated
