from __future__ import annotations

from dataclasses import dataclass

from src.models.base_entity import BaseEntity, _utc_now


@dataclass
class MemoryRecord(BaseEntity):
    title: str = ""
    description: str = ""
    intent: str = ""
    source_text: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.title = self.require_text(self.title, "title")
        self.description = self.require_text(
            self.description, "description"
        )
        self.intent = str(self.intent).strip()
        self.source_text = str(self.source_text).strip()
        self.updated_at = str(self.updated_at or self.created_at).strip()

    def update(
        self,
        *,
        title: str,
        description: str,
        intent: str = "",
        source_text: str | None = None,
    ) -> None:
        self.title = self.require_text(title, "title")
        self.description = self.require_text(
            description, "description"
        )
        self.intent = str(intent).strip()
        if source_text is not None:
            self.source_text = str(source_text).strip()
        self.updated_at = _utc_now()

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "title": self.title,
            "description": self.description,
            "intent": self.intent,
            "source_text": self.source_text,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "MemoryRecord":
        return cls(
            entity_id=str(payload.get("entity_id", "")),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            title=str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            intent=str(payload.get("intent", "")),
            source_text=str(payload.get("source_text", "")),
        )
