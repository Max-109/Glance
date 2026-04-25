from __future__ import annotations

import base64
from datetime import datetime
import json
import locale
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse
import wave

from src.exceptions.app_exceptions import ProviderError
from src.models.prompt_defaults import (
    DEFAULT_TEXT_REPLY_PROMPT,
    DEFAULT_TRANSCRIPTION_PROMPT,
    DEFAULT_TTS_PREPARATION_PROMPT,
    DEFAULT_VOICE_REPLY_PROMPT,
)
from src.models.settings import (
    AUTO_TTS_VOICE_ID,
    AppSettings,
    DEFAULT_FIXED_TTS_VOICE,
    ELEVEN_V3_VOICES,
    get_tts_voice,
    get_tts_voice_label,
)

try:
    from openai import OpenAI
except (
    ImportError
):  # pragma: no cover - exercised only without optional dependency.
    OpenAI = None


logger = logging.getLogger("glance.providers")

_PCM_SAMPLE_RATE = 24000
_PCM_CHANNELS = 1
_PCM_SAMPLE_WIDTH_BYTES = 2
_TIMEZONE_COUNTRY_OVERRIDES = {
    "Europe/Vilnius": "Lithuania",
}
_COUNTRY_BY_REGION_CODE = {
    "AU": "Australia",
    "BR": "Brazil",
    "CA": "Canada",
    "DE": "Germany",
    "ES": "Spain",
    "FR": "France",
    "GB": "United Kingdom",
    "IE": "Ireland",
    "IN": "India",
    "IT": "Italy",
    "JP": "Japan",
    "LT": "Lithuania",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "SE": "Sweden",
    "UA": "Ukraine",
    "US": "United States",
}
OCR_EXTRACTION_PROMPT = """You are an OCR engine. Return clean clipboard text
from the image, not a visual line-by-line transcript.

Rules:
- Output only text that is visibly present in the image.
- Follow the user's OCR request exactly. If they ask for a specific item,
  return only that item.
- If the user's OCR request asks for all visible text, return clean clipboard
  text for the whole image.
- Do not include surrounding UI text unless it is needed to identify the
  requested item.
- Preserve original wording, spelling, capitalization, and punctuation.
- Join prose or UI copy that is only split across lines because the interface
  wrapped it visually.
- Preserve headings, labels, menu items, lists, table rows, and columns.
- If table or grid text is visible, return it as a Markdown table.
- Do not summarize, explain, translate, infer hidden text, add labels.
- Do not say that you extracted the text.
- Do not wrap the answer in code fences.
- If no text is visible, output exactly [NO_VISIBLE_TEXT]."""


@dataclass(frozen=True)
class LiveSpeechReply:
    voice_id: str
    text: str


@dataclass(frozen=True)
class ProviderToolCall:
    call_id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ProviderToolTurn:
    content: str
    tool_calls: list[ProviderToolCall]
    assistant_message: dict


