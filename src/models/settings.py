from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from src.exceptions.app_exceptions import ValidationError
from src.models.prompt_defaults import (
    DEFAULT_TEXT_REPLY_PROMPT,
    DEFAULT_TRANSCRIPTION_PROMPT,
    DEFAULT_TTS_PREPARATION_PROMPT,
    DEFAULT_VOICE_REPLY_PROMPT,
    normalize_prompt_value,
)
from src.services.keybinds import keybinds_are_unique, normalize_keybind


AUTO_TTS_VOICE_ID = "auto"


@dataclass(frozen=True)
class ElevenV3Voice:
    id: str
    name: str
    title: str
    prompt_summary: str


ELEVEN_V3_VOICES = [
    ElevenV3Voice(
        id="BIvP0GN1cAtSRTxNHnWS",
        name="Ellen",
        title="Serious, Direct and Confident",
        prompt_summary="serious, direct, confident, calm international female voice",
    ),
    ElevenV3Voice(
        id="EkK5I93UQWFDigLMpZcX",
        name="James",
        title="Husky, Engaging and Bold",
        prompt_summary="husky, engaging, bold, slightly husky male voice",
    ),
    ElevenV3Voice(
        id="aMSt68OGf4xUZAnLpTU8",
        name="Juniper",
        title="Grounded and Professional",
        prompt_summary="grounded, professional, steady female professional voice",
    ),
    ElevenV3Voice(
        id="UgBBYS2sOqTuMpoF3BR0",
        name="Mark",
        title="Natural Conversations",
        prompt_summary="natural, conversational, casual young-adult speaking style",
    ),
    ElevenV3Voice(
        id="Z3R5wn05IrDiVCyEkUrK",
        name="Arabella",
        title="Mysterious and Emotive",
        prompt_summary="mysterious, emotive, young mature female narrator",
    ),
    ElevenV3Voice(
        id="RILOU7YmBhvwJGDGjNmP",
        name="Jane",
        title="Professional Audiobook Reader",
        prompt_summary="professional audiobook reader, polished, composed delivery",
    ),
    ElevenV3Voice(
        id="tnSpp4vdxKPjI9w0GnoV",
        name="Hope",
        title="Upbeat and Clear",
        prompt_summary="upbeat, clear, bright and reassuring delivery",
    ),
    ElevenV3Voice(
        id="NNl6r8mD7vthiJatiJt1",
        name="Bradford",
        title="Expressive and Articulate",
        prompt_summary="expressive, articulate, adult British male storyteller",
    ),
]
ELEVEN_V3_VOICE_BY_ID = {voice.id: voice for voice in ELEVEN_V3_VOICES}
ELEVEN_V3_VOICE_NAME_TO_ID = {
    voice.name.lower(): voice.id for voice in ELEVEN_V3_VOICES
}
ELEVEN_V3_VOICE_LABELS = {
    AUTO_TTS_VOICE_ID: "Auto",
    **{voice.id: f"{voice.name} - {voice.title}" for voice in ELEVEN_V3_VOICES},
}
DEFAULT_FIXED_TTS_VOICE = "UgBBYS2sOqTuMpoF3BR0"
DEFAULT_TTS_VOICE = AUTO_TTS_VOICE_ID
TTS_VOICE_OPTIONS = [AUTO_TTS_VOICE_ID, *ELEVEN_V3_VOICE_BY_ID.keys()]
DEFAULT_ACCENT_COLOR = "#a7ffde"
_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-f]{6}$")


