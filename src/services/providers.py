from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path
from time import perf_counter

from src.exceptions.app_exceptions import ProviderError
from src.models.settings import AppSettings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised only without optional dependency.
    OpenAI = None


logger = logging.getLogger("glance.providers")


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
            raise ProviderError("The 'openai' package is required for provider access.")
        if not api_key:
            raise ProviderError("Missing LLM API key.")
        return OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"Accept-Encoding": "identity"},
        )

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
            content.append({"type": "text", "text": f"User transcript: {transcript}"})

        system_prompt = self._build_system_prompt(match_user_language)
        started_at = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                reasoning_effort=self._settings.llm_reasoning,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "LLM request failed after %.1f ms [model=%s reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.llm_model_name,
                self._settings.llm_reasoning,
            )
            raise ProviderError(f"LLM request failed: {exc}") from exc

        text = _extract_text_content(response.choices[0].message.content)
        if not text:
            raise ProviderError("LLM response was empty.")
        logger.info(
            "LLM reply completed in %.1f ms [model=%s reasoning=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.llm_model_name,
            self._settings.llm_reasoning,
            _preview_text(text),
        )
        return text.strip()

    def generate_live_speech_reply(self, *, transcript: str) -> str:
        started_at = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                reasoning_effort=self._settings.llm_reasoning,
                messages=[
                    {
                        "role": "system",
                        "content": self._build_live_speech_system_prompt(),
                    },
                    {"role": "user", "content": transcript.strip()},
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Live reply request failed after %.1f ms [model=%s reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.llm_model_name,
                self._settings.llm_reasoning,
            )
            raise ProviderError(f"Live reply request failed: {exc}") from exc

        text = _extract_text_content(response.choices[0].message.content)
        if not text:
            raise ProviderError("Live reply response was empty.")
        logger.info(
            "LLM reply completed in %.1f ms [model=%s reasoning=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.llm_model_name,
            self._settings.llm_reasoning,
            _preview_text(text),
        )
        return text.strip()

    def extract_text(self, image_path: str) -> str:
        prompt = "Extract all visible text exactly as written. Preserve line breaks where useful."
        return self.generate_reply(user_prompt=prompt, image_paths=[image_path])

    def prepare_speech_text(self, text: str) -> str:
        started_at = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                reasoning_effort=self._settings.llm_reasoning,
                messages=[
                    {
                        "role": "system",
                        "content": self._build_tts_preparation_prompt(),
                    },
                    {"role": "user", "content": text},
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Speech text preparation failed after %.1f ms [model=%s reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.llm_model_name,
                self._settings.llm_reasoning,
            )
            raise ProviderError(f"Speech text preparation failed: {exc}") from exc

        prepared_text = _extract_text_content(response.choices[0].message.content)
        if not prepared_text:
            raise ProviderError("Speech text preparation returned empty output.")
        logger.info(
            "Speech text preparation completed in %.1f ms [model=%s reasoning=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.llm_model_name,
            self._settings.llm_reasoning,
            _preview_text(prepared_text),
        )
        return prepared_text.strip()

    def _build_system_prompt(self, match_user_language: bool) -> str:
        prompt = (
            "You are Glance, a live desktop voice assistant. Respond like a helpful, friendly "
            "person in a real spoken back-and-forth conversation. Prioritize being useful, clear, "
            "accurate, and easy to follow. Keep answers natural and easy to speak aloud. Be "
            "concise by default, but include enough detail to genuinely help. Prefer natural "
            "sentences over lists. Do not use markdown, code fences, or visual formatting unless "
            "the user explicitly asks for them."
        )
        override = self._settings.system_prompt_override.strip()
        if override:
            prompt += f" Additional instructions: {override}"
        if match_user_language:
            prompt += (
                " Reply in the same language as the user's spoken request, unless the user "
                "explicitly asks you to use another language. If they ask for another language, "
                "answer in that language immediately in the same reply."
            )
        else:
            prompt += (
                f" Reply in {self._settings.fallback_language} unless the user explicitly asks "
                "for another language. If they ask for another language, answer in that language "
                "immediately in the same reply."
            )
        prompt += (
            " Keep the delivery conversational and pleasant, without sounding forced, overly "
            "cheerful, or theatrical."
        )
        return prompt

    def _build_live_speech_system_prompt(self) -> str:
        prompt = (
            "You are Glance, a live desktop voice assistant. The user's message is a transcript of "
            "what they just said aloud. Your job is to answer them directly and produce the final "
            "spoken text that will be sent straight to Eleven v3. Respond like a warm, lively, "
            "friendly person in a real back-and-forth conversation. Be genuinely helpful, clear, "
            "accurate, and pleasant to listen to. Match the length to what the user actually said: "
            "keep greetings, thanks, acknowledgments, and casual check-ins short and natural, and "
            "only give longer answers when the user is clearly asking for more. Make the reply easy "
            "to understand in one listen. Use natural spoken phrasing, not visual writing. Do not "
            "use markdown, code fences, bullets, or visual formatting. Do not explain your process. "
            "Do not rewrite, critique, or correct another assistant message. Do not change speaker "
            "identity or perspective. Do not mention Claude, Anthropic, or being an AI unless the "
            "user explicitly asks. Preserve meaning and do not add facts. This output is already "
            "the final speech text, so shape it for spoken delivery in this same answer. Normalize "
            "hard-to-speak text into spoken forms when helpful, including abbreviations, symbols, "
            "dates, times, currencies, shortcuts, URLs, percentages, and similar text. Use "
            "punctuation, capitalization, ellipses, and line breaks for pacing only when they help. "
            "Actively use light, contextual Eleven v3 vocal tags when they improve warmth, "
            "friendliness, liveliness, or emotional clarity. In most replies, use some expressive "
            "shaping when it helps the speech feel more human and engaging, but do not overdo it or "
            "sound theatrical. Allowed vocal tags include [laughs], [laughs harder], [starts "
            "laughing], [wheezing], [whispers], [sighs], [exhales], [sarcastic], [curious], "
            "[excited], [crying], [snorts], [mischievously], [swallows], [gulps], [sings], [woo], "
            "[strong X accent], and [fart]."
        )
        override = self._settings.system_prompt_override.strip()
        if override:
            prompt += f" Additional instructions: {override}"
        prompt += (
            " Reply in the same language as the user's spoken request, unless the user explicitly "
            "asks you to use another language. If they ask for another language, answer in that "
            "language immediately in the same reply."
        )
        return prompt

    @staticmethod
    def _build_tts_preparation_prompt() -> str:
        return (
            "You prepare the final spoken text for Eleven v3 text to speech. Return only the "
            "final speech text. Preserve meaning and do not add facts. Your job is to make the "
            "response sound natural, expressive, dynamic, and pleasant to listen to rather than "
            "flat or mechanical. Actively add Eleven v3 vocal tags when they improve delivery. "
            "This is a normal part of the task, not a rare exception. In most replies, use light, "
            "contextual vocal shaping when it helps the speech feel more human, warm, playful, "
            "curious, reassuring, or expressive. If vocal tags would make the line worse, "
            "distracting, exaggerated, or tonally wrong, leave them out. Normalize hard-to-speak "
            "text into spoken forms when helpful, including abbreviations, symbols, dates, times, "
            "currencies, shortcuts, URLs, percentages, and similar text. Remove markdown, code "
            "fences, tables, bullets, and other visual-only formatting. Eleven v3 does not support "
            "SSML, so never use SSML tags. Use punctuation, capitalization, ellipses, and line "
            "breaks for pacing when they improve spoken delivery. Allowed vocal tags include "
            "[laughs], [laughs harder], [starts laughing], [wheezing], [whispers], [sighs], "
            "[exhales], [sarcastic], [curious], [excited], [crying], [snorts], [mischievously], "
            "[swallows], [gulps], [sings], [woo], [strong X accent], and [fart]. Use them "
            "deliberately and contextually, not randomly or excessively."
        )


class NagaTranscriptionProvider:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._client = self._build_client(
            base_url=settings.transcription_base_url,
            api_key=settings.transcription_api_key,
        )

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
        try:
            if self._uses_transcriptions_api():
                with path.open("rb") as audio_file:
                    response = self._client.audio.transcriptions.create(
                        model=self._settings.transcription_model_name,
                        file=audio_file,
                        prompt=self._build_transcription_prompt(),
                        language=None,
                    )
            else:
                audio_format = path.suffix.lower().lstrip(".") or "wav"
                response = self._client.chat.completions.create(
                    model=self._settings.transcription_model_name,
                    reasoning_effort=self._settings.transcription_reasoning,
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
                                        "data": base64.b64encode(audio_bytes).decode(
                                            "ascii"
                                        ),
                                        "format": audio_format,
                                    },
                                },
                            ],
                        },
                    ],
                )
        except Exception as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "Transcription request failed after %.1f ms [model=%s reasoning=%s]",
                _elapsed_ms(started_at),
                self._settings.transcription_model_name,
                self._settings.transcription_reasoning,
            )
            raise ProviderError(f"Transcription request failed: {exc}") from exc

        if self._uses_transcriptions_api():
            text = getattr(response, "text", "")
        else:
            text = _extract_text_content(response.choices[0].message.content)
        if not text:
            raise ProviderError("Transcription response was empty.")
        logger.info(
            "Transcription completed in %.1f ms [model=%s reasoning=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.transcription_model_name,
            self._settings.transcription_reasoning,
            _preview_text(text),
        )
        return text.strip()

    def _uses_transcriptions_api(self) -> bool:
        return self._settings.transcription_model_name.startswith("whisper")

    @staticmethod
    def _build_transcription_prompt() -> str:
        return (
            "You are an automatic speech recognition model. Transcribe the user's spoken audio "
            "faithfully and return only the transcript text. Do not answer the user, do not "
            "summarize, do not explain, and do not add extra commentary. Preserve the original "
            "language. If a short segment is partly unclear, use the surrounding context to infer "
            "the most likely intended wording when the inference is high confidence; otherwise "
            "stay conservative rather than inventing content."
        )


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
            raise ProviderError("The 'openai' package is required for TTS access.")
        if not api_key:
            raise ProviderError("Missing TTS API key.")
        return OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"Accept-Encoding": "identity"},
        )

    def synthesize(self, text: str, output_path: Path) -> str:
        started_at = perf_counter()
        try:
            response = self._client.audio.speech.create(
                model=self._settings.tts_model,
                voice=self._settings.tts_voice_id,
                input=text,
            )
            response.stream_to_file(output_path)
        except Exception as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "TTS request failed after %.1f ms [model=%s voice=%s]",
                _elapsed_ms(started_at),
                self._settings.tts_model,
                self._settings.tts_voice_id,
            )
            raise ProviderError(f"TTS request failed: {exc}") from exc
        logger.info(
            "Speech synthesis completed in %.1f ms [model=%s voice=%s input=%s]",
            _elapsed_ms(started_at),
            self._settings.tts_model,
            self._settings.tts_voice_id,
            _preview_text(text),
        )
        return str(output_path)


def _file_to_data_url(file_path: Path) -> str:
    if not file_path.exists():
        raise ProviderError(f"Image file does not exist: {file_path}")
    mime_type, _ = mimetypes.guess_type(file_path.name)
    mime_type = mime_type or "application/octet-stream"
    payload = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


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


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 1)


def _preview_text(text: str, *, limit: int = 320) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return "." * limit
    return normalized[: limit - 3].rstrip() + "..."
