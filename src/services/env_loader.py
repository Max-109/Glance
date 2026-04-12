from __future__ import annotations

from pathlib import Path


ENV_KEY_MAP = {
    "LLM_BASE_URL": "llm_base_url",
    "LLM_API_KEY": "llm_api_key",
    "LLM_MODEL": "llm_model_name",
    "LLM_REASONING": "llm_reasoning",
    "TRANSCRIPTION_MODEL": "transcription_model_name",
    "TRANSCRIPTION_REASONING": "transcription_reasoning",
    "TTS_BASE_URL": "tts_base_url",
    "TTS_API_KEY": "tts_api_key",
    "TTS_MODEL": "tts_model",
    "TTS_VOICE": "tts_voice_id",
    "FALLBACK_LANGUAGE": "fallback_language",
    "HISTORY_LENGTH": "history_length",
    "SCREENSHOT_INTERVAL": "screenshot_interval",
    "SCREEN_CHANGE_THRESHOLD": "screen_change_threshold",
    "BATCH_WINDOW_DURATION": "batch_window_duration",
}


def load_env_file(file_path: Path) -> dict:
    if not file_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned = value.strip().strip('"').strip("'")
        values[key.strip()] = cleaned
    return values


def translate_env_values(raw_env: dict) -> dict:
    translated: dict[str, str] = {}
    for raw_key, mapped_key in ENV_KEY_MAP.items():
        if raw_key in raw_env:
            translated[mapped_key] = raw_env[raw_key]
    return translated