class OpenAICompatibleProvider:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._client = self._build_client(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )

    @staticmethod
    def _build_client(base_url: str, api_key: str):
        if OpenAI is None:
            raise ProviderError(
                "The 'openai' package is required for provider access."
            )
        if not api_key:
            raise ProviderError("Missing LLM API key.")
        return OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"Accept-Encoding": "identity"},
        )

    def _resolve_prompt_override(
        self, field_name: str, default_prompt: str
    ) -> str:
        override = str(getattr(self._settings, field_name, "")).strip()
        return override or default_prompt

    def _shared_prompt_override(self) -> str:
        return self._settings.system_prompt_override.strip()

    def generate_reply(
        self,
        *,
        user_prompt: str,
        image_paths: list[str] | None = None,
        transcript: str | None = None,
        match_user_language: bool = False,
    ) -> str:
        content: list[dict] = [{"type": "text", "text": user_prompt}]
        for image_path in image_paths or []:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": _file_to_data_url(Path(image_path))},
                }
            )
        if transcript:
            content.append(
                {"type": "text", "text": f"User transcript: {transcript}"}
            )

        system_prompt = self._build_system_prompt(match_user_language)
        started_at = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                **self._llm_reasoning_kwargs(),
                **self._openrouter_request_options(),
                messages=self._cacheable_messages(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ]
                ),
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "LLM request failed after %.1f ms [model=%s reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.llm_model_name,
                self._llm_reasoning_label(),
            )
            raise ProviderError(f"LLM request failed: {exc}") from exc

        text = _extract_text_content(response.choices[0].message.content)
        if not text:
            raise ProviderError("LLM response was empty.")
        logger.info(
            "llm reply completed\nmodel      %s\nreasoning  %s\ntime       "
            "%.1f "
            "ms\nusage      %s\nreply      %s",
            self._settings.llm_model_name,
            self._llm_reasoning_label(),
            _elapsed_ms(started_at),
            _format_usage_summary(response),
            _preview_text(
                text,
                limit=140),
        )
        logger.debug(
            "LLM reply details [model=%s reasoning=%s usage=%s output=%s]",
            self._settings.llm_model_name,
            self._llm_reasoning_label(),
            _format_usage(response),
            _preview_text(text),
        )
        return text.strip()

    def generate_live_speech_reply(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
    ) -> LiveSpeechReply:
        started_at = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                **self._llm_reasoning_kwargs(),
                **self._openrouter_request_options(session_id=session_id),
                messages=self._cacheable_messages(
                    self._build_live_speech_messages(
                        transcript=transcript,
                        conversation_history=conversation_history,
                    )
                ),
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Live reply request failed after %.1f ms [model=%s "
                "reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.llm_model_name,
                self._llm_reasoning_label(),
            )
            raise ProviderError(f"Live reply request failed: {exc}") from exc

        text = _extract_text_content(response.choices[0].message.content)
        if not text:
            raise ProviderError("Live reply response was empty.")
        live_reply = self._parse_live_speech_reply(text)
        logger.info(
            "llm reply completed\nmodel      %s\nreasoning  %s\nvoice      "
            "%s\ntime       %.1f ms\nusage      %s\nreply      %s",
            self._settings.llm_model_name,
            self._llm_reasoning_label(),
            get_tts_voice_label(
                live_reply.voice_id),
            _elapsed_ms(started_at),
            _format_usage_summary(response),
            _preview_text(
                live_reply.text,
                limit=140),
        )
        logger.debug(
            "Live reply details [model=%s reasoning=%s usage=%s voice=%s "
            "output=%s]",
            self._settings.llm_model_name,
            self._llm_reasoning_label(),
            _format_usage(response),
            get_tts_voice_label(
                live_reply.voice_id),
            _preview_text(
                live_reply.text),
        )
        return live_reply

    def generate_live_speech_reply_from_audio(
        self,
        *,
        audio_path: str,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
        client=None,
        model_name: str | None = None,
        reasoning_kwargs: dict[str, str] | None = None,
        reasoning_label: str | None = None,
    ) -> LiveSpeechReply:
        path = Path(audio_path)
        if not path.exists():
            raise ProviderError(f"Audio file does not exist: {audio_path}")
        audio_bytes = path.read_bytes()
        if not audio_bytes:
            raise ProviderError("Audio file was empty.")
        upload_path, cleanup_upload = _prepare_audio_upload_path(path)

        active_client = client if client is not None else self._client
        active_model = model_name or self._settings.llm_model_name
        active_reasoning_kwargs = (
            reasoning_kwargs
            if reasoning_kwargs is not None
            else self._llm_reasoning_kwargs()
        )
        active_reasoning_label = (
            reasoning_label
            if reasoning_label is not None
            else self._llm_reasoning_label()
        )

        started_at = perf_counter()
        try:
            messages: list[dict] = [
                {
                    "role": "system",
                    "content": self._build_live_speech_system_prompt(),
                }
            ]
            messages.extend(_normalize_chat_messages(conversation_history))
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Listen to the user's spoken audio below and "
                            "reply with the final spoken text following all "
                            "the system instructions."
                        ),
                    },
                    {
                        "type": "input_audio",
                        "input_audio": _input_audio_payload_from_path(
                            upload_path
                        ),
                    },
                ],
            })

            response = active_client.chat.completions.create(
                model=active_model,
                **active_reasoning_kwargs,
                **self._openrouter_request_options(session_id=session_id),
                messages=self._cacheable_messages(messages),
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Multimodal live reply request failed after %.1f ms "
                "[model=%s reasoning=%s]",
                _elapsed_ms(started_at),
                active_model,
                active_reasoning_label,
            )
            raise ProviderError(
                f"Multimodal live reply request failed: {exc}"
            ) from exc
        finally:
            cleanup_upload()

        text = _extract_text_content(response.choices[0].message.content)
        if not text:
            raise ProviderError("Multimodal live reply response was empty.")
        live_reply = self._parse_live_speech_reply(text)
        logger.info(
            "llm multimodal reply completed\nmodel      %s\nreasoning  "
            "%s\nvoice      %s\ntime       %.1f ms\nusage      %s\nreply      "
            "%s",
            active_model,
            active_reasoning_label,
            get_tts_voice_label(
                live_reply.voice_id),
            _elapsed_ms(started_at),
            _format_usage_summary(response),
            _preview_text(
                live_reply.text,
                limit=140),
        )
        return live_reply

    def build_live_tool_messages_from_audio(
        self,
        *,
        audio_path: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        audio_part = _audio_message_part_from_path(audio_path)
        messages: list[dict] = [
            {
                "role": "system",
                "content": self._build_live_tool_speech_system_prompt(),
            }
        ]
        messages.extend(_normalize_chat_messages(conversation_history))
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Listen to the user's spoken audio below. Decide "
                        "whether to call an enabled tool or give the final "
                        "spoken answer. If no tool is needed, answer directly "
                        "with the final speech text. Call end_live_session "
                        "when the user clearly says they are done, says no to "
                        "more help, says everything is fine, says thanks after "
                        "a completed task, says goodbye or bye, or asks "
                        "Glance to stop listening."
                    ),
                },
                audio_part,
            ],
        })
        return messages

    def _build_live_speech_messages(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": self._build_live_speech_system_prompt(),
            }
        ]
        messages.extend(_normalize_chat_messages(conversation_history))
        messages.append({"role": "user", "content": transcript.strip()})
        return messages

    def build_live_tool_messages(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        system_prompt = self._build_system_prompt(match_user_language=True)
        system_prompt += (
            " You are running inside Glance Live mode with runtime tools "
            "available. Use a tool only when it materially helps answer the "
            "user's spoken request. Do not expose tool call names, JSON, "
            "arguments, raw fetched text, or screenshot metadata to the "
            "user. OCR is a clipboard action: when the user asks you to "
            "copy, read, extract, grab, transcribe, or get visible text from "
            "the screen, an image, a screenshot, a web page, a video frame, a "
            "document, a table, a label, or any UI element, call ocr_screen "
            "with the user's exact extraction instruction. The user does not "
            "need to say OCR. Do not use take_screenshot for text extraction "
            "requests; use ocr_screen so the result is copied to the "
            "clipboard. Then let Glance confirm that the result was copied. "
            "Never turn OCR output into the spoken final answer. "
            "Call end_live_session when the user clearly says they are done, "
            "says no to more help, says everything is fine, says thanks after "
            "a completed task, says goodbye or bye, or asks Glance to stop "
            "listening. When you have enough information, give only the final "
            "natural answer text. Do not narrate the tool work in the final "
            "answer; answer with the result directly."
        )
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        messages.extend(_normalize_chat_messages(conversation_history))
        messages.append({"role": "user", "content": transcript.strip()})
        return messages

    def parse_live_speech_reply(self, text: str) -> LiveSpeechReply:
        return self._parse_live_speech_reply(text)

    def run_tool_turn(
        self,
        *,
        messages: list[dict],
        tools: list[dict],
        session_id: str | None = None,
        client=None,
        model_name: str | None = None,
        reasoning_kwargs: dict[str, str] | None = None,
        reasoning_label: str | None = None,
    ) -> ProviderToolTurn:
        active_client = client if client is not None else self._client
        active_model = model_name or self._settings.llm_model_name
        active_reasoning_kwargs = (
            reasoning_kwargs
            if reasoning_kwargs is not None
            else self._llm_reasoning_kwargs()
        )
        active_reasoning_label = (
            reasoning_label
            if reasoning_label is not None
            else self._llm_reasoning_label()
        )
        started_at = perf_counter()
        kwargs: dict = {
            "model": active_model,
            **active_reasoning_kwargs,
            **self._openrouter_request_options(session_id=session_id),
            "messages": self._cacheable_messages(messages),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        try:
            response = active_client.chat.completions.create(**kwargs)
        except (
            Exception
        ) as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Tool-capable live request failed after %.1f ms [model=%s "
                "reasoning=%s]",
                _elapsed_ms(started_at),
                active_model,
                active_reasoning_label,
            )
            raise ProviderError(
                f"Tool-capable live request failed: {exc}"
            ) from exc

        message = response.choices[0].message
        content = _extract_text_content(getattr(message, "content", ""))
        tool_calls = _extract_provider_tool_calls(message)
        assistant_message: dict = {
            "role": "assistant",
            "content": content or None,
        }
        if tool_calls:
            assistant_message["tool_calls"] = [
                _provider_tool_call_to_message_payload(tool_call)
                for tool_call in getattr(message, "tool_calls", []) or []
            ]
        logger.info(
            "llm tool turn completed\nmodel      %s\nreasoning  %s\ntime      "
            "%.1f ms\nusage      %s\ntools      %s\nreply      %s",
            active_model,
            active_reasoning_label,
            _elapsed_ms(started_at),
            _format_usage_summary(response),
            ", ".join(
                call.name for call in tool_calls) or "none",
            _preview_text(
                content,
                limit=140),
        )
        return ProviderToolTurn(
            content=content.strip(),
            tool_calls=tool_calls,
            assistant_message=assistant_message,
        )

    def extract_text(self, image_path: str, *, instruction: str = "") -> str:
        prompt = OCR_EXTRACTION_PROMPT
        normalized_instruction = str(instruction).strip()
        if normalized_instruction:
            prompt += f"\n\nUser OCR request: {normalized_instruction}"
        return self.generate_reply(
            user_prompt=prompt,
            image_paths=[image_path],
        )

    def prepare_speech_text(
        self,
        text: str,
        *,
        session_id: str | None = None,
    ) -> LiveSpeechReply:
        started_at = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                **self._llm_reasoning_kwargs(),
                **self._openrouter_request_options(session_id=session_id),
                messages=self._cacheable_messages(
                    [
                        {
                            "role": "system",
                            "content": self._build_tts_preparation_prompt(),
                        },
                        {"role": "user", "content": text},
                    ]
                ),
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Speech text preparation failed after %.1f ms [model=%s "
                "reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.llm_model_name,
                self._llm_reasoning_label(),
            )
            raise ProviderError(
                f"Speech text preparation failed: {exc}"
            ) from exc

        prepared_text = _extract_text_content(
            response.choices[0].message.content
        )
        if not prepared_text:
            raise ProviderError(
                "Speech text preparation returned empty output."
            )
        prepared_reply = self._parse_live_speech_reply(prepared_text)
        logger.info(
            "speech text prepared\nmodel      %s\nreasoning  %s\nvoice      "
            "%s\ntime       %.1f ms\nusage      %s\nreply      %s",
            self._settings.llm_model_name,
            self._llm_reasoning_label(),
            get_tts_voice_label(
                prepared_reply.voice_id),
            _elapsed_ms(started_at),
            _format_usage_summary(response),
            _preview_text(
                prepared_reply.text,
                limit=140),
        )
        logger.debug(
            "Speech prep details [model=%s reasoning=%s usage=%s voice=%s "
            "output=%s]",
            self._settings.llm_model_name,
            self._llm_reasoning_label(),
            _format_usage(response),
            get_tts_voice_label(
                prepared_reply.voice_id),
            _preview_text(
                prepared_reply.text),
        )
        return prepared_reply

    def _llm_reasoning_kwargs(self) -> dict[str, str]:
        if not self._settings.llm_reasoning_enabled:
            return {}
        return {"reasoning_effort": self._settings.llm_reasoning}

    def _llm_reasoning_label(self) -> str:
        if not self._settings.llm_reasoning_enabled:
            return "off"
        return self._settings.llm_reasoning

    def _build_system_prompt(self, match_user_language: bool) -> str:
        prompt = _with_runtime_context(
            self._resolve_prompt_override(
                "text_prompt_override", DEFAULT_TEXT_REPLY_PROMPT
            )
        )
        override = self._shared_prompt_override()
        if override:
            prompt += f" Additional instructions: {override}"
        prompt += _language_reply_instruction()
        prompt += (
            " Keep the delivery conversational and pleasant, without "
            "sounding forced, overly cheerful, or theatrical."
        )
        return prompt

    def _build_live_tool_speech_system_prompt(self) -> str:
        prompt = self._build_live_speech_system_prompt()
        prompt += (
            " Runtime tools are available in this live turn. Use a tool only "
            "when it materially helps answer the user's spoken request. If "
            "you need a tool, call the tool instead of giving a final "
            "answer. Tool calls, tool names, JSON, arguments, raw fetched "
            "text, and screenshot metadata are private runtime details; "
            "never say them to the user. OCR is a clipboard action: when the "
            "user asks you to copy, read, extract, grab, transcribe, or get "
            "visible text from the screen, an image, a screenshot, a web "
            "page, a video frame, a document, a table, a label, or any UI "
            "element, call ocr_screen with the user's exact extraction "
            "instruction. The user does not need to say OCR. Do not use "
            "take_screenshot for text extraction requests; use ocr_screen so "
            "the result is copied to the clipboard. Then let Glance confirm "
            "that the result was copied. Never turn OCR output into the "
            "spoken final answer. Call end_live_session when the user "
            "clearly says they are done, says no to more help, says everything "
            "is fine, says thanks after a completed task, says goodbye or bye, "
            "or asks Glance to stop listening. When you have enough information, "
            "give only the final spoken answer and follow all voice, "
            "emotion, and VOICE_ID rules above. Do not narrate the tool work "
            "in the final answer; answer with the result directly."
        )
        return prompt

    def _build_live_speech_system_prompt(self) -> str:
        prompt = _with_runtime_context(
            self._resolve_prompt_override(
                "voice_prompt_override", DEFAULT_VOICE_REPLY_PROMPT
            )
        )
        override = self._shared_prompt_override()
        if override:
            prompt += f" Additional instructions: {override}"
        prompt += _language_reply_instruction()
        if self._settings.tts_voice_id == AUTO_TTS_VOICE_ID:
            prompt += (
                " Auto voice selection is active. First choose the single "
                "best voice ID from the allowed list below, based on the "
                "emotional shape and style of your answer. Output the first "
                "line exactly as `VOICE_ID: <id>`, then leave one blank "
                "line, then output only the final speech text. Never output "
                "any voice ID outside this list. Do not default to the same "
                "upbeat voice for every positive or generic answer. For "
                "ordinary everyday conversation and casual back-and-forth, "
                "prefer Mark unless another voice is clearly a better fit. "
                "Choose the voice before composing the final reply."
            )
            for voice in ELEVEN_V3_VOICES:
                prompt += (
                    f" Allowed voice: {voice.id} - {voice.name} - "
                    f"{voice.title} - "
                    f"{voice.prompt_summary}."
                )
        else:
            voice = get_tts_voice(self._settings.tts_voice_id)
            if voice is not None:
                prompt += (
                    f" The active voice is fixed to {voice.name} "
                    f"({voice.title}). Shape the final speech text so it "
                    f"suits this voice's strengths: {voice.prompt_summary}. "
                    "Do "
                    "not output a VOICE_ID header when a fixed voice is "
                    "already selected."
                )
        return prompt

    def _parse_live_speech_reply(self, text: str) -> LiveSpeechReply:
        stripped_text = text.strip()
        if self._settings.tts_voice_id != AUTO_TTS_VOICE_ID:
            return LiveSpeechReply(
                voice_id=self._settings.tts_voice_id,
                text=stripped_text,
            )

        match = re.match(r"^VOICE_ID:\s*(\S+)\s*(?:\n+|$)", stripped_text)
        if match is None:
            logger.warning(
                "Auto voice reply was missing a VOICE_ID header; falling "
                "back to %s.",
                get_tts_voice_label(DEFAULT_FIXED_TTS_VOICE),
            )
            return LiveSpeechReply(DEFAULT_FIXED_TTS_VOICE, stripped_text)

        parsed_voice_id = match.group(1).strip()
        remaining_text = stripped_text[match.end():].strip()
        if parsed_voice_id not in {voice.id for voice in ELEVEN_V3_VOICES}:
            logger.warning(
                "Auto voice reply chose unknown voice id %s; falling back to "
                "%s.",
                parsed_voice_id,
                get_tts_voice_label(DEFAULT_FIXED_TTS_VOICE),
            )
            return LiveSpeechReply(
                DEFAULT_FIXED_TTS_VOICE,
                remaining_text or stripped_text,
            )
        if not remaining_text:
            raise ProviderError(
                "Live reply response did not include final speech text."
            )
        return LiveSpeechReply(parsed_voice_id, remaining_text)

    def _build_tts_preparation_prompt(self) -> str:
        prompt = self._resolve_prompt_override(
            "voice_polish_prompt_override", DEFAULT_TTS_PREPARATION_PROMPT
        )
        if self._settings.tts_voice_id == AUTO_TTS_VOICE_ID:
            prompt += (
                " Auto voice selection is active. First choose the single "
                "best voice ID from the allowed list below, based on the "
                "emotional shape and style of the reply. Output the first "
                "line exactly as `VOICE_ID: <id>`, then leave one blank "
                "line, then output only the final speech text. Never output "
                "any voice ID outside this list."
            )
            for voice in ELEVEN_V3_VOICES:
                prompt += (
                    f" Allowed voice: {voice.id} - {voice.name} - "
                    f"{voice.title} - "
                    f"{voice.prompt_summary}."
                )
        else:
            voice = get_tts_voice(self._settings.tts_voice_id)
            if voice is not None:
                prompt += (
                    f" The active voice is fixed to {voice.name} "
                    f"({voice.title}). Shape the final speech text so it "
                    f"suits this voice's strengths: {voice.prompt_summary}. "
                    "Do "
                    "not output a VOICE_ID header when a fixed voice is "
                    "already selected."
                )
        return prompt

    def _is_openrouter(self) -> bool:
        parsed = urlparse(self._settings.llm_base_url)
        host = parsed.netloc.lower()
        return host == "openrouter.ai" or host.endswith(".openrouter.ai")

    def _openrouter_request_options(
        self, *, session_id: str | None = None
    ) -> dict:
        if not self._is_openrouter():
            return {}
        options: dict = {"extra_body": {"usage": {"include": True}}}
        normalized_session_id = (session_id or "").strip()
        if normalized_session_id:
            options["extra_headers"] = {
                "x-session-affinity": normalized_session_id
            }
            options["extra_body"].update(
                {
                    "session_id": normalized_session_id,
                    "prompt_cache_key": normalized_session_id,
                }
            )
        return options

    def _cacheable_messages(self, messages: list[dict]) -> list[dict]:
        if not self._is_openrouter():
            return messages
        return [
            _mark_cacheable_system_message(message) for message in messages
        ]


class NagaTranscriptionProvider:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._client = self._build_client(
            base_url=settings.transcription_base_url,
            api_key=settings.transcription_api_key,
        )

    @property
    def client(self):
        return self._client

    @property
    def model_name(self) -> str:
        return self._settings.transcription_model_name

    def reasoning_kwargs(self) -> dict[str, str]:
        return self._transcription_reasoning_kwargs()

    def reasoning_label(self) -> str:
        return self._transcription_reasoning_label()

    @staticmethod
    def _build_client(base_url: str, api_key: str):
        if OpenAI is None:
            raise ProviderError(
                "The 'openai' package is required for transcription access."
            )
        if not api_key:
            raise ProviderError("Missing transcription API key.")
        return OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"Accept-Encoding": "identity"},
        )

    def transcribe(self, audio_path: str) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise ProviderError(f"Audio file does not exist: {audio_path}")
        audio_bytes = path.read_bytes()
        if not audio_bytes:
            raise ProviderError("Audio file was empty.")

        started_at = perf_counter()
        upload_path, cleanup_upload = _prepare_audio_upload_path(path)
        try:
            if self._uses_transcriptions_api():
                with upload_path.open("rb") as audio_file:
                    response = self._client.audio.transcriptions.create(
                        model=self._settings.transcription_model_name,
                        file=audio_file,
                        prompt=self._build_transcription_prompt(),
                        language=None,
                    )
            else:
                if upload_path != path:
                    audio_bytes = upload_path.read_bytes()
                    if not audio_bytes:
                        raise ProviderError("Audio file was empty.")
                audio_format = upload_path.suffix.lower().lstrip(".") or "wav"
                response = self._client.chat.completions.create(
                    model=self._settings.transcription_model_name,
                    **self._transcription_reasoning_kwargs(),
                    messages=[
                        {
                            "role": "system",
                            "content": self._build_transcription_prompt(),
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Transcribe this audio.",
                                },
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": base64.b64encode(
                                            audio_bytes
                                        ).decode("ascii"),
                                        "format": audio_format,
                                    },
                                },
                            ],
                        },
                    ],
                )
        except (
            Exception
        ) as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Transcription request failed after %.1f ms [model=%s "
                "reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.transcription_model_name,
                self._transcription_reasoning_label(),
            )
            raise ProviderError(
                f"Transcription request failed: {exc}"
            ) from exc
        finally:
            cleanup_upload()

        if self._uses_transcriptions_api():
            text = getattr(response, "text", "")
        else:
            text = _extract_text_content(response.choices[0].message.content)
        if not text:
            raise ProviderError("Transcription response was empty.")
        logger.info(
            "transcription completed\nmodel      %s\nreasoning  %s\ntime      "
            "%.1f ms\nusage      %s\nheard      %s",
            self._settings.transcription_model_name,
            self._transcription_reasoning_label(),
            _elapsed_ms(started_at),
            _format_usage_summary(response),
            _preview_text(
                text,
                limit=140),
        )
        logger.debug(
            "Transcription details [model=%s reasoning=%s usage=%s output=%s]",
            self._settings.transcription_model_name,
            self._transcription_reasoning_label(),
            _format_usage(response),
            _preview_text(text),
        )
        return text.strip()

    def _transcription_reasoning_kwargs(self) -> dict[str, str]:
        if not self._settings.transcription_reasoning_enabled:
            return {}
        return {"reasoning_effort": self._settings.transcription_reasoning}

    def _transcription_reasoning_label(self) -> str:
        if not self._settings.transcription_reasoning_enabled:
            return "off"
        return self._settings.transcription_reasoning

    def _uses_transcriptions_api(self) -> bool:
        return self._settings.transcription_model_name.startswith("whisper")

    def _build_transcription_prompt(self) -> str:
        override = self._settings.transcription_prompt_override.strip()
        return override or DEFAULT_TRANSCRIPTION_PROMPT


