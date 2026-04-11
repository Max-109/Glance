from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.services.providers import OpenAICompatibleProvider


class LLMAgent(BaseAgent):
    def __init__(self, provider: OpenAICompatibleProvider) -> None:
        self._provider = provider

    def run(
        self,
        *,
        user_prompt: str,
        image_paths: list[str] | None = None,
        transcript: str | None = None,
        match_user_language: bool = False,
    ) -> str:
        return self._provider.generate_reply(
            user_prompt=user_prompt,
            image_paths=image_paths,
            transcript=transcript,
            match_user_language=match_user_language,
        )

    def prepare_speech_text(self, *, text: str) -> str:
        return self._provider.prepare_speech_text(text)
