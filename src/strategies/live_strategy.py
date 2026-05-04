from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import tempfile

from src.agents.llm_agent import LLMAgent
from src.agents.ocr_agent import OCRAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.models.interactions import (
    LiveInteraction,
    SessionRecord,
    ToolCallRecord,
)
from src.models.settings import (
    AUTO_TTS_VOICE_ID,
    AppSettings,
    DEFAULT_FIXED_TTS_VOICE,
)
from src.services.clipboard import ClipboardService
from src.services.memory_manager import MemoryManager
from src.services.ocr import OCRService
from src.agents.tts_agent import TTSAgent
from src.agents.transcription_agent import TranscriptionAgent
from src.strategies.mode_strategy import (
    ModeStrategy,
    force_pause_at_end_for_tts,
)
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
_TERMINAL_TOOL_NAMES = {"end_live_session"}
_USER_FACING_TOOL_NAMES = {
    "take_screenshot",
    "ocr_screen",
    "web_search",
    "web_fetch",
    "add_memory",
    "read_memory",
    "change_memory",
}
_OCR_CONFIRMATION_TEXT = "Done, I copied it to your clipboard. Anything else?"
_OCR_NO_TEXT_TEXT = "I didn't find any visible text. Anything else?"
_OCR_FAILURE_TEXT = "I couldn't copy the text this time. Anything else?"


