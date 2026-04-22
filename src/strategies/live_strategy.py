from __future__ import annotations

from pathlib import Path

from src.agents.llm_agent import LLMAgent
from src.models.interactions import LiveInteraction, SessionRecord
from src.models.settings import AppSettings
from src.agents.tts_agent import TTSAgent
from src.agents.transcription_agent import TranscriptionAgent
from src.strategies.mode_strategy import ModeStrategy, force_pause_at_end_for_tts


class LiveStrategy(ModeStrategy):
    def __init__(
        self,
        transcription_agent: TranscriptionAgent,
        llm_agent: LLMAgent,
        tts_agent: TTSAgent,
        audio_dir: Path,
        settings: AppSettings | None = None,
    ) -> None:
        self._transcription_agent = transcription_agent
        self._llm_agent = llm_agent
        self._tts_agent = tts_agent
        self._audio_dir = audio_dir
        self._settings = settings

    def execute(self, context: dict) -> LiveInteraction:
        status_callback = context.get("status_callback")
        recording_path = str(context["recording_path"])
        conversation_history = self._build_conversation_history(
            context.get("session")
        )
        multimodal = bool(
            self._settings is not None
            and getattr(self._settings, "multimodal_live_enabled", False)
        )
        if multimodal:
            _emit_stage_status(
                status_callback, "generating", "Listening and writing a reply..."
            )
            live_reply = self._llm_agent.generate_live_speech_reply_from_audio(
                audio_path=recording_path,
                conversation_history=conversation_history,
            )
            transcript = ""
        else:
            _emit_stage_status(status_callback, "transcribing", "Transcribing...")
            transcript = self._transcription_agent.run(audio_path=recording_path)
            _emit_stage_status(status_callback, "generating", "Writing a reply...")
            live_reply = self._llm_agent.generate_live_speech_reply(
                transcript=transcript,
                conversation_history=conversation_history,
            )
        speech_path = self._audio_dir / f"live-{Path(recording_path).stem}.wav"
        _emit_stage_status(status_callback, "speaking", "Preparing speech...")
        generated_speech_path = self._tts_agent.run(
            text=force_pause_at_end_for_tts(live_reply.text),
            output_path=str(speech_path),
            voice_id=live_reply.voice_id,
        )
        return LiveInteraction(
            mode="live",
            recording_path=recording_path,
            transcript=transcript,
            response=live_reply.text,
            speech_path=generated_speech_path,
        )

    @staticmethod
    def _build_conversation_history(
        session: SessionRecord | None,
    ) -> list[dict[str, str]]:
        if session is None:
            return []

        history: list[dict[str, str]] = []
        for interaction in session.interactions:
            if not isinstance(interaction, LiveInteraction):
                continue
            history.append({"role": "user", "content": interaction.transcript})
            history.append({"role": "assistant", "content": interaction.response})
        return history


def _emit_stage_status(
    callback: object,
    state: str,
    message: str,
) -> None:
    if not callable(callback):
        return
    stage_callback = callback
    stage_callback(state, message)
