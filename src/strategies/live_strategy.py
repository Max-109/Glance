from __future__ import annotations

from pathlib import Path

from src.agents.llm_agent import LLMAgent
from src.agents.tts_agent import TTSAgent
from src.agents.transcription_agent import TranscriptionAgent
from src.models.interactions import LiveInteraction
from src.strategies.mode_strategy import ModeStrategy


class LiveStrategy(ModeStrategy):
    def __init__(
        self,
        transcription_agent: TranscriptionAgent,
        llm_agent: LLMAgent,
        tts_agent: TTSAgent,
        audio_dir: Path,
    ) -> None:
        self._transcription_agent = transcription_agent
        self._llm_agent = llm_agent
        self._tts_agent = tts_agent
        self._audio_dir = audio_dir

    def execute(self, context: dict) -> LiveInteraction:
        recording_path = str(context["recording_path"])
        transcript = self._transcription_agent.run(audio_path=recording_path)
        response = self._llm_agent.generate_live_speech_reply(transcript=transcript)
        speech_path = self._audio_dir / f"live-{Path(recording_path).stem}.mp3"
        generated_speech_path = self._tts_agent.run(
            text=response,
            output_path=str(speech_path),
        )
        return LiveInteraction(
            mode="live",
            recording_path=recording_path,
            transcript=transcript,
            response=response,
            speech_path=generated_speech_path,
        )
