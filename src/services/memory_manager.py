from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock

from src.exceptions.app_exceptions import StorageError, ValidationError
from src.models.memories import MemoryRecord


_TITLE_LIMIT = 20
_DETAIL_LIMIT = 5
_CANDIDATE_LIMIT = 5
_STOP_WORDS = {
    "a",
    "about",
    "and",
    "do",
    "for",
    "i",
    "me",
    "my",
    "of",
    "on",
    "read",
    "remind",
    "tell",
    "the",
    "to",
    "was",
    "what",
}


class MemoryManager:
    def __init__(self, memory_file: Path) -> None:
        self._memory_file = memory_file
        self._lock = Lock()
        self._memories = self._load()

    def list_memories(self) -> list[MemoryRecord]:
        with self._lock:
            return list(reversed(self._memories))

    def search_memories(
        self, query: str = "", *, max_results: int = _DETAIL_LIMIT
    ) -> dict:
        max_result_count = min(10, max(1, int(max_results or _DETAIL_LIMIT)))
        query_text = str(query).strip()
        query_terms = _query_terms(query_text)
        with self._lock:
            memories = list(reversed(self._memories))

        available_titles = [
            memory.title for memory in memories[:_TITLE_LIMIT]
        ]
        if not memories:
            return {
                "status": "empty",
                "query": query_text,
                "matches": [],
                "available_titles": [],
            }
        if not query_terms:
            return {
                "status": "titles",
                "query": query_text,
                "matches": [],
                "available_titles": available_titles,
            }

        scored_memories = [
            (_memory_score(memory, query_text, query_terms), memory)
            for memory in memories
        ]
        matches = [
            memory
            for score, memory in sorted(
                scored_memories,
                key=lambda item: (item[0], item[1].created_at),
                reverse=True,
            )
            if score > 0
        ][:max_result_count]
        return {
            "status": "matches" if matches else "none",
            "query": query_text,
            "matches": [_memory_payload(memory) for memory in matches],
            "available_titles": available_titles,
        }

    def add_memory(
        self,
        *,
        title: str,
        description: str,
        intent: str = "",
        source_text: str = "",
    ) -> MemoryRecord:
        memory = MemoryRecord(
            title=_trim_text(title, 120),
            description=_trim_text(description, 4000),
            intent=_trim_text(intent, 1000),
            source_text=_trim_text(source_text, 4000),
        )
        with self._lock:
            self._memories.append(memory)
            self._save_locked()
        return memory

    def change_memory(
        self,
        *,
        memory_id: str = "",
        query: str = "",
        title: str | None = None,
        description: str | None = None,
        intent: str | None = None,
        source_text: str | None = None,
    ) -> dict:
        updates = _memory_updates(
            title=title,
            description=description,
            intent=intent,
            source_text=source_text,
        )
        if not updates:
            raise ValidationError("Tell me what to change.")

        memory_id = str(memory_id).strip()
        query_text = str(query).strip()
        with self._lock:
            if memory_id:
                memory = self._find_locked(memory_id)
                _apply_memory_updates(memory, updates)
                self._save_locked()
                return {
                    "status": "updated",
                    "memory": _memory_payload(memory),
                }

            memories = list(reversed(self._memories))
            if not memories:
                return {
                    "status": "empty",
                    "query": query_text,
                    "memory": None,
                    "candidates": [],
                }

            query_terms = _query_terms(query_text)
            if not query_terms:
                return {
                    "status": "ambiguous",
                    "query": query_text,
                    "memory": None,
                    "candidates": [
                        _memory_candidate_payload(memory)
                        for memory in memories[:_CANDIDATE_LIMIT]
                    ],
                }

            ranked = _rank_memories(memories, query_text, query_terms)
            if not ranked:
                return {
                    "status": "none",
                    "query": query_text,
                    "memory": None,
                    "candidates": [
                        _memory_candidate_payload(memory)
                        for memory in memories[:_CANDIDATE_LIMIT]
                    ],
                }
            if len(ranked) > 1:
                return {
                    "status": "ambiguous",
                    "query": query_text,
                    "memory": None,
                    "candidates": [
                        _memory_candidate_payload(memory)
                        for _, memory in ranked[:_CANDIDATE_LIMIT]
                    ],
                }

            memory = ranked[0][1]
            _apply_memory_updates(memory, updates)
            self._save_locked()
            return {
                "status": "updated",
                "query": query_text,
                "memory": _memory_payload(memory),
                "candidates": [],
            }

    def update_memory(
        self,
        memory_id: str,
        *,
        title: str,
        description: str,
        intent: str = "",
        source_text: str | None = None,
    ) -> MemoryRecord:
        with self._lock:
            memory = self._find_locked(memory_id)
            memory.update(
                title=_trim_text(title, 120),
                description=_trim_text(description, 4000),
                intent=_trim_text(intent, 1000),
                source_text=(
                    _trim_text(source_text, 4000)
                    if source_text is not None
                    else None
                ),
            )
            self._save_locked()
            return memory

    def delete_memory(self, memory_id: str) -> None:
        with self._lock:
            before_count = len(self._memories)
            self._memories = [
                memory
                for memory in self._memories
                if memory.entity_id != memory_id
            ]
            if len(self._memories) == before_count:
                raise ValidationError("Memory was not found.")
            self._save_locked()

    def _find_locked(self, memory_id: str) -> MemoryRecord:
        for memory in self._memories:
            if memory.entity_id == memory_id:
                return memory
        raise ValidationError("Memory was not found.")

    def _load(self) -> list[MemoryRecord]:
        if not self._memory_file.exists():
            return []
        try:
            payload = json.loads(self._memory_file.read_text("utf-8"))
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"Invalid memories file: {self._memory_file}"
            ) from exc
        if isinstance(payload, dict):
            raw_items = payload.get("memories", [])
        else:
            raw_items = payload
        if not isinstance(raw_items, list):
            raise StorageError(
                f"Invalid memories file: {self._memory_file}"
            )
        return [MemoryRecord.from_dict(item) for item in raw_items]

    def _save_locked(self) -> None:
        try:
            self._memory_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "memories": [
                    memory.to_dict() for memory in self._memories
                ],
            }
            self._memory_file.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise StorageError(
                f"Could not save memories to {self._memory_file}"
            ) from exc


