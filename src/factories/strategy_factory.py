from __future__ import annotations

from pathlib import Path

from src.agents.audio_capture_agent import AudioCaptureAgent
from src.agents.llm_agent import LLMAgent
from src.agents.ocr_agent import OCRAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.agents.screen_diff_agent import ScreenDiffAgent
from src.agents.tts_agent import TTSAgent
from src.exceptions.app_exceptions import ValidationError
from src.services.clipboard import ClipboardService
from src.strategies.live_strategy import LiveStrategy
from src.strategies.mode_strategy import ModeStrategy
from src.strategies.ocr_strategy import OCRStrategy
from src.strategies.quick_strategy import QuickStrategy


class ModeStrategyFactory:
    def create(
        self,
        *,
        mode: str,
        screen_capture_agent: ScreenCaptureAgent,
        screen_diff_agent: ScreenDiffAgent,
        audio_capture_agent: AudioCaptureAgent,
        llm_agent: LLMAgent,
        ocr_agent: OCRAgent,
        tts_agent: TTSAgent,
        clipboard_service: ClipboardService,
        audio_dir: Path,
    ) -> ModeStrategy:
        normalized_mode = mode.strip().lower()
        if normalized_mode == "quick":
            return QuickStrategy(
                screen_capture_agent=screen_capture_agent,
                llm_agent=llm_agent,
                tts_agent=tts_agent,
                audio_dir=audio_dir,
            )
        if normalized_mode == "ocr":
            return OCRStrategy(
                screen_capture_agent=screen_capture_agent,
                ocr_agent=ocr_agent,
                clipboard_service=clipboard_service,
            )
        if normalized_mode == "live":
            return LiveStrategy(
                screen_capture_agent=screen_capture_agent,
                screen_diff_agent=screen_diff_agent,
                audio_capture_agent=audio_capture_agent,
                llm_agent=llm_agent,
                tts_agent=tts_agent,
                audio_dir=audio_dir,
            )
        raise ValidationError(f"Unsupported mode: {mode!r}")
