from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.exceptions.app_exceptions import ValidationError


class AudioCaptureAgent(BaseAgent):
    def run(self, *, transcript: str) -> str:
        cleaned = transcript.strip()
        if not cleaned:
            raise ValidationError("transcript cannot be empty.")
        return cleaned