class NagaSpeechProvider:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._client = self._build_client(
            base_url=settings.tts_base_url,
            api_key=settings.tts_api_key,
        )

    @staticmethod
    def _build_client(base_url: str, api_key: str):
        if OpenAI is None:
            raise ProviderError(
                "The 'openai' package is required for TTS access."
            )
        if not api_key:
            raise ProviderError("Missing TTS API key.")
        return OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"Accept-Encoding": "identity"},
        )

    def synthesize(
        self,
        text: str,
        output_path: Path,
        *,
        voice_id: str | None = None,
    ) -> str:
        started_at = perf_counter()
        resolved_voice_id = voice_id or self._settings.tts_voice_id
        if resolved_voice_id == AUTO_TTS_VOICE_ID:
            resolved_voice_id = DEFAULT_FIXED_TTS_VOICE
        try:
            requested_format = _speech_response_format(output_path)
            with self._client.audio.speech.with_streaming_response.create(
                model=self._settings.tts_model,
                voice=resolved_voice_id,
                input=text,
                response_format=requested_format,
            ) as response:
                response.stream_to_file(output_path)
                content_type = response.headers.get("content-type", "")
            output_path = _normalize_synthesized_audio(
                output_path,
                requested_format,
                content_type=content_type,
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "TTS request failed after %.1f ms [model=%s voice=%s]",
                _elapsed_ms(started_at),
                self._settings.tts_model,
                get_tts_voice_label(resolved_voice_id),
            )
            raise ProviderError(f"TTS request failed: {exc}") from exc
        logger.info(
            "speech synthesis completed\nmodel      %s\nvoice      %s\n"
            "time      %.1f ms\nspoken     %s",
            self._settings.tts_model,
            get_tts_voice_label(resolved_voice_id),
            _elapsed_ms(started_at),
            _preview_text(
                text,
                limit=140),
        )
        logger.debug(
            "Speech synthesis details [model=%s voice=%s input=%s]",
            self._settings.tts_model,
            get_tts_voice_label(resolved_voice_id),
            _preview_text(text),
        )
        return str(output_path)


