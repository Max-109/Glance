from __future__ import annotations

from pathlib import Path

from src.agents.audio_capture_agent import AudioCaptureAgent
from src.agents.llm_agent import LLMAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.agents.screen_diff_agent import ScreenDiffAgent
from src.agents.tts_agent import TTSAgent
from src.models.interactions import LiveInteraction
from src.strategies.mode_strategy import ModeStrategy


class LiveStrategy(ModeStrategy):
    def __init__(
        self,
        screen_capture_agent: ScreenCaptureAgent,
        screen_diff_agent: ScreenDiffAgent,
        audio_capture_agent: AudioCaptureAgent,
        llm_agent: LLMAgent,
        tts_agent: TTSAgent,
        audio_dir: Path,
    ) -> None:
        self._screen_capture_agent = screen_capture_agent
        self._screen_diff_agent = screen_diff_agent
        self._audio_capture_agent = audio_capture_agent
        self._llm_agent = llm_agent
        self._tts_agent = tts_agent
        self._audio_dir = audio_dir

    def execute(self, context: dict) -> LiveInteraction:
        transcript = self._audio_capture_agent.run(transcript=context["transcript"])
        frame_paths: list[str] = []
        previous_path: str | None = None
        for image_path in context["image_paths"]:
            current_path = self._screen_capture_agent.run(image_path=image_path)
            if self._screen_diff_agent.run(
                previous_path=previous_path,
                current_path=current_path,
            ):
                frame_paths.append(current_path)
                previous_path = current_path

        if not frame_paths:
            first_image = self._screen_capture_agent.run(
                image_path=context["image_paths"][0]
            )
            frame_paths.append(first_image)

        prompt = "Respond briefly to the user's live request using the provided frames as context."
        response = self._llm_agent.run(
            user_prompt=prompt,
            image_paths=frame_paths,
            transcript=transcript,
            match_user_language=True,
        )
        spoken_response = self._llm_agent.prepare_speech_text(text=response)
        speech_path = self._audio_dir / f"live-{Path(frame_paths[0]).stem}.mp3"
        generated_speech_path = self._tts_agent.run(
            text=spoken_response,
            output_path=str(speech_path),
        )
        return LiveInteraction(
            mode="live",
            transcript=transcript,
            response=response,
            frame_paths=frame_paths,
            speech_path=generated_speech_path,
        )
