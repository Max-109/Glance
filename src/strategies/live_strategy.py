from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
import tempfile

from src.agents.llm_agent import LLMAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.models.interactions import LiveInteraction, SessionRecord, ToolCallRecord
from src.models.settings import AppSettings
from src.agents.tts_agent import TTSAgent
from src.agents.transcription_agent import TranscriptionAgent
from src.strategies.mode_strategy import ModeStrategy, force_pause_at_end_for_tts
from src.tools import (
    RuntimeToolRegistry,
    ToolCallRequest,
    ToolExecutor,
    ToolResult,
    file_to_data_url,
)


logger = logging.getLogger("glance.live_strategy")
_MAX_TOOL_STEPS_PER_LIVE_TURN = 4
_MAX_TOOL_CALLS_PER_LIVE_TURN = 6


class LiveStrategy(ModeStrategy):
    def __init__(
        self,
        transcription_agent: TranscriptionAgent,
        llm_agent: LLMAgent,
        tts_agent: TTSAgent,
        screen_capture_agent: ScreenCaptureAgent | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self._transcription_agent = transcription_agent
        self._llm_agent = llm_agent
        self._tts_agent = tts_agent
        self._screen_capture_agent = screen_capture_agent
        self._settings = settings

    def execute(self, context: dict) -> LiveInteraction:
        status_callback = context.get("status_callback")
        recording_path = str(context["recording_path"])
        conversation_history = self._build_conversation_history(
            context.get("session")
        )
        session_id = _session_id(context.get("session"))
        multimodal = bool(
            self._settings is not None
            and getattr(self._settings, "multimodal_live_enabled", False)
        )
        tools_enabled = bool(
            self._settings is not None
            and getattr(self._settings, "tools_enabled", False)
        )
        tool_records = []
        if tools_enabled and multimodal:
            _emit_stage_status(
                status_callback, "generating", "Listening and working with tools..."
            )
            final_text, tool_records = self._generate_multimodal_tool_reply(
                audio_path=recording_path,
                conversation_history=conversation_history,
                context=context,
                session_id=session_id,
            )
            live_reply = self._llm_agent.parse_live_speech_reply(final_text)
            transcript = ""
        elif tools_enabled:
            _emit_stage_status(status_callback, "transcribing", "Transcribing...")
            transcript = self._transcription_agent.run(audio_path=recording_path)
            _emit_stage_status(status_callback, "generating", "Working with tools...")
            final_text, tool_records = self._generate_tool_reply(
                transcript=transcript,
                conversation_history=conversation_history,
                context=context,
                session_id=session_id,
            )
            live_reply = self._llm_agent.prepare_speech_text(
                text=final_text,
                session_id=session_id,
            )
            live_reply = _guard_speech_prep_drift(final_text, live_reply)
        elif multimodal:
            _emit_stage_status(
                status_callback, "generating", "Listening and writing a reply..."
            )
            live_reply = self._llm_agent.generate_live_speech_reply_from_audio(
                audio_path=recording_path,
                conversation_history=conversation_history,
                session_id=session_id,
            )
            transcript = ""
        else:
            _emit_stage_status(status_callback, "transcribing", "Transcribing...")
            transcript = self._transcription_agent.run(audio_path=recording_path)
            _emit_stage_status(status_callback, "generating", "Writing a reply...")
            live_reply = self._llm_agent.generate_live_speech_reply(
                transcript=transcript,
                conversation_history=conversation_history,
                session_id=session_id,
            )
        temp_file = tempfile.NamedTemporaryFile(
            prefix="glance-live-reply-",
            suffix=".wav",
            delete=False,
        )
        temp_file.close()
        _emit_stage_status(status_callback, "speaking", "Preparing speech...")
        generated_speech_path = self._tts_agent.run(
            text=force_pause_at_end_for_tts(live_reply.text),
            output_path=temp_file.name,
            voice_id=live_reply.voice_id,
        )
        return LiveInteraction(
            mode="live",
            recording_path=recording_path,
            transcript=transcript,
            response=live_reply.text,
            speech_path=generated_speech_path,
            tool_calls=tool_records,
        )

    def _generate_tool_reply(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]],
        context: dict,
        session_id: str | None,
    ) -> tuple[str, list]:
        if self._settings is None:
            raise RuntimeError("Tool mode requires settings.")
        registry = RuntimeToolRegistry(
            self._settings,
            screen_capture_agent=self._screen_capture_agent,
        )
        executor = ToolExecutor(registry)
        enabled_tools = registry.enabled_definitions
        messages = self._llm_agent.build_live_tool_messages(
            transcript=transcript,
            conversation_history=conversation_history,
        )
        tool_payloads = [definition.provider_payload() for definition in enabled_tools]
        return self._run_tool_reply_loop(
            messages=messages,
            registry=registry,
            executor=executor,
            tool_payloads=tool_payloads,
            context=context,
            session_id=session_id,
            turn_runner=self._llm_agent.run_tool_turn,
        )

    def _generate_multimodal_tool_reply(
        self,
        *,
        audio_path: str,
        conversation_history: list[dict[str, str]],
        context: dict,
        session_id: str | None,
    ) -> tuple[str, list]:
        if self._settings is None:
            raise RuntimeError("Tool mode requires settings.")
        registry = RuntimeToolRegistry(
            self._settings,
            screen_capture_agent=self._screen_capture_agent,
        )
        executor = ToolExecutor(registry)
        enabled_tools = registry.enabled_definitions
        messages = self._llm_agent.build_live_tool_messages_from_audio(
            audio_path=audio_path,
            conversation_history=conversation_history,
        )
        tool_payloads = [definition.provider_payload() for definition in enabled_tools]
        return self._run_tool_reply_loop(
            messages=messages,
            registry=registry,
            executor=executor,
            tool_payloads=tool_payloads,
            context=context,
            session_id=session_id,
            turn_runner=self._llm_agent.run_multimodal_tool_turn,
        )

    def _run_tool_reply_loop(
        self,
        *,
        messages: list[dict],
        registry: RuntimeToolRegistry,
        executor: ToolExecutor,
        tool_payloads: list[dict],
        context: dict,
        session_id: str | None,
        turn_runner,
    ) -> tuple[str, list]:
        tool_records = []
        tool_call_count = 0
        status_callback = context.get("status_callback")

        for _step in range(_MAX_TOOL_STEPS_PER_LIVE_TURN):
            turn = turn_runner(
                messages=messages,
                tools=tool_payloads,
                session_id=session_id,
            )
            messages.append(turn.assistant_message)
            if not turn.tool_calls:
                if turn.content:
                    return turn.content, tool_records
                break

            image_messages: list[dict] = []
            for provider_call in turn.tool_calls:
                call = ToolCallRequest(
                    call_id=provider_call.call_id,
                    name=provider_call.name,
                    arguments=provider_call.arguments,
                )
                definition = registry.get(call.name)
                if tool_call_count >= _MAX_TOOL_CALLS_PER_LIVE_TURN:
                    record, result = _tool_limit_result(call)
                elif definition is None:
                    record, result = executor.execute(call)
                    tool_call_count += 1
                else:
                    self._emit_tool_notice(
                        definition.pre_speech_notice,
                        context=context,
                        status_callback=status_callback,
                    )
                    record, result = executor.execute(call)
                    tool_call_count += 1
                tool_records.append(record)
                messages.append(_tool_result_message(call, result))
                image_messages.extend(_image_context_messages(call, result))
            messages.extend(image_messages)

        messages.append(
            {
                "role": "user",
                "content": (
                    "No more tool calls are available for this live turn. Give the "
                    "best concise final answer now."
                ),
            }
        )
        final_turn = turn_runner(
            messages=messages,
            tools=[],
            session_id=session_id,
        )
        if final_turn.content:
            return final_turn.content, tool_records
        return (
            "I tried to use the enabled tools, but I could not produce a clear answer.",
            tool_records,
        )

    def _emit_tool_notice(
        self,
        notice: str,
        *,
        context: dict,
        status_callback: object,
    ) -> None:
        if not notice:
            return
        _emit_stage_status(status_callback, "speaking", notice)
        notice_callback = context.get("tool_notice_callback")
        if callable(notice_callback):
            notice_callback(notice)
        audio_callback = context.get("announce_audio_callback")
        if not callable(audio_callback):
            return
        temp_file = tempfile.NamedTemporaryFile(
            prefix="glance-tool-notice-",
            suffix=".wav",
            delete=False,
        )
        temp_file.close()
        notice_path = temp_file.name
        generated_notice_path = notice_path
        try:
            generated_notice_path = self._tts_agent.run(
                text=force_pause_at_end_for_tts(notice),
                output_path=notice_path,
            )
            audio_callback(generated_notice_path)
        except Exception as exc:  # pragma: no cover - defensive runtime behavior.
            logger.warning("Tool notice playback failed: %s", exc)
        finally:
            for path_value in {notice_path, generated_notice_path}:
                try:
                    Path(path_value).unlink(missing_ok=True)
                except OSError:
                    pass

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