def _speech_response_format(output_path: Path) -> str:
    suffix = output_path.suffix.lower().lstrip(".")
    if suffix:
        return suffix
    return "mp3"


def _normalize_synthesized_audio(
    output_path: Path,
    requested_format: str,
    *,
    content_type: str = "",
) -> Path:
    actual_format = _detect_audio_format(output_path)
    if actual_format is None or actual_format == requested_format:
        if requested_format == "wav" and _should_wrap_pcm_as_wav(
            output_path, actual_format=actual_format, content_type=content_type
        ):
            return _wrap_pcm_file_as_wav(output_path)
        return output_path

    logger.warning(
        "TTS provider returned %s while %s was requested for %s",
        actual_format,
        requested_format,
        output_path.name,
    )

    if requested_format == "wav":
        converted_path = _convert_audio_to_wav(output_path)
        if converted_path is not None:
            return converted_path

    normalized_path = output_path.with_suffix(f".{actual_format}")
    if normalized_path == output_path:
        return output_path
    output_path.replace(normalized_path)
    return normalized_path


def _should_wrap_pcm_as_wav(
    output_path: Path,
    *,
    actual_format: str | None,
    content_type: str,
) -> bool:
    if actual_format is not None:
        return False
    if not output_path.exists() or output_path.stat().st_size == 0:
        return False
    normalized_content_type = content_type.lower().split(";", 1)[0].strip()
    if not normalized_content_type:
        return True
    return normalized_content_type in {
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
        "audio/pcm",
        "audio/mp3",
        "audio/mpeg",
        "application/octet-stream",
    }


