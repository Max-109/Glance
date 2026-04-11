from __future__ import annotations

from src.agents.ocr_agent import OCRAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.models.interactions import OCRInteraction
from src.services.clipboard import ClipboardService
from src.strategies.mode_strategy import ModeStrategy


class OCRStrategy(ModeStrategy):
    def __init__(
        self,
        screen_capture_agent: ScreenCaptureAgent,
        ocr_agent: OCRAgent,
        clipboard_service: ClipboardService,
    ) -> None:
        self._screen_capture_agent = screen_capture_agent
        self._ocr_agent = ocr_agent
        self._clipboard_service = clipboard_service

    def execute(self, context: dict) -> OCRInteraction:
        image_path = self._screen_capture_agent.run(image_path=context["image_path"])
        extracted_text = self._ocr_agent.run(image_path=image_path)
        self._clipboard_service.copy_text(extracted_text)
        return OCRInteraction(
            mode="ocr",
            image_path=image_path,
            extracted_text=extracted_text,
        )