class LiveStrategy(ModeStrategy):
    def __init__(
        self,
        transcription_agent: TranscriptionAgent,
        llm_agent: LLMAgent,
        tts_agent: TTSAgent,
        screen_capture_agent: ScreenCaptureAgent | None = None,
        ocr_agent: OCRAgent | None = None,
        clipboard_service: ClipboardService | None = None,
        settings: AppSettings | None = None,
        memory_manager: MemoryManager | None = None,
        static_speech_dir: Path | None = None,
    ) -> None:
        self._transcription_agent = transcription_agent
        self._llm_agent = llm_agent
        self._tts_agent = tts_agent
        self._screen_capture_agent = screen_capture_agent
        self._ocr_agent = ocr_agent
        self._clipboard_service = clipboard_service
        self._settings = settings
        self._memory_manager = memory_manager
        self._static_speech_dir = static_speech_dir

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
        runtime_tools_allowed = bool(
            self._settings is not None and self._settings.tools_enabled
        )
        user_tools_available = self._has_user_facing_tools_available()
        tool_records = []

        # live has four paths: audio with tools, transcript with tools,
        # audio-only, or transcript-only.
        if runtime_tools_allowed and user_tools_available and multimodal:
            _emit_stage_status(
                status_callback, "transcribing", "Transcribing..."
            )
            transcript = self._transcription_agent.run(
                audio_path=recording_path
            )
            _emit_stage_status(
                status_callback, "generating", "Listening and checking..."
            )
            final_text, tool_records, terminal_tool = (
                self._generate_multimodal_tool_reply(
                    audio_path=recording_path,
                    transcript=transcript,
                    conversation_history=conversation_history,
                    context=context,
                    session_id=session_id,
                )
            )
            if terminal_tool:
                return LiveInteraction(
                    mode="live",
                    recording_path=recording_path,
                    transcript=transcript,
                    response=final_text,
                    speech_path="",
                    tool_calls=tool_records,
                )
            live_reply = _local_speech_reply(final_text, self._settings)
            if live_reply is None:
                live_reply = self._llm_agent.parse_live_speech_reply(
                    final_text
                )
        elif runtime_tools_allowed and user_tools_available:
            _emit_stage_status(
                status_callback, "transcribing", "Transcribing..."
            )
            transcript = self._transcription_agent.run(
                audio_path=recording_path
            )
            _emit_stage_status(status_callback, "generating", "Checking...")
            final_text, tool_records, terminal_tool = (
                self._generate_tool_reply(
                    transcript=transcript,
                    conversation_history=conversation_history,
                    context=context,
                    session_id=session_id,
                )
            )
            if terminal_tool:
                return LiveInteraction(
                    mode="live",
                    recording_path=recording_path,
                    transcript=transcript,
                    response=final_text,
                    speech_path="",
                    tool_calls=tool_records,
                )
            live_reply = _local_speech_reply(final_text, self._settings)
            if live_reply is None:
                live_reply = self._llm_agent.prepare_speech_text(
                    text=final_text,
                    session_id=session_id,
                )
                live_reply = _guard_speech_prep_drift(final_text, live_reply)
        elif multimodal:
            _emit_stage_status(
                status_callback, "transcribing", "Transcribing..."
            )
            transcript = self._transcription_agent.run(
                audio_path=recording_path
            )
            _emit_stage_status(
                status_callback,
                "generating",
                "Listening and writing a reply...",
            )
            live_reply = self._llm_agent.generate_live_speech_reply_from_audio(
                audio_path=recording_path,
                transcript=transcript,
                conversation_history=conversation_history,
                session_id=session_id,
            )
        else:
            _emit_stage_status(
                status_callback, "transcribing", "Transcribing..."
            )
            transcript = self._transcription_agent.run(
                audio_path=recording_path
            )
            local_end = self._maybe_end_live_locally(
                transcript=transcript,
                conversation_history=conversation_history,
                context=context,
            )
            if local_end is not None:
                final_text, tool_records, terminal_tool = local_end
                if terminal_tool:
                    return LiveInteraction(
                        mode="live",
                        recording_path=recording_path,
                        transcript=transcript,
                        response=final_text,
                        speech_path="",
                        tool_calls=tool_records,
                    )
            _emit_stage_status(
                status_callback, "generating", "Writing a reply..."
            )
            live_reply = self._llm_agent.generate_live_speech_reply(
                transcript=transcript,
                conversation_history=conversation_history,
                session_id=session_id,
            )
        _emit_stage_status(status_callback, "speaking", "Preparing speech...")
        static_speech_path = _local_static_speech_path(
            live_reply,
            self._static_speech_dir,
        )
        if static_speech_path is not None:
            generated_speech_path = str(static_speech_path)
            return LiveInteraction(
                mode="live",
                recording_path=recording_path,
                transcript=transcript,
                response=live_reply.text,
                speech_path=generated_speech_path,
                tool_calls=tool_records,
            )

        temp_file = tempfile.NamedTemporaryFile(
            prefix="glance-live-reply-",
            suffix=".wav",
            delete=False,
        )
        temp_file.close()
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

    def _has_user_facing_tools_available(self) -> bool:
        if self._settings is None or not self._settings.tools_enabled:
            return False
        registry = RuntimeToolRegistry(
            self._settings,
            screen_capture_agent=self._screen_capture_agent,
            ocr_service=self._build_ocr_service(),
            memory_manager=self._memory_manager,
            include_live_control_tools=True,
        )
        return any(
            definition.name in _USER_FACING_TOOL_NAMES
            for definition in registry.enabled_definitions
        )

    def _maybe_end_live_locally(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]],
        context: dict,
    ) -> tuple[str, list[ToolCallRecord], bool] | None:
        if self._settings is None:
            return None
        if not _should_end_live_from_transcript(
            transcript, conversation_history
        ):
            return None
        registry = RuntimeToolRegistry(
            self._settings,
            include_live_control_tools=True,
        )
        return _local_end_live_session(
            ToolExecutor(registry),
            context.get("status_callback"),
            reason="user declined more help",
        )

    def _generate_tool_reply(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]],
        context: dict,
        session_id: str | None,
    ) -> tuple[str, list, bool]:
        if self._settings is None:
            raise RuntimeError("Tool mode requires settings.")
        registry = RuntimeToolRegistry(
            self._settings,
            screen_capture_agent=self._screen_capture_agent,
            ocr_service=self._build_ocr_service(),
            memory_manager=self._memory_manager,
            include_live_control_tools=True,
        )
        executor = ToolExecutor(registry)
        if _should_end_live_from_transcript(transcript, conversation_history):
            return _local_end_live_session(
                executor,
                context.get("status_callback"),
                reason="user declined more help",
            )
        enabled_tools = registry.enabled_definitions
        enabled_tool_names = {definition.name for definition in enabled_tools}
        messages = self._llm_agent.build_live_tool_messages(
            transcript=transcript,
            conversation_history=conversation_history,
            enabled_tool_names=enabled_tool_names,
        )
        tool_payloads = [
            definition.provider_payload() for definition in enabled_tools
        ]
        return self._run_tool_reply_loop(
            messages=messages,
            registry=registry,
            executor=executor,
            tool_payloads=tool_payloads,
            context=context,
            session_id=session_id,
            turn_runner=self._llm_agent.run_tool_turn,
            user_context=transcript,
        )

    def _generate_multimodal_tool_reply(
        self,
        *,
        audio_path: str,
        transcript: str,
        conversation_history: list[dict[str, str]],
        context: dict,
        session_id: str | None,
    ) -> tuple[str, list, bool]:
        if self._settings is None:
            raise RuntimeError("Tool mode requires settings.")
        registry = RuntimeToolRegistry(
            self._settings,
            screen_capture_agent=self._screen_capture_agent,
            ocr_service=self._build_ocr_service(),
            memory_manager=self._memory_manager,
            include_live_control_tools=True,
        )
        executor = ToolExecutor(registry)
        enabled_tools = registry.enabled_definitions
        enabled_tools = [
            definition
            for definition in enabled_tools
            if definition.name in _USER_FACING_TOOL_NAMES
            or definition.name in _TERMINAL_TOOL_NAMES
        ]
        enabled_tool_names = {definition.name for definition in enabled_tools}
        messages = self._llm_agent.build_live_tool_messages_from_audio(
            audio_path=audio_path,
            transcript=transcript,
            conversation_history=conversation_history,
            enabled_tool_names=enabled_tool_names,
        )
        tool_payloads = [
            definition.provider_payload() for definition in enabled_tools
        ]
        return self._run_tool_reply_loop(
            messages=messages,
            registry=registry,
            executor=executor,
            tool_payloads=tool_payloads,
            context=context,
            session_id=session_id,
            turn_runner=self._llm_agent.run_multimodal_tool_turn,
            user_context=transcript,
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
        user_context: str,
    ) -> tuple[str, list, bool]:
        tool_records = []
        tool_call_count = 0
        status_callback = context.get("status_callback")

        # each pass saves the assistant tool-call message, runs the tools,
        # then feeds tool results and images back into the next provider turn.
        # if caps are hit, the last turn runs without tools and must answer.
        for _step in range(_MAX_TOOL_STEPS_PER_LIVE_TURN):
            previous_messages = list(messages)
            turn = turn_runner(
                messages=messages,
                tools=tool_payloads,
                session_id=session_id,
            )
            messages.append(turn.assistant_message)
            if not turn.tool_calls:
                if _should_end_live_from_final_reply(
                    turn.content,
                    previous_messages,
                ):
                    return _local_end_live_session(
                        executor,
                        status_callback,
                        reason="assistant recognized user is done",
                    )
                if turn.content:
                    return turn.content, tool_records, False
                break

            if _has_user_facing_tool_call(turn.tool_calls):
                self._emit_tool_notice(
                    turn.content,
                    context=context,
                    status_callback=status_callback,
                )

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
                    record, result = executor.execute(call)
                    tool_call_count += 1
                tool_records.append(record)
                if call.name == "ocr_screen":
                    # ocr is a clipboard action. keep the copied text out of
                    # the spoken answer and use the short follow-up instead.
                    status = _ocr_tool_status(record, result)
                    _emit_stage_status(status_callback, "idle", status)
                    return (
                        _ocr_followup_text(record, result),
                        tool_records,
                        False,
                    )
                if _is_terminal_tool(call.name):
                    terminal_status = _terminal_tool_status(
                        call, record, result
                    )
                    _emit_stage_status(
                        status_callback, "idle", terminal_status
                    )
                    return terminal_status, tool_records, True
                if call.name == "change_memory":
                    status = _memory_change_followup(record, result)
                    _emit_stage_status(status_callback, "idle", status)
                    return status, tool_records, False
                messages.append(_tool_result_message(call, result))
                image_messages.extend(_image_context_messages(call, result))
            messages.extend(image_messages)

        messages.append(
            {
                "role": "user",
                "content": (
                    "No more tool calls are available for this live turn. "
                    "Give the "
                    "best concise final answer now."),
            })
        final_turn = turn_runner(
            messages=messages,
            tools=[],
            session_id=session_id,
        )
        if final_turn.content:
            return final_turn.content, tool_records, False
        return (
            "I tried to use the enabled tools, but I could not produce a "
            "clear answer.",
            tool_records,
            False,
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
        # tool notices are quick spoken progress updates before the final
        # reply. they use throwaway audio because final audio is created later.
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
        except (
            Exception
        ) as exc:  # pragma: no cover - defensive runtime behavior.
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
            history.append(
                {"role": "assistant", "content": interaction.response}
            )
        return history

    def _build_ocr_service(self) -> OCRService | None:
        if self._ocr_agent is None or self._clipboard_service is None:
            return None
        return OCRService(self._ocr_agent, self._clipboard_service)


@dataclass
class _LocalSpeechReply:
    voice_id: str
    text: str


def _is_terminal_tool(tool_name: str) -> bool:
    return tool_name in _TERMINAL_TOOL_NAMES


def _has_user_facing_tool_call(tool_calls: list) -> bool:
    return any(
        getattr(call, "name", "") in _USER_FACING_TOOL_NAMES
        for call in tool_calls
    )


def _local_end_live_session(
    executor: ToolExecutor,
    status_callback: object,
    *,
    reason: str,
) -> tuple[str, list[ToolCallRecord], bool]:
    record, result = executor.execute(
        ToolCallRequest(
            call_id="local-end-live-session",
            name="end_live_session",
            arguments={"reason": reason},
        )
    )
    status = _terminal_tool_status(
        ToolCallRequest(
            call_id=record.call_id,
            name=record.tool_name,
            arguments={"reason": reason},
        ),
        record,
        result,
    )
    _emit_stage_status(status_callback, "idle", status)
    return status, [record], True


def _local_speech_reply(
    text: str,
    settings: AppSettings | None,
) -> _LocalSpeechReply | None:
    if text not in _LOCAL_SPEECH_TEXTS:
        return None
    voice_id = (
        DEFAULT_FIXED_TTS_VOICE
        if settings is None or settings.tts_voice_id == AUTO_TTS_VOICE_ID
        else settings.tts_voice_id
    )
    return _LocalSpeechReply(voice_id=voice_id, text=text)


def static_live_speech_file_name(text: str, voice_id: str) -> str:
    if text == _OCR_CONFIRMATION_TEXT:
        return f"live-ocr-confirmation-{_safe_file_part(voice_id)}.wav"
    if text == _OCR_NO_TEXT_TEXT:
        return f"live-ocr-no-text-{_safe_file_part(voice_id)}.wav"
    if text == _OCR_FAILURE_TEXT:
        return f"live-ocr-failure-{_safe_file_part(voice_id)}.wav"
    return ""


def _local_static_speech_path(
    reply: _LocalSpeechReply,
    static_speech_dir: Path | None,
) -> Path | None:
    if static_speech_dir is None:
        return None
    file_name = static_live_speech_file_name(reply.text, reply.voice_id)
    if not file_name:
        return None
    speech_path = static_speech_dir / file_name
    if not speech_path.exists() or speech_path.stat().st_size <= 0:
        return None
    return speech_path


def _safe_file_part(value: object) -> str:
    safe_value = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in str(value).strip().lower()
    ).strip("-")
    return safe_value or "default"