def _wrap_pcm_file_as_wav(output_path: Path) -> Path:
    pcm_bytes = output_path.read_bytes()
    temp_path = output_path.with_name(f"{output_path.stem}-pcm-wrap.wav")
    with wave.open(str(temp_path), "wb") as wav_file:
        wav_file.setnchannels(_PCM_CHANNELS)
        wav_file.setsampwidth(_PCM_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(_PCM_SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)
    output_path.unlink(missing_ok=True)
    temp_path.replace(output_path)
    logger.debug(
        "Wrapped headerless PCM stream as WAV for %s using %d Hz mono s16le.",
        output_path.name,
        _PCM_SAMPLE_RATE,
    )
    return output_path


def _detect_audio_format(output_path: Path) -> str | None:
    try:
        header = output_path.read_bytes()[:16]
    except OSError:
        return None
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return "wav"
    if header.startswith(b"ID3"):
        return "mp3"
    if _looks_like_mp3_frame_header(header):
        return "mp3"
    return None


def _looks_like_mp3_frame_header(header: bytes) -> bool:
    if len(header) < 4:
        return False
    if header[0] != 0xFF or (header[1] & 0xE0) != 0xE0:
        return False

    version_bits = (header[1] >> 3) & 0x03
    layer_bits = (header[1] >> 1) & 0x03
    bitrate_index = (header[2] >> 4) & 0x0F
    sample_rate_index = (header[2] >> 2) & 0x03

    if version_bits == 0x01:
        return False
    if layer_bits == 0x00:
        return False
    if bitrate_index in {0x00, 0x0F}:
        return False
    if sample_rate_index == 0x03:
        return False
    return True


def _convert_audio_to_wav(output_path: Path) -> Path | None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        logger.warning(
            "ffmpeg is unavailable, keeping synthesized audio in its original "
            "format."
        )
        return None

    converted_path = output_path.with_name(f"{output_path.stem}-converted.wav")
    try:
        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(output_path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                str(converted_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning(
            "ffmpeg WAV conversion failed for %s: %s", output_path.name, exc
        )
        try:
            converted_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    output_path.unlink(missing_ok=True)
    converted_path.replace(output_path)
    return output_path


def _prepare_audio_upload_path(
    source_path: Path,
) -> tuple[Path, Callable[[], None]]:
    if source_path.suffix.lower() == ".mp3":
        return source_path, _noop_cleanup

    converted_path = _convert_audio_to_mp3(source_path)
    if converted_path is None:
        return source_path, _noop_cleanup
    return converted_path, lambda: _cleanup_temp_audio_file(converted_path)


def _convert_audio_to_mp3(source_path: Path) -> Path | None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        logger.warning(
            "ffmpeg is unavailable, uploading original audio format for %s.",
            source_path.name,
        )
        return None

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        prefix=f"{source_path.stem}-upload-",
        delete=False,
    )
    temp_file.close()
    converted_path = Path(temp_file.name)
    try:
        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source_path),
                "-vn",
                "-acodec",
                "libmp3lame",
                "-b:a",
                "32k",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(converted_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning(
            "ffmpeg MP3 conversion failed for %s: %s", source_path.name, exc
        )
        _cleanup_temp_audio_file(converted_path)
        return None

    return converted_path


def _cleanup_temp_audio_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _noop_cleanup() -> None:
    return None


def _with_runtime_context(prompt: str) -> str:
    return f"{_runtime_context_prompt()}\n\n{prompt}"


def _runtime_context_prompt() -> str:
    return (
        "Current day and time: "
        f"{_format_runtime_datetime(_current_local_datetime())}.\n"
        f"User country: {_detect_user_country()}.\n"
        "Use the current day, date, time, year, timezone, and user country "
        "above as the source of truth."
    )


def _current_local_datetime() -> datetime:
    return datetime.now().astimezone()


def _format_runtime_datetime(moment: datetime) -> str:
    timezone_name = moment.tzname() or _format_utc_offset(moment)
    return (
        f"{moment.strftime('%A')}, {moment.strftime('%B')} {moment.day}, "
        f"{moment.year}, {moment.strftime('%H:%M')} {timezone_name} "
        f"({_format_utc_offset(moment)})"
    )


def _format_utc_offset(moment: datetime) -> str:
    offset = moment.utcoffset()
    if offset is None:
        return "UTC"
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _detect_user_country() -> str:
    explicit_country = os.environ.get("GLANCE_USER_COUNTRY", "").strip()
    if explicit_country:
        return explicit_country

    timezone_name = _local_timezone_name()
    if timezone_name in _TIMEZONE_COUNTRY_OVERRIDES:
        return _TIMEZONE_COUNTRY_OVERRIDES[timezone_name]

    region_code = _locale_region_code()
    if region_code in _COUNTRY_BY_REGION_CODE:
        return _COUNTRY_BY_REGION_CODE[region_code]
    return "Unknown"


def _local_timezone_name() -> str:
    env_timezone = os.environ.get("TZ", "").strip()
    if "/" in env_timezone:
        return env_timezone.lstrip(":")

    try:
        localtime_path = os.path.realpath("/etc/localtime")
    except OSError:
        return ""
    marker = "/zoneinfo/"
    if marker not in localtime_path:
        return ""
    return localtime_path.split(marker, 1)[1]


def _locale_region_code() -> str:
    locale_names: list[str | None] = [locale.getlocale()[0]]
    locale_names.extend(
        os.environ.get(name) for name in ("LC_ALL", "LC_MESSAGES", "LANG")
    )
    for locale_name in locale_names:
        if not locale_name:
            continue
        normalized = locale_name.split(".", 1)[0].split("@", 1)[0]
        if "_" not in normalized:
            continue
        region_code = normalized.rsplit("_", 1)[1].upper()
        if region_code:
            return region_code
    return ""


def _audio_message_part_from_path(audio_path: str) -> dict:
    path = Path(audio_path)
    if not path.exists():
        raise ProviderError(f"Audio file does not exist: {audio_path}")
    if not path.read_bytes():
        raise ProviderError("Audio file was empty.")

    upload_path, cleanup_upload = _prepare_audio_upload_path(path)
    try:
        return {
            "type": "input_audio",
            "input_audio": _input_audio_payload_from_path(upload_path),
        }
    finally:
        cleanup_upload()


def _input_audio_payload_from_path(audio_path: Path) -> dict[str, str]:
    audio_bytes = audio_path.read_bytes()
    if not audio_bytes:
        raise ProviderError("Audio file was empty.")
    audio_format = audio_path.suffix.lower().lstrip(".") or "wav"
    return {
        "data": base64.b64encode(audio_bytes).decode("ascii"),
        "format": audio_format,
    }


def _language_reply_instruction() -> str:
    return (
        " Reply in the same language as the user's request, unless the user "
        "explicitly asks you to use another language. If they ask for "
        "another language, answer in that language immediately in the same "
        "reply. Do not claim you are limited to English or cannot speak a "
        "requested language; attempt the requested language directly."
    )


def _file_to_data_url(file_path: Path) -> str:
    if not file_path.exists():
        raise ProviderError(f"Image file does not exist: {file_path}")
    mime_type, _ = mimetypes.guess_type(file_path.name)
    mime_type = mime_type or "application/octet-stream"
    payload = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


def _extract_provider_tool_calls(message) -> list[ProviderToolCall]:
    parsed_calls: list[ProviderToolCall] = []
    for tool_call in getattr(message, "tool_calls", []) or []:
        function = _tool_call_attr(tool_call, "function")
        name = str(_tool_call_attr(function, "name") or "")
        arguments_text = str(_tool_call_attr(function, "arguments") or "{}")
        try:
            arguments = json.loads(arguments_text)
        except json.JSONDecodeError:
            arguments = {"_raw_arguments": arguments_text}
        if not isinstance(arguments, dict):
            arguments = {"_raw_arguments": arguments_text}
        parsed_calls.append(
            ProviderToolCall(
                call_id=str(_tool_call_attr(tool_call, "id") or ""),
                name=name,
                arguments=arguments,
            )
        )
    return parsed_calls


def _provider_tool_call_to_message_payload(tool_call) -> dict:
    function = _tool_call_attr(tool_call, "function")
    return {
        "id": str(_tool_call_attr(tool_call, "id") or ""),
        "type": "function",
        "function": {
            "name": str(_tool_call_attr(function, "name") or ""),
            "arguments": str(_tool_call_attr(function, "arguments") or "{}"),
        },
    }


def _tool_call_attr(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            text = _extract_part_text(part)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    text = _extract_part_text(content)
    return text or ""


def _extract_part_text(part) -> str | None:
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        if part.get("type") == "text":
            text_value = part.get("text")
            if isinstance(text_value, dict):
                return text_value.get("value")
            return text_value
        return part.get("text")

    part_type = getattr(part, "type", None)
    if part_type == "text":
        text_value = getattr(part, "text", None)
        if hasattr(text_value, "value"):
            return text_value.value
        return text_value

    text_value = getattr(part, "text", None)
    if hasattr(text_value, "value"):
        return text_value.value
    return text_value


def _mark_cacheable_system_message(message: dict) -> dict:
    if message.get("role") != "system":
        return message

    content = message.get("content")
    marked_message = dict(message)
    if isinstance(content, str):
        marked_message["content"] = [
            {
                "type": "text",
                "text": content,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        return marked_message

    if isinstance(content, list) and content:
        marked_parts = []
        marked_index = _last_text_part_index(content)
        for index, part in enumerate(content):
            if index == marked_index and isinstance(part, dict):
                marked_part = dict(part)
                marked_part["cache_control"] = {"type": "ephemeral"}
                marked_parts.append(marked_part)
                continue
            marked_parts.append(part)
        marked_message["content"] = marked_parts
    return marked_message


def _last_text_part_index(parts: list) -> int | None:
    for index in range(len(parts) - 1, -1, -1):
        part = parts[index]
        if isinstance(part, dict) and part.get("type") == "text":
            return index
    return None


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 1)


def _preview_text(text: str, *, limit: int = 320) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return "." * limit
    return normalized[: limit - 3].rstrip() + "..."


def _format_usage(response) -> str:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return "n/a"

    usage = _normalize_usage_payload(usage)
    if not usage:
        return "n/a"

    flattened_usage = dict(_flatten_mapping(usage))
    details: list[str] = []
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "cached_tokens",
        "prompt_tokens_details.cached_tokens",
        "input_tokens_details.cached_tokens",
        "cache_write_tokens",
        "cache_creation_input_tokens",
        "prompt_tokens_details.cache_write_tokens",
        "prompt_tokens_details.cache_creation_input_tokens",
        "input_tokens_details.cache_write_tokens",
        "input_tokens_details.cache_creation_input_tokens",
        "output_tokens_details.reasoning_tokens",
    ):
        value = flattened_usage.pop(key, None)
        if value is not None:
            details.append(f"{key}={value}")

    for key, value in flattened_usage.items():
        details.append(f"{key}={value}")

    return ",".join(details) if details else "n/a"


def _format_usage_summary(response) -> str:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return "n/a"

    flattened_usage = dict(_flatten_mapping(_normalize_usage_payload(usage)))
    summary_parts: list[str] = []
    for label, keys in (
        ("total", ("total_tokens",)),
        ("prompt", ("prompt_tokens", "input_tokens")),
        ("completion", ("completion_tokens", "output_tokens")),
        (
            "reasoning",
            ("reasoning_tokens", "output_tokens_details.reasoning_tokens"),
        ),
        (
            "cached",
            (
                "cached_tokens",
                "prompt_tokens_details.cached_tokens",
                "input_tokens_details.cached_tokens",
            ),
        ),
        (
            "cache_write",
            (
                "cache_write_tokens",
                "cache_creation_input_tokens",
                "prompt_tokens_details.cache_write_tokens",
                "prompt_tokens_details.cache_creation_input_tokens",
                "input_tokens_details.cache_write_tokens",
                "input_tokens_details.cache_creation_input_tokens",
            ),
        ),
        ("cost", ("cost",)),
    ):
        for key in keys:
            value = flattened_usage.get(key)
            if value is not None:
                summary_parts.append(f"{label}={value}")
                break

    return ", ".join(summary_parts) if summary_parts else "n/a"


def _normalize_chat_messages(
    messages: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    normalized_messages: list[dict[str, str]] = []
    for message in messages or []:
        role = str(message.get("role", "")).strip().lower()
        content = message.get("content", "")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str):
            content = _extract_text_content(content)
        stripped_content = content.strip()
        if not stripped_content:
            continue
        normalized_messages.append({"role": role, "content": stripped_content})
    return normalized_messages


def _normalize_usage_payload(value):
    if isinstance(value, dict):
        return {
            key: _normalize_usage_payload(item)
            for key, item in value.items()
            if item is not None
        }
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _normalize_usage_payload(model_dump(exclude_none=True))
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _normalize_usage_payload(to_dict())
    try:
        public_attributes = {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_") and item is not None
        }
    except TypeError:
        return value
    if not public_attributes:
        return value
    return {
        key: _normalize_usage_payload(item)
        for key, item in public_attributes.items()
    }


def _flatten_mapping(mapping: dict, prefix: str = ""):
    for key, value in mapping.items():
        composed_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and value:
            yield from _flatten_mapping(value, composed_key)
            continue
        yield composed_key, value
