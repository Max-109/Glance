from __future__ import annotations

import tempfile

from src.agents.llm_agent import LLMAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.agents.tts_agent import TTSAgent
from src.models.interactions import QuickInteraction
from src.strategies.mode_strategy import (
    ModeStrategy,
    force_pause_at_end_for_tts,
)


class QuickStrategy(ModeStrategy):
    def __init__(
        self,
        screen_capture_agent: ScreenCaptureAgent,
        llm_agent: LLMAgent,
        tts_agent: TTSAgent,
    ) -> None:
        self._screen_capture_agent = screen_capture_agent
        self._llm_agent = llm_agent
        self._tts_agent = tts_agent

    def execute(self, context: dict) -> QuickInteraction:
        image_path = self._screen_capture_agent.run(
            image_path=context["image_path"]
        )
        question = (
            context.get("question")
            or "What should I notice in this selection?"
        )
        answer = self._llm_agent.run(
            user_prompt=question, image_paths=[image_path]
        )
        spoken_reply = self._llm_agent.prepare_speech_text(text=answer)
        temp_file = tempfile.NamedTemporaryFile(
            prefix="glance-quick-reply-",
            suffix=".wav",
            delete=False,
        )
        temp_file.close()
        generated_speech_path = self._tts_agent.run(
            text=force_pause_at_end_for_tts(spoken_reply.text),
            output_path=temp_file.name,
            voice_id=spoken_reply.voice_id,
        )
        return QuickInteraction(
            mode="quick",
            question=question,
            answer=answer,
            image_path=image_path,
            speech_path=generated_speech_path,
        )
