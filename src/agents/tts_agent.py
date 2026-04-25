from __future__ import annotations

from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.services.providers import NagaSpeechProvider


class TTSAgent(BaseAgent):
    def __init__(self, provider: NagaSpeechProvider) -> None:
        self._provider = provider

    def run(
        self, *, text: str, output_path: str, voice_id: str | None = None
    ) -> str:
        return self._provider.synthesize(
            text=text,
            output_path=Path(output_path),
            voice_id=voice_id,
        )
