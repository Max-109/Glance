from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
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
from src.models.settings import AppSettings
from src.services.clipboard import ClipboardService
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
    short_site_name,
)


logger = logging.getLogger("glance.live_strategy")
_MAX_TOOL_STEPS_PER_LIVE_TURN = 4
_MAX_TOOL_CALLS_PER_LIVE_TURN = 6
_TERMINAL_TOOL_NAMES = {"end_live_session"}
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
    ) -> None:
        self._transcription_agent = transcription_agent
        self._llm_agent = llm_agent
        self._tts_agent = tts_agent
        self._screen_capture_agent = screen_capture_agent
        self._ocr_agent = ocr_agent
        self._clipboard_service = clipboard_service
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
        tools_enabled = self._settings is not None
        tool_records = []
        if tools_enabled and multimodal:
            _emit_stage_status(
                status_callback, "generating", "Listening and checking..."
            )
            final_text, tool_records, terminal_tool = (
                self._generate_multimodal_tool_reply(
                    audio_path=recording_path,
                    conversation_history=conversation_history,
                    context=context,
                    session_id=session_id,
                )
            )
            if terminal_tool:
                return LiveInteraction(
                    mode="live",
                    recording_path=recording_path,
                    transcript="",
                    response=final_text,
                    speech_path="",
                    tool_calls=tool_records,
                )
            live_reply = self._llm_agent.parse_live_speech_reply(final_text)
            transcript = ""
        elif tools_enabled:
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
            live_reply = self._llm_agent.prepare_speech_text(
                text=final_text,
                session_id=session_id,
            )
            live_reply = _guard_speech_prep_drift(final_text, live_reply)
        elif multimodal:
            _emit_stage_status(
                status_callback,
                "generating",
                "Listening and writing a reply...",
            )
            live_reply = self._llm_agent.generate_live_speech_reply_from_audio(
                audio_path=recording_path,
                conversation_history=conversation_history,
                session_id=session_id,
            )
            transcript = ""
        else:
            _emit_stage_status(
                status_callback, "transcribing", "Transcribing..."
            )
            transcript = self._transcription_agent.run(
                audio_path=recording_path
            )
            _emit_stage_status(
                status_callback, "generating", "Writing a reply..."
            )
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
    ) -> tuple[str, list, bool]:
        if self._settings is None:
            raise RuntimeError("Tool mode requires settings.")
        registry = RuntimeToolRegistry(
            self._settings,
            screen_capture_agent=self._screen_capture_agent,
            ocr_service=self._build_ocr_service(),
            include_live_control_tools=True,
        )
        executor = ToolExecutor(registry)
        enabled_tools = registry.enabled_definitions
        messages = self._llm_agent.build_live_tool_messages(
            transcript=transcript,
            conversation_history=conversation_history,
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
            include_live_control_tools=True,
        )
        executor = ToolExecutor(registry)
        enabled_tools = registry.enabled_definitions
        messages = self._llm_agent.build_live_tool_messages_from_audio(
            audio_path=audio_path,
            conversation_history=conversation_history,
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
            user_context="",
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
        notice_context = ToolNoticeContext(user_context=user_context)

        for _step in range(_MAX_TOOL_STEPS_PER_LIVE_TURN):
            turn = turn_runner(
                messages=messages,
                tools=tool_payloads,
                session_id=session_id,
            )
            messages.append(turn.assistant_message)
            if not turn.tool_calls:
                if turn.content:
                    return turn.content, tool_records, False
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
                    notice = compose_tool_notice(call, notice_context)
                    if notice:
                        self._emit_tool_notice(
                            notice,
                            context=context,
                            status_callback=status_callback,
                        )
                        notice_context.mark_spoken(call, notice)
                    record, result = executor.execute(call)
                    tool_call_count += 1
                    notice_context.record_result(call, record, result)
                tool_records.append(record)
                if call.name == "ocr_screen":
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
class ToolNoticeContext:
    user_context: str = ""
    last_notice_kind: str = ""
    last_notice_subject: str = ""
    last_spoken_notice: str = ""
    last_search_notice: str = ""
    last_search_query: str = ""
    last_search_results: list[dict[str, str]] = field(default_factory=list)
    last_opened_url: str = ""
    last_opened_title: str = ""
    last_opened_site: str = ""
    previous_records: list[ToolCallRecord] = field(default_factory=list)

    def mark_spoken(self, call: ToolCallRequest, notice: str) -> None:
        self.last_notice_kind = _notice_kind(call.name)
        self.last_notice_subject = _notice_subject(call)
        self.last_spoken_notice = notice
        if call.name == "web_search":
            self.last_search_notice = notice

    def record_result(
        self,
        call: ToolCallRequest,
        record: ToolCallRecord,
        result: ToolResult,
    ) -> None:
        self.previous_records.append(record)
        metadata = result.metadata
        if call.name == "web_search":
            self.last_search_query = str(metadata.get("query", "")).strip()
            self.last_search_results = [
                item
                for item in metadata.get("results", [])
                if isinstance(item, dict)
            ]
        elif call.name == "web_fetch":
            self.last_opened_url = str(metadata.get("url", "")).strip()
            self.last_opened_title = str(metadata.get("title", "")).strip()
            self.last_opened_site = str(metadata.get("site_name", "")).strip()


def compose_tool_notice(
    call: ToolCallRequest,
    context: ToolNoticeContext,
) -> str:
    notice = ""
    if call.name == "web_search":
        notice = _compose_search_notice(call, context)
    elif call.name == "web_fetch":
        notice = _compose_fetch_notice(call, context)
    elif call.name == "take_screenshot":
        notice = _compose_screenshot_notice(call)
    if not notice:
        return ""
    kind = _notice_kind(call.name)
    subject = _notice_subject(call)
    if kind == context.last_notice_kind and (
        subject == context.last_notice_subject or subject == "generic"
    ):
        return ""
    if (
        call.name == "web_search"
        and notice == context.last_search_notice
        and notice
        in {
            "I'm looking that up.",
            "I'm checking that.",
            "I'm checking the latest information.",
        }
    ):
        return ""
    return notice


def _compose_search_notice(
    call: ToolCallRequest,
    context: ToolNoticeContext,
) -> str:
    del context
    query = _squash_notice_text(str(call.arguments.get("query", "")))
    location = _weather_location(query)
    if location:
        return f"I'm checking the weather in {location}."
    lowered = query.lower()
    if any(
        term in lowered
        for term in ("latest", "current", "today", "now", "price")
    ):
        return "I'm checking the latest information."
    if any(
        term in lowered
        for term in (
            "who", "what", "when", "where", "why", "how", "is ", "are ",
        )
    ):
        return "I'm checking that."
    return "I'm looking that up."


def _compose_fetch_notice(
    call: ToolCallRequest,
    context: ToolNoticeContext,
) -> str:
    url = str(call.arguments.get("url", "")).strip()
    site_name = _matching_search_site(url, context) or short_site_name(url)
    source = site_name if _is_speakable_source(site_name) else ""
    if source and context.last_search_results:
        return f"I found {source}. I'm opening it."
    if source:
        return f"I'm opening {source}."
    if context.last_search_results:
        return "I found a result. I'm opening it."
    return "I'm opening the page."


def _compose_screenshot_notice(call: ToolCallRequest) -> str:
    reason = _squash_notice_text(str(call.arguments.get("reason", ""))).lower()
    if any(
        term in reason
        for term in ("code", "function", "file", "editor", "terminal", "log")
    ):
        return "I'll take a quick screenshot of your code."
    if any(
        term in reason
        for term in (
            "error", "exception", "traceback", "warning", "bug", "failure",
        )
    ):
        return "I'll take a quick screenshot of the error."
    if any(term in reason for term in ("screen", "window", "app", "page")):
        return "I'll take a quick screenshot of your screen."
    return "I'll take a quick screenshot."


def _weather_location(query: str) -> str:
    patterns = (
        r"\bweather(?:\s+forecast)?\s+(?:in|for|at)\s+(.+)",
        r"\b(?:current|today'?s|tomorrow'?s)\s+weather\s+(?:in|for|at)\s+(.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            return _clean_location(match.group(1))
    return ""


def _clean_location(value: str) -> str:
    text = re.sub(
        r"\b(today|tomorrow|right now|now|current|forecast|weather)\b",
        " ",
        value,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[^A-Za-zÀ-ž\s.'-]", " ", text)
    text = _squash_notice_text(text)
    if len(text) > 40:
        return ""
    return " ".join(word[:1].upper() + word[1:] for word in text.split())


def _matching_search_site(url: str, context: ToolNoticeContext) -> str:
    target = url.strip()
    if not target:
        return ""
    for result in context.last_search_results:
        if str(result.get("url", "")).strip() == target:
            return str(result.get("site_name", "")).strip()
    return ""


def _notice_kind(tool_name: str) -> str:
    if tool_name == "web_search":
        return "search"
    if tool_name == "web_fetch":
        return "fetch"
    if tool_name == "take_screenshot":
        return "screenshot"
    if tool_name == "ocr_screen":
        return "ocr"
    return tool_name


def _notice_subject(call: ToolCallRequest) -> str:
    if call.name == "web_search":
        query = _squash_notice_text(
            str(call.arguments.get("query", ""))
        ).lower()
        return query or "generic"
    if call.name == "web_fetch":
        return str(call.arguments.get("url", "")).strip().lower() or "generic"
    if call.name == "take_screenshot":
        return _compose_screenshot_notice(call)
    return "generic"


def _is_terminal_tool(tool_name: str) -> bool:
    return tool_name in _TERMINAL_TOOL_NAMES


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


def _is_speakable_source(source: str) -> bool:
    if not source:
        return False
    if len(source) > 22:
        return False
    return bool(re.search(r"[A-Za-z]", source))


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
    "theandforthatthisyouyourarewaswerewithfrombutnotcanjustitsit'si'mimemywe"
    "ourtheythemthereherelookslike",
}