@dataclass
class AppSettings:
    live_keybind: str = "CMD+SHIFT+L"
    quick_keybind: str = "CMD+SHIFT+Q"
    ocr_keybind: str = "CMD+SHIFT+O"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model_name: str = "claude-opus-4.6"
    llm_reasoning_enabled: bool = True
    llm_reasoning: str = "low"
    transcription_base_url: str = "https://api.naga.ac/v1"
    transcription_api_key: str = ""
    transcription_model_name: str = "whisper-large-v3-turbo"
    transcription_reasoning_enabled: bool = True
    transcription_reasoning: str = "medium"
    multimodal_live_enabled: bool = False
    tts_base_url: str = "https://api.naga.ac/v1"
    tts_api_key: str = ""
    tts_model: str = "eleven-v3"
    tts_voice_id: str = DEFAULT_TTS_VOICE
    fallback_language: str = "en"
    history_length: int = 50
    screenshot_interval: float = 1.5
    screen_change_threshold: float = 0.08
    batch_window_duration: float = 4.0
    audio_input_device: str = "default"
    audio_output_device: str = "default"
    audio_activation_threshold: float = 0.02
    audio_silence_seconds: float = 0.5
    audio_max_wait_seconds: float = 15.0
    audio_max_record_seconds: float = 30.0
    audio_preroll_seconds: float = 0.25
    system_prompt_override: str = ""
    text_prompt_override: str = DEFAULT_TEXT_REPLY_PROMPT
    voice_prompt_override: str = DEFAULT_VOICE_REPLY_PROMPT
    voice_polish_prompt_override: str = DEFAULT_TTS_PREPARATION_PROMPT
    transcription_prompt_override: str = DEFAULT_TRANSCRIPTION_PROMPT
    theme_preference: str = "dark"
    accent_color: str = DEFAULT_ACCENT_COLOR

    def validate(self) -> None:
        self.live_keybind = normalize_keybind(self.live_keybind)
        self.quick_keybind = normalize_keybind(self.quick_keybind)
        self.ocr_keybind = normalize_keybind(self.ocr_keybind)
        self.tts_voice_id = normalize_tts_voice_id(self.tts_voice_id)
        if not keybinds_are_unique(
            [self.live_keybind, self.quick_keybind, self.ocr_keybind]
        ):
            raise ValidationError("Each keybind must be unique.")
        if not self.llm_base_url.strip():
            raise ValidationError("llm_base_url cannot be empty.")
        if not self.llm_model_name.strip():
            raise ValidationError("llm_model_name cannot be empty.")
        if not self.transcription_model_name.strip():
            raise ValidationError("transcription_model_name cannot be empty.")
        if not self.tts_base_url.strip():
            raise ValidationError("tts_base_url cannot be empty.")
        if not self.tts_model.strip():
            raise ValidationError("tts_model cannot be empty.")
        if not self.tts_voice_id.strip():
            raise ValidationError("tts_voice_id cannot be empty.")
        if self.llm_reasoning not in {"minimal", "low", "medium", "high"}:
            raise ValidationError(
                "llm_reasoning must be minimal, low, medium, or high."
            )
        if self.transcription_reasoning not in {"minimal", "low", "medium", "high"}:
            raise ValidationError(
                "transcription_reasoning must be minimal, low, medium, or high."
            )
        if not self.fallback_language.strip():
            raise ValidationError("fallback_language cannot be empty.")
        if self.history_length <= 0:
            raise ValidationError("history_length must be positive.")
        if self.screenshot_interval <= 0:
            raise ValidationError("screenshot_interval must be positive.")
        if not 0 < self.screen_change_threshold <= 1:
            raise ValidationError("screen_change_threshold must be between 0 and 1.")
        if self.batch_window_duration <= 0:
            raise ValidationError("batch_window_duration must be positive.")
        if not 0 < self.audio_activation_threshold <= 1:
            raise ValidationError("audio_activation_threshold must be between 0 and 1.")
        if self.audio_silence_seconds <= 0:
            raise ValidationError("audio_silence_seconds must be positive.")
        if self.audio_max_wait_seconds <= 0:
            raise ValidationError("audio_max_wait_seconds must be positive.")
        if self.audio_max_record_seconds <= 0:
            raise ValidationError("audio_max_record_seconds must be positive.")
        if self.audio_preroll_seconds < 0:
            raise ValidationError("audio_preroll_seconds must be zero or positive.")
        if self.theme_preference not in {"dark", "light", "system"}:
            raise ValidationError("theme_preference must be dark, light, or system.")
        self.accent_color = normalize_hex_color(self.accent_color)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: dict, *, validate: bool = True) -> "AppSettings":
        settings = cls(
            live_keybind=normalize_keybind(data.get("live_keybind", cls.live_keybind)),
            quick_keybind=normalize_keybind(
                data.get("quick_keybind", cls.quick_keybind)
            ),
            ocr_keybind=normalize_keybind(data.get("ocr_keybind", cls.ocr_keybind)),
            llm_base_url=data.get("llm_base_url", cls.llm_base_url),
            llm_api_key=data.get("llm_api_key", cls.llm_api_key),
            llm_model_name=data.get("llm_model_name", cls.llm_model_name),
            llm_reasoning_enabled=coerce_bool(
                data.get("llm_reasoning_enabled", cls.llm_reasoning_enabled)
            ),
            llm_reasoning=normalize_llm_reasoning(
                data.get("llm_reasoning", cls.llm_reasoning)
            ),
            transcription_base_url=data.get(
                "transcription_base_url", cls.transcription_base_url
            ),
            transcription_api_key=data.get(
                "transcription_api_key", cls.transcription_api_key
            ),
            transcription_model_name=data.get(
                "transcription_model_name", cls.transcription_model_name
            ),
            transcription_reasoning_enabled=coerce_bool(
                data.get(
                    "transcription_reasoning_enabled",
                    cls.transcription_reasoning_enabled,
                )
            ),
            transcription_reasoning=normalize_llm_reasoning(
                data.get("transcription_reasoning", cls.transcription_reasoning)
            ),
            multimodal_live_enabled=coerce_bool(
                data.get("multimodal_live_enabled", cls.multimodal_live_enabled)
            ),
            tts_base_url=data.get("tts_base_url", cls.tts_base_url),
            tts_api_key=data.get("tts_api_key", cls.tts_api_key),
            tts_model=data.get("tts_model", cls.tts_model),
            tts_voice_id=normalize_tts_voice_id(
                data.get("tts_voice_id", cls.tts_voice_id)
            ),
            fallback_language=data.get("fallback_language", cls.fallback_language),
            history_length=int(data.get("history_length", cls.history_length)),
            screenshot_interval=float(
                data.get("screenshot_interval", cls.screenshot_interval)
            ),
            screen_change_threshold=float(
                data.get("screen_change_threshold", cls.screen_change_threshold)
            ),
            batch_window_duration=float(
                data.get("batch_window_duration", cls.batch_window_duration)
            ),
            audio_input_device=data.get("audio_input_device", cls.audio_input_device),
            audio_output_device=data.get(
                "audio_output_device", cls.audio_output_device
            ),
            audio_activation_threshold=float(
                data.get("audio_activation_threshold", cls.audio_activation_threshold)
            ),
            audio_silence_seconds=float(
                data.get("audio_silence_seconds", cls.audio_silence_seconds)
            ),
            audio_max_wait_seconds=float(
                data.get("audio_max_wait_seconds", cls.audio_max_wait_seconds)
            ),
            audio_max_record_seconds=float(
                data.get("audio_max_record_seconds", cls.audio_max_record_seconds)
            ),
            audio_preroll_seconds=float(
                data.get("audio_preroll_seconds", cls.audio_preroll_seconds)
            ),
            system_prompt_override=data.get(
                "system_prompt_override", cls.system_prompt_override
            ),
            text_prompt_override=normalize_prompt_value(
                "text_prompt_override",
                data.get("text_prompt_override", cls.text_prompt_override),
            ),
            voice_prompt_override=normalize_prompt_value(
                "voice_prompt_override",
                data.get("voice_prompt_override", cls.voice_prompt_override),
            ),
            voice_polish_prompt_override=normalize_prompt_value(
                "voice_polish_prompt_override",
                data.get(
                    "voice_polish_prompt_override",
                    cls.voice_polish_prompt_override,
                ),
            ),
            transcription_prompt_override=normalize_prompt_value(
                "transcription_prompt_override",
                data.get(
                    "transcription_prompt_override",
                    cls.transcription_prompt_override,
                ),
            ),
            theme_preference=data.get("theme_preference", cls.theme_preference),
            accent_color=normalize_hex_color(
                data.get("accent_color", cls.accent_color)
            ),
        )
        if validate:
            settings.validate()
        return settings


