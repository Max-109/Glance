from __future__ import annotations

from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.exceptions.app_exceptions import PermissionDeniedError, ValidationError

try:
    from PIL import ImageGrab
except ImportError:  # pragma: no cover - depends on optional dependency.
    ImageGrab = None


class ScreenCaptureAgent(BaseAgent):
    def run(
        self, *, image_path: str | None = None, output_path: str | None = None
    ) -> str:
        if image_path:
            source = Path(image_path)
            if not source.exists():
                raise ValidationError(f"Image path does not exist: {image_path}")
            return str(source)

        if ImageGrab is None:
            raise PermissionDeniedError(
                "Pillow ImageGrab is unavailable, so direct screen capture cannot run."
            )
        destination = Path(output_path or "screen_capture.png")
        try:
            grab = ImageGrab.grab()
            grab.save(destination)
        except OSError as exc:
            raise PermissionDeniedError(
                "Screen capture failed. Check macOS screen recording permission."
            ) from exc
        return str(destination)
