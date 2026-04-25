from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.interactions import BaseInteraction


def force_pause_at_end_for_tts(text: str) -> str:
    stripped_text = text.rstrip()
    if stripped_text.endswith(("...", "…")):
        return stripped_text
    return f"{stripped_text}..."


class ModeStrategy(ABC):
    @abstractmethod
    def execute(self, context: dict) -> BaseInteraction:
        "Run one mode workflow and return the resulting interaction."