def _should_end_live_from_transcript(
    transcript: str,
    conversation_history: list[dict[str, str]],
) -> bool:
    text = _normalize_stop_text(transcript)
    if not text:
        return False
    if text in _ALWAYS_STOP_REQUESTS:
        return True
    if not _last_assistant_invited_more(conversation_history):
        return False
    if text in _DECLINE_MORE_HELP_REQUESTS:
        return True
    return text.startswith("no ") and len(text.split()) <= 5


def _should_end_live_from_final_reply(
    content: str,
    previous_messages: list[dict],
) -> bool:
    if not _last_assistant_invited_more(previous_messages):
        return False
    text = _strip_voice_reply_markup(content)
    lowered = text.lower()
    if _normalize_stop_text(text) in _DECLINE_MORE_HELP_REPLIES:
        return True
    has_closing_ack = any(
        phrase in lowered
        for phrase in (
            "no problem",
            "no worries",
            "you're welcome",
            "you are welcome",
            "glad to help",
        )
    )
    has_goodbye = any(
        phrase in lowered
        for phrase in (
            "have a great",
            "let me know if you need",
            "anything else",
            "if you need anything else",
        )
    )
    return has_closing_ack and has_goodbye


def _last_assistant_invited_more(
    messages: list[dict[str, str]] | list[dict],
) -> bool:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        content = message.get("content", "")
        if not isinstance(content, str):
            continue
        lowered = content.lower()
        return "anything else" in lowered or "need anything else" in lowered
    return False