def _trim_text(value: str, limit: int) -> str:
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _query_terms(value: str) -> list[str]:
    terms = [
        term
        for term in re.findall(r"[a-zA-Z0-9À-ž]+", value.lower())
        if len(term) > 1 and term not in _STOP_WORDS
    ]
    return list(dict.fromkeys(terms))


def _memory_score(
    memory: MemoryRecord, query_text: str, query_terms: list[str]
) -> int:
    lowered_query = query_text.lower()
    score = 0
    fields = (
        (memory.title.lower(), 5),
        (memory.intent.lower(), 4),
        (memory.description.lower(), 2),
        (memory.source_text.lower(), 1),
    )
    for text, weight in fields:
        if lowered_query and lowered_query in text:
            score += weight * 4
        for term in query_terms:
            if term in text:
                score += weight
    return score


def _rank_memories(
    memories: list[MemoryRecord],
    query_text: str,
    query_terms: list[str],
) -> list[tuple[int, MemoryRecord]]:
    return [
        (score, memory)
        for score, memory in sorted(
            [
                (_memory_score(memory, query_text, query_terms), memory)
                for memory in memories
            ],
            key=lambda item: (item[0], item[1].created_at),
            reverse=True,
        )
        if score > 0
    ]


def _memory_updates(
    *,
    title: str | None = None,
    description: str | None = None,
    intent: str | None = None,
    source_text: str | None = None,
) -> dict[str, str]:
    updates = {}
    if title is not None and str(title).strip():
        updates["title"] = _trim_text(title, 120)
    if description is not None and str(description).strip():
        updates["description"] = _trim_text(description, 4000)
    if intent is not None and str(intent).strip():
        updates["intent"] = _trim_text(intent, 1000)
    if source_text is not None and str(source_text).strip():
        updates["source_text"] = _trim_text(source_text, 4000)
    return updates


def _apply_memory_updates(
    memory: MemoryRecord, updates: dict[str, str]
) -> None:
    memory.update(
        title=updates.get("title", memory.title),
        description=updates.get("description", memory.description),
        intent=updates.get("intent", memory.intent),
        source_text=updates.get("source_text"),
    )


def _memory_candidate_payload(memory: MemoryRecord) -> dict:
    return {
        "id": memory.entity_id,
        "title": memory.title,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }


def _memory_payload(memory: MemoryRecord) -> dict:
    return {
        "id": memory.entity_id,
        "title": memory.title,
        "description": memory.description,
        "intent": memory.intent,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }
