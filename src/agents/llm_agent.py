from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.services.providers import NagaTranscriptionProvider, OpenAICompatibleProvider


class LLMAgent(BaseAgent):
    def __init__(
        self,
        provider: OpenAICompatibleProvider,
        transcription_provider: NagaTranscriptionProvider | None = None,
    ) -> None:
        self._provider = provider
        self._transcription_provider = transcription_provider

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

    def prepare_speech_text(self, *, text: str, session_id: str | None = None):
        return self._provider.prepare_speech_text(text, session_id=session_id)

    def generate_live_speech_reply(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
    ):
        return self._provider.generate_live_speech_reply(
            transcript=transcript,
            conversation_history=conversation_history,
            session_id=session_id,
        )

    def build_live_tool_messages(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]] | None = None,
    ):
        return self._provider.build_live_tool_messages(
            transcript=transcript,
            conversation_history=conversation_history,
        )

    def build_live_tool_messages_from_audio(
        self,
        *,
        audio_path: str,
        conversation_history: list[dict[str, str]] | None = None,
    ):
        return self._provider.build_live_tool_messages_from_audio(
            audio_path=audio_path,
            conversation_history=conversation_history,
        )

    def run_tool_turn(
        self,
        *,
        messages: list[dict],
        tools: list[dict],
        session_id: str | None = None,
    ):
        return self._provider.run_tool_turn(
            messages=messages,
            tools=tools,
            session_id=session_id,
        )

    def run_multimodal_tool_turn(
        self,
        *,
        messages: list[dict],
        tools: list[dict],
        session_id: str | None = None,
    ):
        if self._transcription_provider is not None:
            return self._provider.run_tool_turn(
                messages=messages,
                tools=tools,
                session_id=session_id,
                client=self._transcription_provider.client,
                model_name=self._transcription_provider.model_name,
                reasoning_kwargs=self._transcription_provider.reasoning_kwargs(),
                reasoning_label=self._transcription_provider.reasoning_label(),
            )
        return self._provider.run_tool_turn(
            messages=messages,
            tools=tools,
            session_id=session_id,
        )

    def parse_live_speech_reply(self, text: str):
        return self._provider.parse_live_speech_reply(text)

    def generate_live_speech_reply_from_audio(
        self,
        *,
        audio_path: str,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
    ):
        if self._transcription_provider is not None:
            return self._provider.generate_live_speech_reply_from_audio(
                audio_path=audio_path,
                conversation_history=conversation_history,
                session_id=session_id,
                client=self._transcription_provider.client,
                model_name=self._transcription_provider.model_name,
                reasoning_kwargs=self._transcription_provider.reasoning_kwargs(),
                reasoning_label=self._transcription_provider.reasoning_label(),
            )
        return self._provider.generate_live_speech_reply_from_audio(
            audio_path=audio_path,
            conversation_history=conversation_history,
            session_id=session_id,
        )
