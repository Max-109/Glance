from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.services.providers import NagaTranscriptionProvider


class TranscriptionAgent(BaseAgent):
    def __init__(self, provider: NagaTranscriptionProvider) -> None:
        self._provider = provider

    def run(self, *, audio_path: str) -> str:
        return self._provider.transcribe(audio_path)
