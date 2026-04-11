from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.services.providers import OpenAICompatibleProvider


class OCRAgent(BaseAgent):
    def __init__(self, provider: OpenAICompatibleProvider) -> None:
        self._provider = provider

    def run(self, *, image_path: str) -> str:
        return self._provider.extract_text(image_path)
