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
        existing_index = next(
            (
                index
                for index, existing_session in enumerate(updated_sessions)
                if existing_session.entity_id == session.entity_id
            ),
            None,
        )
        if existing_index is None:
            updated_sessions.append(session)
        else:
            updated_sessions[existing_index] = session
        if len(updated_sessions) > self._history_limit:
            updated_sessions = updated_sessions[-self._history_limit :]
        self._repository.save(updated_sessions)
        self._sessions = updated_sessions

    def list_sessions(self) -> list[SessionRecord]:
        return list(self._sessions)

    def clear(self) -> None:
        self._repository.save([])
        self._sessions = []

    def set_history_limit(self, history_limit: int) -> None:
        self._history_limit = history_limit
