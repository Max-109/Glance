from __future__ import annotations

import json
from pathlib import Path

from src.exceptions.app_exceptions import NotFoundError, StorageError
from src.models.interactions import SessionRecord
from src.models.settings import AppSettings
from src.storage.abstract_repository import AbstractRepository


class JsonHistoryRepository(AbstractRepository[SessionRecord]):
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._sessions: list[SessionRecord] = []

    def load(self) -> list[SessionRecord]:
        if not self._file_path.exists():
            self._sessions = []
            self.save([])
            return []
        try:
            payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StorageError(f"Invalid history file: {self._file_path}") from exc
        self._sessions = [SessionRecord.from_dict(item) for item in payload]
        return list(self._sessions)

    def save(self, entities: list[SessionRecord]) -> None:
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [entity.to_dict() for entity in entities]
            self._file_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
            self._sessions = list(entities)
        except OSError as exc:
            raise StorageError(f"Could not save history to {self._file_path}") from exc

    def add(self, entity: SessionRecord) -> None:
        sessions = self.list_all()
        sessions.append(entity)
        self.save(sessions)

    def remove(self, entity_id: str) -> None:
        sessions = [
            session for session in self.list_all() if session.entity_id != entity_id
        ]
        if len(sessions) == len(self.list_all()):
            raise NotFoundError(f"Session '{entity_id}' was not found.")
        self.save(sessions)

    def list_all(self) -> list[SessionRecord]:
        return list(self._sessions)


class JsonSettingsStore:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def load(self) -> dict:
        if not self._file_path.exists():
            return {}
        try:
            return json.loads(self._file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StorageError(f"Invalid config file: {self._file_path}") from exc

    def save(self, settings: AppSettings) -> None:
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(
                json.dumps(settings.to_dict(), indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise StorageError(f"Could not save config to {self._file_path}") from exc
