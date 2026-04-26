from __future__ import annotations

from pathlib import Path

from src.agents.llm_agent import LLMAgent
from src.agents.ocr_agent import OCRAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.agents.tts_agent import TTSAgent
from src.agents.transcription_agent import TranscriptionAgent
from src.exceptions.app_exceptions import ValidationError
from src.models.settings import AppSettings
from src.services.clipboard import ClipboardService
from src.services.memory_manager import MemoryManager
from src.strategies.live_strategy import LiveStrategy
from src.strategies.mode_strategy import ModeStrategy
from src.strategies.ocr_strategy import OCRStrategy


class ModeStrategyFactory:
    def __init__(self, *, static_speech_dir: Path | None = None) -> None:
        self._static_speech_dir = static_speech_dir

    def create(
        self,
        *,
        mode: str,
        screen_capture_agent: ScreenCaptureAgent,
        transcription_agent: TranscriptionAgent,
        llm_agent: LLMAgent,
        ocr_agent: OCRAgent,
        tts_agent: TTSAgent,
        clipboard_service: ClipboardService,
        settings: AppSettings | None = None,
        memory_manager: MemoryManager | None = None,
    ) -> ModeStrategy:
        normalized_mode = mode.strip().lower()
        if normalized_mode == "ocr":
            return OCRStrategy(
                screen_capture_agent=screen_capture_agent,
                ocr_agent=ocr_agent,
                clipboard_service=clipboard_service,
            )
        if normalized_mode == "live":
            return LiveStrategy(
                transcription_agent=transcription_agent,
                llm_agent=llm_agent,
                tts_agent=tts_agent,
                screen_capture_agent=screen_capture_agent,
                ocr_agent=ocr_agent,
                clipboard_service=clipboard_service,
                settings=settings,
                memory_manager=memory_manager,
                static_speech_dir=self._static_speech_dir,
            )
        raise ValidationError(f"Unsupported mode: {mode!r}")