def normalize_tts_voice_id(value: str) -> str:
    stripped_value = str(value).strip()
    if not stripped_value:
        return DEFAULT_TTS_VOICE

    lowered_value = stripped_value.lower()
    if lowered_value == AUTO_TTS_VOICE_ID:
        return AUTO_TTS_VOICE_ID
    if lowered_value == "alloy":
        return DEFAULT_TTS_VOICE

    if stripped_value in ELEVEN_V3_VOICE_BY_ID:
        return stripped_value
    if lowered_value in ELEVEN_V3_VOICE_NAME_TO_ID:
        return ELEVEN_V3_VOICE_NAME_TO_ID[lowered_value]

    for voice_id, label in ELEVEN_V3_VOICE_LABELS.items():
        if label.lower() == lowered_value:
            return voice_id
    return DEFAULT_TTS_VOICE


def normalize_llm_reasoning(value: str) -> str:
    lowered_value = str(value).strip().lower()
    if lowered_value == "instant":
        return "minimal"
    if lowered_value in {"minimal", "low", "medium", "high"}:
        return lowered_value
    return lowered_value


def coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    lowered_value = str(value).strip().lower()
    if lowered_value in {"1", "true", "yes", "on"}:
        return True
    if lowered_value in {"0", "false", "no", "off", ""}:
        return False
    return bool(value)


def normalize_hex_color(value: object) -> str:
    normalized_value = str(value).strip().lower()
    if not normalized_value:
        return DEFAULT_ACCENT_COLOR
    if not normalized_value.startswith("#"):
        normalized_value = f"#{normalized_value}"
    if not _HEX_COLOR_PATTERN.match(normalized_value):
        raise ValidationError("accent_color must be a valid six-digit hex color.")
    return normalized_value


def get_tts_voice(voice_id: str) -> ElevenV3Voice | None:
    return ELEVEN_V3_VOICE_BY_ID.get(normalize_tts_voice_id(voice_id))


def get_tts_voice_label(voice_id: str) -> str:
    normalized_voice_id = normalize_tts_voice_id(voice_id)
    return ELEVEN_V3_VOICE_LABELS.get(
        normalized_voice_id, ELEVEN_V3_VOICE_LABELS[AUTO_TTS_VOICE_ID]
    )
