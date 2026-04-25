from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.settings import AUTO_TTS_VOICE_ID, DEFAULT_FIXED_TTS_VOICE, AppSettings
from src.services.providers import NagaSpeechProvider
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import JsonSettingsStore
from src.strategies.live_strategy import static_live_speech_file_name
from src.strategies.mode_strategy import force_pause_at_end_for_tts


OCR_CONFIRMATION_TEXT = "Done, I copied it to your clipboard. Anything else?"


def load_settings(config_path: Path) -> AppSettings:
    manager = SettingsManager(store=JsonSettingsStore(config_path))
    return manager.load()


def resolved_voice_id(settings: AppSettings, override: str | None) -> str:
    selected_voice_id = override or settings.tts_voice_id
    if selected_voice_id == AUTO_TTS_VOICE_ID:
        return DEFAULT_FIXED_TTS_VOICE
    return selected_voice_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate reusable static Live speech files, starting with the OCR "
            "clipboard confirmation."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".glance" / "config.json",
        help="Path to the Glance config.json with TTS provider settings.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path.home() / ".glance" / "audio-feedback",
        help="Directory where Live UI sound and static speech WAVs live.",
    )
    parser.add_argument(
        "--voice-id",
        default=None,
        help=(
            "Voice id to generate. Defaults to the configured TTS voice, "
            "resolving auto to Glance's fixed default voice."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate the file even when it already exists.",
    )
    args = parser.parse_args()

    settings = load_settings(args.config)
    if not settings.tts_api_key:
        raise SystemExit("Missing TTS API key in the selected Glance config.")

    voice_id = resolved_voice_id(settings, args.voice_id)
    file_name = static_live_speech_file_name(OCR_CONFIRMATION_TEXT, voice_id)
    if not file_name:
        raise SystemExit("No static speech file name is registered for OCR.")

    args.out.mkdir(parents=True, exist_ok=True)
    output_path = args.out / file_name
    if output_path.exists() and output_path.stat().st_size > 0 and not args.force:
        print(f"skip OCR confirmation: {output_path}")
        return 0

    print(f"record OCR confirmation: {output_path}")
    NagaSpeechProvider(settings).synthesize(
        force_pause_at_end_for_tts(OCR_CONFIRMATION_TEXT),
        output_path=output_path,
        voice_id=voice_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