def _tool_limit_result(call: ToolCallRequest) -> tuple[ToolCallRecord, ToolResult]:
    message = "Tool call limit reached for this live turn."
    timestamp = datetime.now(timezone.utc).isoformat()
    record = ToolCallRecord(
        call_id=call.call_id,
        tool_name=call.name,
        status="error",
        arguments_summary="limit reached",
        result_preview=message,
        error=message,
        started_at=timestamp,
        finished_at=timestamp,
    )
    return record, ToolResult(content=f"{call.name} failed: {message}")


def _tool_result_message(call: ToolCallRequest, result: ToolResult) -> dict:
    return {
        "role": "tool",
        "tool_call_id": call.call_id,
        "content": result.content,
    }


def _image_context_messages(call: ToolCallRequest, result: ToolResult) -> list[dict]:
    messages: list[dict] = []
    for image in result.images:
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Visual context returned by {call.name}. Use the image "
                            "to answer the user's live request."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": file_to_data_url(Path(image.path))},
                    },
                ],
            }
        )
    return messages


def _emit_stage_status(
    callback: object,
    state: str,
    message: str,
) -> None:
    if not callable(callback):
        return
    stage_callback = callback
    stage_callback(state, message)


def _session_id(session: object) -> str | None:
    entity_id = str(getattr(session, "entity_id", "")).strip()
    return entity_id or None


