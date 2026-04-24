from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.settings import ELEVEN_V3_VOICES, AppSettings
from src.services.providers import NagaSpeechProvider
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import JsonSettingsStore


SAMPLE_TEXT = (
    "Hi, I am {name}. This is the voice Glance will use for spoken replies."
)


def safe_file_part(value: object) -> str:
    safe_value = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in str(value).strip().lower()
    ).strip("-")
    return safe_value or "default"


def load_settings(config_path: Path) -> AppSettings:
    manager = SettingsManager(store=JsonSettingsStore(config_path))
    return manager.load()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate recorded voice preview samples for the Glance settings UI."
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
        default=PROJECT_ROOT / "src" / "assets" / "voice-previews",
        help="Directory where preview WAV files should be written.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate samples even when files already exist.",
    )
    args = parser.parse_args()

    settings = load_settings(args.config)
    args.out.mkdir(parents=True, exist_ok=True)

    if not settings.tts_api_key:
        raise SystemExit("Missing TTS API key in the selected Glance config.")

    provider = NagaSpeechProvider(settings)
    for voice in ELEVEN_V3_VOICES:
        output_path = args.out / f"{safe_file_part(voice.id)}.wav"
        if output_path.exists() and output_path.stat().st_size > 0 and not args.force:
            print(f"skip {voice.name}: {output_path}")
            continue
        print(f"record {voice.name}: {output_path}")
        provider.synthesize(
            SAMPLE_TEXT.format(name=voice.name),
            output_path=output_path,
            voice_id=voice.id,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