def _strip_voice_reply_markup(text: str) -> str:
    stripped = str(text).strip()
    stripped = re.sub(
        r"^VOICE_ID:\s*\S+\s*", "", stripped, flags=re.IGNORECASE
    )
    stripped = re.sub(r"\[[^\]]+\]", " ", stripped)
    return _squash_notice_text(stripped)


def _normalize_stop_text(text: str) -> str:
    normalized = str(text).lower()
    normalized = re.sub(r"\[[^\]]+\]", " ", normalized)
    normalized = re.sub(r"[^a-z0-9\s']+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _ocr_tool_status(record: ToolCallRecord, result: ToolResult) -> str:
    if record.status == "success":
        if result.content.strip():
            return "OCR copied text to clipboard."
        return "OCR found no visible text. Clipboard cleared."
    return f"OCR failed: {record.error or result.content}"


def _ocr_followup_text(record: ToolCallRecord, result: ToolResult) -> str:
    if record.status == "success" and result.content.strip():
        return _OCR_CONFIRMATION_TEXT
    if record.status == "success":
        return _OCR_NO_TEXT_TEXT
    return _OCR_FAILURE_TEXT


def _terminal_tool_status(
    call: ToolCallRequest,
    record: ToolCallRecord,
    result: ToolResult,
) -> str:
    if call.name == "end_live_session" and record.status == "success":
        return "Live ended."
    return f"{call.name} failed: {record.error or result.content}"


def _memory_change_followup(
    record: ToolCallRecord, result: ToolResult
) -> str:
    if record.status != "success":
        if "not found" in record.error.lower():
            return "I could not find that saved memory."
        return "I could not update that memory."
    status = str(result.metadata.get("status", ""))
    if status == "updated":
        return "Done, I updated that memory."
    if status == "empty":
        return "You do not have any saved memories yet."

    candidates = [
        candidate
        for candidate in result.metadata.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    titles = [
        _squash_notice_text(str(candidate.get("title", "")))
        for candidate in candidates[:3]
        if str(candidate.get("title", "")).strip()
    ]
    if status == "ambiguous":
        if titles:
            return (
                "I am not sure which memory to update. I found "
                f"{', '.join(titles)}. Which one did you mean?"
            )
        return "I am not sure which memory to update. Which one did you mean?"
    if titles:
        return (
            "I could not find a close memory match. I found "
            f"{', '.join(titles)}. Which one did you mean?"
        )
    return "I could not find a close memory match."


def _squash_notice_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,:;!?")


def _tool_limit_result(
    call: ToolCallRequest,
) -> tuple[ToolCallRecord, ToolResult]:
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
    content = result.content
    return {
        "role": "tool",
        "tool_call_id": call.call_id,
        "content": content,
    }


def _image_context_messages(
    call: ToolCallRequest, result: ToolResult
) -> list[dict]:
    messages: list[dict] = []
    for image in result.images:
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Visual context returned by {call.name}. Use "
                            "the image "
                            "to answer the user's live request."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": file_to_data_url(Path(image.path))
                        },
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
        "Speech prep changed the final answer too much; using the original "
        "answer text."
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

    coverage = len(set(original_words) & set(prepared_words)) / len(
        set(original_words)
    )
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
    "im",
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

_ALWAYS_STOP_REQUESTS = {
    "stop",
    "stop listening",
    "end live",
    "end the live session",
    "end session",
    "quit",
    "exit",
    "bye",
    "goodbye",
}

_DECLINE_MORE_HELP_REQUESTS = {
    "no",
    "nope",
    "nah",
    "no thanks",
    "no thank you",
    "thanks",
    "thank you",
    "thanks you",
    "nothing",
    "nothing else",
    "everything is fine",
    "everything's fine",
    "everything fine",
    "all fine",
    "that's all",
    "that is all",
    "that's it",
    "that is it",
    "all good",
    "im good",
    "i'm good",
    "done",
    "we're done",
    "were done",
}

_DECLINE_MORE_HELP_REPLIES = {
    "ok",
    "okay",
    "alright",
    "sure",
    "sure thing",
}

_LOCAL_SPEECH_TEXTS = {
    _OCR_CONFIRMATION_TEXT,
    _OCR_NO_TEXT_TEXT,
    _OCR_FAILURE_TEXT,
}
