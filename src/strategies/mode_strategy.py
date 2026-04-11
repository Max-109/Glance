from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.interactions import BaseInteraction


class ModeStrategy(ABC):
    @abstractmethod
    def execute(self, context: dict) -> BaseInteraction:
        """Run one mode workflow and return the resulting interaction."""
