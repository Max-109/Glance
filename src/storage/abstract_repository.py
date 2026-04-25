from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    def load(self) -> list[T]:
        "Load all entities from persistent storage."

    @abstractmethod
    def save(self, entities: list[T]) -> None:
        "Persist all entities to storage."

    @abstractmethod
    def list_all(self) -> list[T]:
        "Return all in-memory entities."
