from __future__ import annotations

from src.models.interactions import BaseInteraction, SessionRecord
from src.storage.abstract_repository import AbstractRepository


class HistoryManager:
    def __init__(
        self,
        repository: AbstractRepository[SessionRecord],
        history_limit: int,
        retention_enabled: bool = True,
    ) -> None:
        self._repository = repository
        self._history_limit = max(1, int(history_limit))
        self._retention_enabled = bool(retention_enabled)
        self._sessions = self._apply_retention(repository.load(), persist=True)

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
        updated_sessions = self._apply_retention(updated_sessions)
        self._repository.save(updated_sessions)
        self._sessions = updated_sessions

    def list_sessions(self) -> list[SessionRecord]:
        return list(self._sessions)

    def clear(self) -> None:
        self._repository.save([])
        self._sessions = []

    def set_history_limit(self, history_limit: int) -> None:
        self.set_history_policy(
            history_limit=history_limit,
            retention_enabled=self._retention_enabled,
        )

    def set_history_policy(
        self, history_limit: int, retention_enabled: bool
    ) -> None:
        self._history_limit = max(1, int(history_limit))
        self._retention_enabled = bool(retention_enabled)
        self._sessions = self._apply_retention(
            self._repository.list_all(),
            persist=True,
        )

    def _apply_retention(
        self,
        sessions: list[SessionRecord],
        *,
        persist: bool = False,
    ) -> list[SessionRecord]:
        retained_sessions = list(sessions)
        if (
            self._retention_enabled
            and len(retained_sessions) > self._history_limit
        ):
            retained_sessions = retained_sessions[-self._history_limit:]
        if persist and len(retained_sessions) != len(sessions):
            self._repository.save(retained_sessions)
        return retained_sessions
