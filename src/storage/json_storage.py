from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from src.exceptions.app_exceptions import NotFoundError, StorageError
from src.models.interactions import (
    LiveInteraction,
    OCRInteraction,
    QuickInteraction,
    SessionRecord,
)
from src.models.settings import AppSettings
from src.storage.abstract_repository import AbstractRepository


class SessionDirectoryRepository(AbstractRepository[SessionRecord]):
    _SESSION_FILE_NAME = "session.json"
    _CONVERSATION_FILE_NAME = "conversation.md"

    def __init__(self, sessions_dir: Path) -> None:
        self._sessions_dir = sessions_dir
        self._sessions: list[SessionRecord] = []
        self._session_dirs: dict[str, Path] = {}

    def load(self) -> list[SessionRecord]:
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        sessions: list[SessionRecord] = []
        session_dirs: dict[str, Path] = {}
        for session_dir in self._sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            session_file = session_dir / self._SESSION_FILE_NAME
            if not session_file.exists():
                continue
            try:
                payload = json.loads(session_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise StorageError(f"Invalid session file: {session_file}") from exc
            resolved_payload = _resolve_session_payload(payload, session_dir)
            session = SessionRecord.from_dict(resolved_payload)
            sessions.append(session)
            session_dirs[session.entity_id] = session_dir
        sessions.sort(key=lambda session: session.created_at)
        self._sessions = sessions
        self._session_dirs = session_dirs
        return list(self._sessions)

    def save(self, entities: list[SessionRecord]) -> None:
        try:
            self._sessions_dir.mkdir(parents=True, exist_ok=True)
            next_session_dirs: dict[str, Path] = {}
            retained_dirs: set[Path] = set()
            for session in entities:
                previous_dir = self._session_dirs.get(session.entity_id)
                target_dir = self._sessions_dir / _session_folder_name(session)
                if previous_dir is not None and previous_dir.exists() and previous_dir != target_dir:
                    previous_dir.replace(target_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
                self._ingest_session_artifacts(
                    session,
                    session_dir=target_dir,
                    previous_dir=previous_dir if previous_dir != target_dir else None,
                )
                payload = _serialize_session_payload(session, target_dir)
                (target_dir / self._SESSION_FILE_NAME).write_text(
                    json.dumps(payload, indent=2),
                    encoding="utf-8",
                )
                (target_dir / self._CONVERSATION_FILE_NAME).write_text(
                    _build_conversation_markdown(session, target_dir),
                    encoding="utf-8",
                )
                next_session_dirs[session.entity_id] = target_dir
                retained_dirs.add(target_dir)
            for session_dir in self._sessions_dir.iterdir():
                if session_dir.is_dir() and session_dir not in retained_dirs:
                    shutil.rmtree(session_dir)
            self._sessions = list(entities)
            self._session_dirs = next_session_dirs
        except OSError as exc:
            raise StorageError(
                f"Could not save sessions to {self._sessions_dir}"
            ) from exc

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

    def _ingest_session_artifacts(
        self,
        session: SessionRecord,
        *,
        session_dir: Path,
        previous_dir: Path | None,
    ) -> None:
        for turn_index, interaction in enumerate(session.interactions, start=1):
            turn_prefix = f"turn-{turn_index:03d}"
            if isinstance(interaction, QuickInteraction):
                interaction.image_path = _store_artifact(
                    interaction.image_path,
                    target_path=session_dir / f"{turn_prefix}-image{_path_suffix(interaction.image_path, '.png')}",
                    move_source=False,
                    previous_dir=previous_dir,
                    session_dir=session_dir,
                )
                if interaction.speech_path:
                    interaction.speech_path = _store_artifact(
                        interaction.speech_path,
                        target_path=session_dir
                        / f"{turn_prefix}-assistant{_path_suffix(interaction.speech_path, '.mp3')}",
                        move_source=True,
                        previous_dir=previous_dir,
                        session_dir=session_dir,
                    )
                continue
            if isinstance(interaction, OCRInteraction):
                interaction.image_path = _store_artifact(
                    interaction.image_path,
                    target_path=session_dir / f"{turn_prefix}-image{_path_suffix(interaction.image_path, '.png')}",
                    move_source=False,
                    previous_dir=previous_dir,
                    session_dir=session_dir,
                )
                continue
            if isinstance(interaction, LiveInteraction):
                interaction.recording_path = _store_artifact(
                    interaction.recording_path,
                    target_path=session_dir
                    / f"{turn_prefix}-user{_path_suffix(interaction.recording_path, '.wav')}",
                    move_source=True,
                    previous_dir=previous_dir,
                    session_dir=session_dir,
                )
                if interaction.speech_path:
                    interaction.speech_path = _store_artifact(
                        interaction.speech_path,
                        target_path=session_dir
                        / f"{turn_prefix}-assistant{_path_suffix(interaction.speech_path, '.mp3')}",
                        move_source=True,
                        previous_dir=previous_dir,
                        session_dir=session_dir,
                    )
                if interaction.frame_paths:
                    interaction.frame_paths = [
                        _store_artifact(
                            frame_path,
                            target_path=session_dir
                            / (
                                f"{turn_prefix}-frame-{frame_index:02d}"
                                f"{_path_suffix(frame_path, '.png')}"
                            ),
                            move_source=False,
                            previous_dir=previous_dir,
                            session_dir=session_dir,
                        )
                        for frame_index, frame_path in enumerate(
                            interaction.frame_paths,
                            start=1,
                        )
                    ]


def _session_folder_name(session: SessionRecord) -> str:
    timestamp = _format_session_timestamp(session.created_at)
    return f"{timestamp}__{session.mode}__turns-{len(session.interactions)}"


def _format_session_timestamp(created_at: str) -> str:
    try:
        moment = datetime.fromisoformat(created_at)
    except ValueError:
        return created_at.replace(":", "-").replace("+", "_")
    return moment.strftime("%Y-%m-%d_%H-%M-%S_%f")


def _serialize_session_payload(session: SessionRecord, session_dir: Path) -> dict:
    payload = session.to_dict()
    payload["interactions"] = [
        _serialize_interaction_payload(interaction, session_dir)
        for interaction in payload.get("interactions", [])
    ]
    return payload


def _serialize_interaction_payload(payload: dict, session_dir: Path) -> dict:
    serialized = dict(payload)
    for key in ("image_path", "speech_path", "recording_path"):
        value = serialized.get(key)
        if isinstance(value, str) and value:
            serialized[key] = _relative_artifact_path(value, session_dir)
    frame_paths = serialized.get("frame_paths")
    if isinstance(frame_paths, list):
        serialized["frame_paths"] = [
            _relative_artifact_path(str(path_value), session_dir)
            for path_value in frame_paths
        ]
    return serialized


def _resolve_session_payload(payload: dict, session_dir: Path) -> dict:
    resolved = dict(payload)
    interactions = payload.get("interactions", [])
    resolved["interactions"] = [
        _resolve_interaction_payload(interaction, session_dir)
        for interaction in interactions
    ]
    return resolved


def _resolve_interaction_payload(payload: dict, session_dir: Path) -> dict:
    resolved = dict(payload)
    for key in ("image_path", "speech_path", "recording_path"):
        value = resolved.get(key)
        if isinstance(value, str) and value:
            resolved[key] = _resolve_artifact_path(value, session_dir)
    frame_paths = resolved.get("frame_paths")
    if isinstance(frame_paths, list):
        resolved["frame_paths"] = [
            _resolve_artifact_path(str(path_value), session_dir)
            for path_value in frame_paths
        ]
    return resolved


def _relative_artifact_path(path_value: str, session_dir: Path) -> str:
    path = Path(path_value)
    if path.is_absolute():
        try:
            return str(path.relative_to(session_dir))
        except ValueError:
            return str(path)
    return path_value


def _resolve_artifact_path(path_value: str, session_dir: Path) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str(session_dir / path)


def _store_artifact(
    path_value: str,
    *,
    target_path: Path,
    move_source: bool,
    previous_dir: Path | None,
    session_dir: Path,
) -> str:
    if not path_value:
        return path_value
    source_path = _resolve_source_path(
        path_value,
        previous_dir=previous_dir,
        session_dir=session_dir,
    )
    if source_path == target_path and target_path.exists():
        return str(target_path)
    if not source_path.exists():
        return str(target_path if target_path.exists() else source_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if move_source:
        source_path.replace(target_path)
    elif source_path != target_path:
        shutil.copy2(source_path, target_path)
    return str(target_path)


def _resolve_source_path(
    path_value: str,
    *,
    previous_dir: Path | None,
    session_dir: Path,
) -> Path:
    source_path = Path(path_value)
    if previous_dir is not None and source_path.is_absolute():
        try:
            relative_path = source_path.relative_to(previous_dir)
        except ValueError:
            return source_path
        return session_dir / relative_path
    if source_path.is_absolute() or previous_dir is None:
        return source_path
    return session_dir / source_path


def _path_suffix(path_value: str, fallback: str) -> str:
    suffix = Path(path_value).suffix.lower()
    return suffix or fallback


def _build_conversation_markdown(session: SessionRecord, session_dir: Path) -> str:
    lines = [
        f"# {session.mode.title()} session",
        "",
        f"Started: {session.created_at}",
        f"Turns: {len(session.interactions)}",
    ]
    for turn_index, interaction in enumerate(session.interactions, start=1):
        lines.extend(["", f"## Turn {turn_index}"])
        if isinstance(interaction, LiveInteraction):
            lines.extend(
                [
                    "",
                    "User transcript:",
                    interaction.transcript or "(multimodal audio turn)",
                    "",
                    "Assistant reply:",
                    interaction.response,
                    "",
                    f"User audio: {_relative_artifact_path(interaction.recording_path, session_dir)}",
                ]
            )
            if interaction.speech_path:
                lines.append(
                    f"Assistant audio: {_relative_artifact_path(interaction.speech_path, session_dir)}"
                )
            continue
        if isinstance(interaction, QuickInteraction):
            lines.extend(
                [
                    "",
                    "Question:",
                    interaction.question,
                    "",
                    "Assistant reply:",
                    interaction.answer,
                    "",
                    f"Image: {_relative_artifact_path(interaction.image_path, session_dir)}",
                ]
            )
            if interaction.speech_path:
                lines.append(
                    f"Assistant audio: {_relative_artifact_path(interaction.speech_path, session_dir)}"
                )
            continue
        if isinstance(interaction, OCRInteraction):
            lines.extend(
                [
                    "",
                    "Extracted text:",
                    interaction.extracted_text,
                    "",
                    f"Image: {_relative_artifact_path(interaction.image_path, session_dir)}",
                ]
            )
    lines.append("")
    return "\n".join(lines)


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
