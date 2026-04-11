from __future__ import annotations

from pathlib import Path


ENV_KEY_MAP = {
    "GLANCE_LLM_BASE_URL": "llm_base_url",
    "GLANCE_LLM_API_KEY": "llm_api_key",
    "GLANCE_LLM_MODEL": "llm_model_name",
    "GLANCE_LLM_REASONING": "llm_reasoning",
    "GLANCE_TTS_BASE_URL": "tts_base_url",
    "GLANCE_TTS_API_KEY": "tts_api_key",
    "GLANCE_TTS_MODEL": "tts_model",
    "GLANCE_TTS_VOICE": "tts_voice_id",
    "GLANCE_FALLBACK_LANGUAGE": "fallback_language",
    "GLANCE_HISTORY_LENGTH": "history_length",
    "GLANCE_SCREENSHOT_INTERVAL": "screenshot_interval",
    "GLANCE_SCREEN_CHANGE_THRESHOLD": "screen_change_threshold",
    "GLANCE_BATCH_WINDOW_DURATION": "batch_window_duration",
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
