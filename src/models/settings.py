from __future__ import annotations

from dataclasses import asdict, dataclass

from src.exceptions.app_exceptions import ValidationError


@dataclass
class AppSettings:
    live_keybind: str = "cmd+shift+l"
    quick_keybind: str = "cmd+shift+q"
    ocr_keybind: str = "cmd+shift+o"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model_name: str = "claude-opus-4.6"
    llm_reasoning: str = "medium"
    tts_base_url: str = "https://api.naga.ac/v1"
    tts_api_key: str = ""
    tts_model: str = "eleven-v3"
    tts_voice_id: str = "alloy"
    fallback_language: str = "en"
    history_length: int = 50
    screenshot_interval: float = 1.5
    screen_change_threshold: float = 0.08
    batch_window_duration: float = 4.0
    audio_input_device: str = "default"
    audio_output_device: str = "default"
    system_prompt_override: str = ""

    def validate(self) -> None:
        if not self.llm_base_url.strip():
            raise ValidationError("llm_base_url cannot be empty.")
        if not self.llm_model_name.strip():
            raise ValidationError("llm_model_name cannot be empty.")
        if not self.tts_base_url.strip():
            raise ValidationError("tts_base_url cannot be empty.")
        if self.history_length <= 0:
            raise ValidationError("history_length must be positive.")
        if self.screenshot_interval <= 0:
            raise ValidationError("screenshot_interval must be positive.")
        if not 0 < self.screen_change_threshold <= 1:
            raise ValidationError("screen_change_threshold must be between 0 and 1.")
        if self.batch_window_duration <= 0:
            raise ValidationError("batch_window_duration must be positive.")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: dict) -> "AppSettings":
        settings = cls(
            live_keybind=data.get("live_keybind", cls.live_keybind),
            quick_keybind=data.get("quick_keybind", cls.quick_keybind),
            ocr_keybind=data.get("ocr_keybind", cls.ocr_keybind),
            llm_base_url=data.get("llm_base_url", cls.llm_base_url),
            llm_api_key=data.get("llm_api_key", cls.llm_api_key),
            llm_model_name=data.get("llm_model_name", cls.llm_model_name),
            llm_reasoning=data.get("llm_reasoning", cls.llm_reasoning),
            tts_base_url=data.get("tts_base_url", cls.tts_base_url),
            tts_api_key=data.get("tts_api_key", cls.tts_api_key),
            tts_model=data.get("tts_model", cls.tts_model),
            tts_voice_id=data.get("tts_voice_id", cls.tts_voice_id),
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
            system_prompt_override=data.get(
                "system_prompt_override", cls.system_prompt_override
            ),
        )
        settings.validate()
        return settings
