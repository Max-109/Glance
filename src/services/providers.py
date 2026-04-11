from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from src.exceptions.app_exceptions import ProviderError
from src.models.settings import AppSettings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised only without optional dependency.
    OpenAI = None


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
        return OpenAI(base_url=base_url, api_key=api_key)

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
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on external service.
            raise ProviderError("LLM request failed.") from exc

        text = response.choices[0].message.content
        if not text:
            raise ProviderError("LLM response was empty.")
        return text.strip()

    def extract_text(self, image_path: str) -> str:
        prompt = "Extract all visible text exactly as written. Preserve line breaks where useful."
        return self.generate_reply(user_prompt=prompt, image_paths=[image_path])

    def prepare_speech_text(self, text: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self._build_tts_preparation_prompt(),
                    },
                    {"role": "user", "content": text},
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on external service.
            raise ProviderError("Speech text preparation failed.") from exc

        prepared_text = response.choices[0].message.content
        if not prepared_text:
            raise ProviderError("Speech text preparation returned empty output.")
        return prepared_text.strip()

    def _build_system_prompt(self, match_user_language: bool) -> str:
        prompt = self._settings.system_prompt_override.strip() or (
            "You are Glance, a concise desktop assistant. Keep answers brief, clear, useful, "
            "and easy to speak aloud."
        )
        if match_user_language:
            prompt += " Reply in the same language used by the user transcript."
        else:
            prompt += (
                f" Reply in {self._settings.fallback_language} unless the user explicitly asks "
                "for another language."
            )
        return prompt

    @staticmethod
    def _build_tts_preparation_prompt() -> str:
        return (
            "You rewrite assistant text so it sounds natural with Eleven v3 text to speech. "
            "Return only the final speech text. Preserve meaning and do not add facts. Keep it "
            "concise. Expand abbreviations, symbols, dates, times, currencies, shortcuts, URLs, "
            "and other hard-to-speak text into clear spoken forms. Remove markdown, code fences, "
            "tables, bullets when possible, and visual-only formatting. Use natural punctuation "
            "and sentence structure for pacing. Do not use SSML. Use Eleven v3-style audio tags "
            "only when they clearly improve delivery, keep them sparse, and only use vocal tags "
            "such as [whispers], [sighs], [excited], or [curious]. Default to a neutral, helpful "
            "assistant tone without tags unless emotion is clearly helpful."
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
        return OpenAI(base_url=base_url, api_key=api_key)

    def synthesize(self, text: str, output_path: Path) -> str:
        try:
            response = self._client.audio.speech.create(
                model=self._settings.tts_model,
                voice=self._settings.tts_voice_id,
                input=text,
            )
            response.stream_to_file(output_path)
        except Exception as exc:  # pragma: no cover - depends on external service.
            raise ProviderError("TTS request failed.") from exc
        return str(output_path)


def _file_to_data_url(file_path: Path) -> str:
    if not file_path.exists():
        raise ProviderError(f"Image file does not exist: {file_path}")
    mime_type, _ = mimetypes.guess_type(file_path.name)
    mime_type = mime_type or "application/octet-stream"
    payload = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"