def _guard_speech_prep_drift(
    original_text: str,
    prepared_reply,
):
    prepared_text = str(getattr(prepared_reply, "text", ""))
    if not _speech_prep_drifted(original_text, prepared_text):
        return prepared_reply
    logger.warning(
        "Speech prep changed the final answer too much; using the original answer text."
    )
    return type(prepared_reply)(
        voice_id=prepared_reply.voice_id,
        text=original_text.strip(),
    )


def _speech_prep_drifted(original_text: str, prepared_text: str) -> bool:
    original_words = _meaning_words(original_text)
    prepared_words = _meaning_words(prepared_text)
    if not original_words:
        return False
    if not prepared_words:
        return True

    coverage = len(set(original_words) & set(prepared_words)) / len(set(original_words))
    if len(set(original_words)) <= 4:
        return coverage < 0.75
    return coverage < 0.55


def _meaning_words(text: str) -> list[str]:
    cleaned = re.sub(r"\[[^\]]+\]", " ", text.lower())
    return [
        word
        for word in re.findall(r"[a-z0-9][a-z0-9._'-]*", cleaned)
        if len(word) > 2 and word not in _DRIFT_STOPWORDS
    ]


_DRIFT_STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "you",
    "your",
    "are",
    "was",
    "were",
    "with",
    "from",
    "but",
    "not",
    "can",
    "just",
    "its",
    "it's",
    "i'm",
    "i",
    "me",
    "my",
    "we",
    "our",
    "they",
    "them",
    "there",
    "here",
    "looks",
    "like",
}
