from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root_dir: Path
    config_file: Path
    history_file: Path
    audio_dir: Path


def build_app_paths() -> AppPaths:
    root_dir = Path.home() / ".glance"
    audio_dir = root_dir / "audio"
    root_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    return AppPaths(
        root_dir=root_dir,
        config_file=root_dir / "config.json",
        history_file=root_dir / "history.json",
        audio_dir=audio_dir,
    )
