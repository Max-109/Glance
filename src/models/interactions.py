from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.exceptions.app_exceptions import ValidationError
from src.models.base_entity import BaseEntity


@dataclass
class BaseInteraction(BaseEntity, ABC):
    mode: str = ""

    def __post_init__(self) -> None:
        self.mode = self.require_text(self.mode, "mode").lower()

    @abstractmethod
    def summary(self) -> str:
        """Return a short human-readable summary."""


@dataclass
class QuickInteraction(BaseInteraction):
    question: str = ""
    answer: str = ""
    image_path: str = ""
    speech_path: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.question = self.require_text(self.question, "question")
        self.answer = self.require_text(self.answer, "answer")
        self.image_path = self.require_text(self.image_path, "image_path")

    def summary(self) -> str:
        return f"Quick: {self.question}"

    def to_dict(self) -> dict:
        return {
            "type": "quick",
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "question": self.question,
            "answer": self.answer,
            "image_path": self.image_path,
            "speech_path": self.speech_path,
        }


@dataclass
class OCRInteraction(BaseInteraction):
    image_path: str = ""
    extracted_text: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.image_path = self.require_text(self.image_path, "image_path")
        self.extracted_text = self.require_text(self.extracted_text, "extracted_text")

    def summary(self) -> str:
        return f"OCR: {self.extracted_text[:40]}"

    def to_dict(self) -> dict:
        return {
            "type": "ocr",
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "image_path": self.image_path,
            "extracted_text": self.extracted_text,
        }


@dataclass
class LiveInteraction(BaseInteraction):
    recording_path: str = ""
    transcript: str = ""
    response: str = ""
    frame_paths: list[str] = field(default_factory=list)
    speech_path: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.recording_path = self.require_text(self.recording_path, "recording_path")
        self.transcript = self.require_text(self.transcript, "transcript")
        self.response = self.require_text(self.response, "response")

    def summary(self) -> str:
        return f"Live: {self.transcript[:40]}"

    def to_dict(self) -> dict:
        return {
            "type": "live",
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "recording_path": self.recording_path,
            "transcript": self.transcript,
            "response": self.response,
            "frame_paths": list(self.frame_paths),
            "speech_path": self.speech_path,
        }


@dataclass
class SessionRecord(BaseEntity):
    mode: str = ""
    interactions: list[BaseInteraction] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.mode = self.require_text(self.mode, "mode").lower()

    def add_interaction(self, interaction: BaseInteraction) -> None:
        if interaction.mode != self.mode:
            raise ValidationError(
                f"Interaction mode '{interaction.mode}' does not match session mode '{self.mode}'."
            )
        self.interactions.append(interaction)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "interactions": [
                interaction.to_dict() for interaction in self.interactions
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SessionRecord":
        session = cls(
            entity_id=payload["entity_id"],
            created_at=payload["created_at"],
            mode=payload["mode"],
        )
        for item in payload.get("interactions", []):
            session.add_interaction(interaction_from_dict(item))
        return session


def interaction_from_dict(payload: dict) -> BaseInteraction:
    interaction_type = payload.get("type")
    common = {
        "entity_id": payload["entity_id"],
        "created_at": payload["created_at"],
        "mode": payload["mode"],
    }
    if interaction_type == "quick":
        return QuickInteraction(
            question=payload["question"],
            answer=payload["answer"],
            image_path=payload["image_path"],
            speech_path=payload.get("speech_path", ""),
            **common,
        )
    if interaction_type == "ocr":
        return OCRInteraction(
            image_path=payload["image_path"],
            extracted_text=payload["extracted_text"],
            **common,
        )
    if interaction_type == "live":
        return LiveInteraction(
            recording_path=payload.get("recording_path", payload.get("audio_path", "")),
            transcript=payload["transcript"],
            response=payload["response"],
            frame_paths=list(payload.get("frame_paths", [])),
            speech_path=payload.get("speech_path", ""),
            **common,
        )
    raise ValidationError(f"Unsupported interaction type: {interaction_type!r}")
