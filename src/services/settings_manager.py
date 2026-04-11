from __future__ import annotations

from pathlib import Path

from src.models.settings import AppSettings
from src.services.env_loader import load_env_file, translate_env_values
from src.storage.json_storage import JsonSettingsStore


class SettingsManager:
    def __init__(self, store: JsonSettingsStore, env_file: Path) -> None:
        self._store = store
        self._env_file = env_file
        self._settings: AppSettings | None = None

    def load(self) -> AppSettings:
        persisted_values = self._store.load()
        env_values = translate_env_values(load_env_file(self._env_file))
        merged = {}
        merged.update(persisted_values)
        merged.update(env_values)
        settings = AppSettings.from_mapping(merged)
        self._store.save(settings)
        self._settings = settings
        return settings

    def save(self, settings: AppSettings) -> None:
        settings.validate()
        self._store.save(settings)
        self._settings = settings

    def current(self) -> AppSettings:
        if self._settings is None:
            return self.load()
        return self._settings
