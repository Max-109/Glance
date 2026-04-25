from __future__ import annotations

import re
from dataclasses import dataclass

from src.agents.ocr_agent import OCRAgent
from src.exceptions.app_exceptions import ProviderError
from src.services.clipboard import ClipboardService


NO_VISIBLE_TEXT_SENTINEL = "[NO_VISIBLE_TEXT]"


@dataclass(frozen=True)
class OCRResult:
    text: str
    image_path: str


class OCRService:
    def __init__(
        self,
        ocr_agent: OCRAgent,
        clipboard_service: ClipboardService,
    ) -> None:
        self._ocr_agent = ocr_agent
        self._clipboard_service = clipboard_service

    def extract_to_clipboard(
        self,
        *,
        image_path: str,
        instruction: str = "",
    ) -> OCRResult:
        normalized_instruction = (
            str(instruction).strip()
            or "Extract all visible text from the image."
        )
        raw_text = self._ocr_agent.run(
            image_path=image_path,
            instruction=normalized_instruction,
        )
        extracted_text = sanitize_ocr_output(raw_text)
        self._clipboard_service.copy_text(extracted_text)
        return OCRResult(text=extracted_text, image_path=image_path)


def sanitize_ocr_output(value: str) -> str:
    text = str(value or "").strip()
    for _ in range(2):
        next_text = _strip_intro_line(_strip_code_fence(text)).strip()
        if next_text == text:
            break
        text = next_text
    text = text.strip()
    if text.upper() == NO_VISIBLE_TEXT_SENTINEL:
        return ""
    return text


def _strip_code_fence(text: str) -> str:
    match = re.fullmatch(
        r"```(?:text|markdown|md)?\s*\n(?P<body>.*?)\n```",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if match is None:
        return text
    return match.group("body")


def _strip_intro_line(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    first_line = lines[0].strip().lower().rstrip(":")
    if first_line in {
        "here is the extracted texthere's the extracted textextracted "
        "textthe extracted text isocr resultocr output",
    }:
        return "\n".join(lines[1:])
    if (
        first_line.startswith("here is ")
        and "text" in first_line
        and len(lines) > 1
    ):
        return "\n".join(lines[1:])
    return text


def require_ocr_text(text: str) -> str:
    cleaned = sanitize_ocr_output(text)
    if not cleaned:
        raise ProviderError("OCR found no visible text.")
    return cleaned
