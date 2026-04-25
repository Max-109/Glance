from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from src.exceptions.app_exceptions import ValidationError


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class BaseEntity(ABC):
    entity_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=_utc_now)

    @staticmethod
    def require_text(value: str, field_name: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"{field_name} cannot be empty.")
        return cleaned

    @abstractmethod
    def to_dict(self) -> dict:
        "Serialize the entity to a dictionary."
