from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root_dir: Path
    config_file: Path
    audio_feedback_dir: Path
    sessions_dir: Path
    memories_file: Path


def build_app_paths() -> AppPaths:
    root_dir = Path.home() / ".glance"
    audio_feedback_dir = root_dir / "audio-feedback"
    sessions_dir = root_dir / "sessions"
    root_dir.mkdir(parents=True, exist_ok=True)
    audio_feedback_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return AppPaths(
        root_dir=root_dir,
        config_file=root_dir / "config.json",
        audio_feedback_dir=audio_feedback_dir,
        sessions_dir=sessions_dir,
        memories_file=root_dir / "memories.json",
    )
