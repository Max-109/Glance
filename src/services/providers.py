from __future__ import annotations

import base64
import logging
import mimetypes
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
import wave

from src.exceptions.app_exceptions import ProviderError
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
except ImportError:  # pragma: no cover - exercised only without optional dependency.
    OpenAI = None


logger = logging.getLogger("glance.providers")

_PCM_SAMPLE_RATE = 24000
_PCM_CHANNELS = 1
_PCM_SAMPLE_WIDTH_BYTES = 2


@dataclass(frozen=True)
class LiveSpeechReply:
    voice_id: str
    text: str


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
            "LLM reply completed in %.1f ms [model=%s reasoning=%s usage=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.llm_model_name,
            self._settings.llm_reasoning,
            _format_usage(response),
            _preview_text(text),
        )
        return text.strip()

    def generate_live_speech_reply(self, *, transcript: str) -> LiveSpeechReply:
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
        live_reply = self._parse_live_speech_reply(text)
        logger.info(
            "LLM reply completed in %.1f ms [model=%s reasoning=%s usage=%s voice=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.llm_model_name,
            self._settings.llm_reasoning,
            _format_usage(response),
            get_tts_voice_label(live_reply.voice_id),
            _preview_text(live_reply.text),
        )
        return live_reply

    def extract_text(self, image_path: str) -> str:
        prompt = "Extract all visible text exactly as written. Preserve line breaks where useful."
        return self.generate_reply(user_prompt=prompt, image_paths=[image_path])

    def prepare_speech_text(self, text: str) -> LiveSpeechReply:
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
        prepared_reply = self._parse_live_speech_reply(prepared_text)
        logger.info(
            "Speech text preparation completed in %.1f ms [model=%s reasoning=%s usage=%s voice=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.llm_model_name,
            self._settings.llm_reasoning,
            _format_usage(response),
            get_tts_voice_label(prepared_reply.voice_id),
            _preview_text(prepared_reply.text),
        )
        return prepared_reply

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
            "You are Glance, a live desktop voice assistant. The input is the user's spoken "
            "transcript. Your job is to answer the user directly and produce the final spoken text "
            "that will be sent straight to Eleven v3. Respond like a warm, lively, friendly person "
            "in a real back-and-forth conversation. Be genuinely helpful, clear, accurate, happy, "
            "and pleasant to listen to. Match the answer length to the user's request. Keep short "
            "greetings, thanks, acknowledgments, and casual check-ins short and natural, and only "
            "give longer answers when the user is clearly asking for more. Small conversational turns "
            "should usually be one short sentence, or two short sentences at most. Avoid rambling, "
            "avoid repeating the same feeling in multiple ways, and ask at most one follow-up "
            "question unless the user clearly wants a deeper conversation. Make the reply easy to "
            "understand in one listen. Use natural spoken phrasing, not visual writing. Do not use "
            "markdown, code fences, bullets, or visual formatting. Do not explain your process. Do "
            "not rewrite, critique, or correct another assistant message. Do not change speaker "
            "identity or perspective. Do not mention Claude, Anthropic, or being an AI unless the "
            "user explicitly asks. Preserve the intended meaning and do not add facts. This output "
            "is already the final speech text, so shape it for spoken delivery in this same answer. "
            "Actively follow Eleven v3 best practices: use contextually appropriate audio tags, "
            "punctuation, capitalization, ellipses, and text structure to make the result more "
            "expressive and engaging while preserving meaning. Use tags strategically. By default, "
            "place the main tag at the start of the reply. For short replies, use at most one tag "
            "unless a second tag is clearly necessary. Only place a tag mid-sentence when there is a "
            "real emotional shift. Use voice-related tags, non-verbal vocal sounds, accent tags, and "
            "sound-effect tags when they genuinely improve the spoken result. For warm, playful, "
            "sympathetic, excited, reassuring, or emotional replies, include at least one suitable "
            "Eleven-style tag when it improves delivery. For neutral factual replies, tags may stay "
            "sparse. Use them freely when useful, but do not overdo them or make the result chaotic. "
            "Use only square-bracket Eleven-style tags such as [excited], [laughs], [sighs], "
            "[whispers], [curious], [mischievously], [swallows], [strong French accent], or "
            "[applause]. Never use angle-bracket tags like <laugh>, never use emoji, never use "
            "SSML, and never invent non-auditory stage directions. Normalize hard-to-speak text into "
            "spoken forms when helpful, including numbers, dates, times, currencies, phone numbers, "
            "symbols, abbreviations, shortcuts, URLs, percentages, and similar text. Example good "
            "outputs: `[excited] Hey! I'm doing great, thanks for asking!` and `[sighs] I'm really "
            "sorry you're going through that.`"
        )
        override = self._settings.system_prompt_override.strip()
        if override:
            prompt += f" Additional instructions: {override}"
        prompt += (
            " Reply in the same language as the user's spoken request, unless the user explicitly "
            "asks you to use another language. If they ask for another language, answer in that "
            "language immediately in the same reply."
        )
        if self._settings.tts_voice_id == AUTO_TTS_VOICE_ID:
            prompt += (
                " Auto voice selection is active. First choose the single best voice ID from the "
                "allowed list below, based on the emotional shape and style of your answer. Output "
                "the first line exactly as `VOICE_ID: <id>`, then leave one blank line, then output "
                "only the final speech text. Never output any voice ID outside this list. Do not "
                "default to the same upbeat voice for every positive or generic answer. For ordinary "
                "everyday conversation and casual back-and-forth, prefer Mark unless another voice is "
                "clearly a better fit. Choose the voice before composing the final reply."
            )
            for voice in ELEVEN_V3_VOICES:
                prompt += (
                    f" Allowed voice: {voice.id} - {voice.name} - {voice.title} - "
                    f"{voice.prompt_summary}."
                )
        else:
            voice = get_tts_voice(self._settings.tts_voice_id)
            if voice is not None:
                prompt += (
                    f" The active voice is fixed to {voice.name} ({voice.title}). Shape the final "
                    f"speech text so it suits this voice's strengths: {voice.prompt_summary}. Do "
                    "not output a VOICE_ID header when a fixed voice is already selected."
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
                "Auto voice reply was missing a VOICE_ID header; falling back to %s.",
                get_tts_voice_label(DEFAULT_FIXED_TTS_VOICE),
            )
            return LiveSpeechReply(DEFAULT_FIXED_TTS_VOICE, stripped_text)

        parsed_voice_id = match.group(1).strip()
        remaining_text = stripped_text[match.end() :].strip()
        if parsed_voice_id not in {voice.id for voice in ELEVEN_V3_VOICES}:
            logger.warning(
                "Auto voice reply chose unknown voice id %s; falling back to %s.",
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
        prompt = (
            "You are an AI assistant specializing in enhancing dialogue text for Eleven v3 speech "
            "generation. Your primary goal is to prepare final spoken text that sounds expressive, "
            "engaging, and natural while strictly preserving the original meaning and intent of the "
            "reply. Actively apply Eleven v3 best practices. Integrate contextually appropriate "
            "audio tags, punctuation, capitalization, ellipses, and text structure to improve "
            "delivery. Use voice-related tags, non-verbal vocal sounds, accent tags, and sound "
            "effect tags when they genuinely improve the spoken result. For warm, playful, "
            "sympathetic, excited, reassuring, or emotional replies, include at least one suitable "
            "Eleven-style tag when it improves delivery. For neutral factual replies, tags may stay "
            "sparse. Use them strategically and freely when useful, but do not make the output "
            "chaotic or theatrical. Use only square-bracket Eleven-style tags such as [excited], "
            "[laughs], [sighs], [whispers], [curious], [mischievously], [swallows], [strong French "
            "accent], or [applause]. Never use angle-bracket tags like <laugh>, never use emoji, "
            "never use SSML, and never invent non-auditory stage directions. Do not add facts. Do "
            "not answer the text as if it were a new conversation turn. Do not change speaker "
            "identity or perspective. Do not mention Claude, Anthropic, or being an AI unless the "
            "user explicitly asked for that. Normalize hard-to-speak text into spoken forms when "
            "helpful, including numbers, dates, times, currencies, phone numbers, symbols, "
            "abbreviations, shortcuts, URLs, percentages, and similar text. Remove markdown, code "
            "fences, tables, bullets, and other visual-only formatting. Reply only with the final "
            "speech text. Example good outputs: `[excited] Hey! I'm doing great, thanks for asking!` "
            "and `[sighs] I'm really sorry you're going through that.`"
        )
        if self._settings.tts_voice_id == AUTO_TTS_VOICE_ID:
            prompt += (
                " Auto voice selection is active. First choose the single best voice ID from the "
                "allowed list below, based on the emotional shape and style of the reply. Output "
                "the first line exactly as `VOICE_ID: <id>`, then leave one blank line, then output "
                "only the final speech text. Never output any voice ID outside this list."
            )
            for voice in ELEVEN_V3_VOICES:
                prompt += (
                    f" Allowed voice: {voice.id} - {voice.name} - {voice.title} - "
                    f"{voice.prompt_summary}."
                )
        else:
            voice = get_tts_voice(self._settings.tts_voice_id)
            if voice is not None:
                prompt += (
                    f" The active voice is fixed to {voice.name} ({voice.title}). Shape the final "
                    f"speech text so it suits this voice's strengths: {voice.prompt_summary}. Do "
                    "not output a VOICE_ID header when a fixed voice is already selected."
                )
        return prompt


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
            "Transcription completed in %.1f ms [model=%s reasoning=%s usage=%s output=%s]",
            _elapsed_ms(started_at),
            self._settings.transcription_model_name,
            self._settings.transcription_reasoning,
            _format_usage(response),
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
        except Exception as exc:  # pragma: no cover - depends on external service.
            logger.exception(
                "TTS request failed after %.1f ms [model=%s voice=%s]",
                _elapsed_ms(started_at),
                self._settings.tts_model,
                get_tts_voice_label(resolved_voice_id),
            )
            raise ProviderError(f"TTS request failed: {exc}") from exc
        logger.info(
            "Speech synthesis completed in %.1f ms [model=%s voice=%s input=%s]",
            _elapsed_ms(started_at),
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
    normalized_content_type = content_type.lower()
    return normalized_content_type in {
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
        "audio/pcm",
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
    logger.warning(
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
    if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return "mp3"
    return None


def _convert_audio_to_wav(output_path: Path) -> Path | None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        logger.warning(
            "ffmpeg is unavailable, keeping synthesized audio in its original format."
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
        logger.warning("ffmpeg WAV conversion failed for %s: %s", output_path.name, exc)
        try:
            converted_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    output_path.unlink(missing_ok=True)
    converted_path.replace(output_path)
    return output_path


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


def _format_usage(response) -> str:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return "n/a"

    if not isinstance(usage, dict):
        usage = {
            key: value
            for key, value in vars(usage).items()
            if not key.startswith("_") and value is not None
        }

    if not usage:
        return "n/a"

    details: list[str] = []
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
        "cached_tokens",
    ):
        value = usage.get(key)
        if value is not None:
            details.append(f"{key}={value}")

    for key, value in usage.items():
        if key in {
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "reasoning_tokens",
            "cached_tokens",
        }:
            continue
        details.append(f"{key}={value}")

    return ",".join(details) if details else "n/a"
