from __future__ import annotations

import hashlib
from pathlib import Path

from src.agents.base_agent import BaseAgent


class ScreenDiffAgent(BaseAgent):
    def run(self, *, previous_path: str | None, current_path: str) -> bool:
        if previous_path is None:
            return True
        return self._digest(Path(previous_path)) != self._digest(Path(current_path))

    @staticmethod
    def _digest(file_path: Path) -> str:
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
