from __future__ import annotations

from src.models.interactions import BaseInteraction, SessionRecord
from src.storage.json_storage import JsonHistoryRepository


class HistoryManager:
    def __init__(self, repository: JsonHistoryRepository, history_limit: int) -> None:
        self._repository = repository
        self._sessions = repository.load()
        self._history_limit = history_limit

    def start_session(self, mode: str) -> SessionRecord:
        return SessionRecord(mode=mode)

    def save_interaction(
        self, session: SessionRecord, interaction: BaseInteraction
    ) -> None:
        session.add_interaction(interaction)
        updated_sessions = self._repository.list_all()
        updated_sessions.append(session)
        if len(updated_sessions) > self._history_limit:
            updated_sessions = updated_sessions[-self._history_limit :]
        self._repository.save(updated_sessions)
        self._sessions = updated_sessions

    def list_sessions(self) -> list[SessionRecord]:
        return list(self._sessions)
