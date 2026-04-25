from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.exceptions.app_exceptions import ValidationError
from src.models.base_entity import BaseEntity


@dataclass
class ToolCallRecord:
    call_id: str
    tool_name: str
    status: str
    arguments_summary: str = ""
    result_preview: str = ""
    error: str = ""
    result_path: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "arguments_summary": self.arguments_summary,
            "result_preview": self.result_preview,
            "error": self.error,
            "result_path": self.result_path,
            "artifact_paths": list(self.artifact_paths),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ToolCallRecord":
        return cls(
            call_id=str(payload.get("call_id", "")),
            tool_name=str(payload.get("tool_name", "")),
            status=str(payload.get("status", "")),
            arguments_summary=str(payload.get("arguments_summary", "")),
            result_preview=str(payload.get("result_preview", "")),
            error=str(payload.get("error", "")),
            result_path=str(payload.get("result_path", "")),
            artifact_paths=[str(path) for path in payload.get("artifact_paths", [])],
            started_at=str(payload.get("started_at", "")),
            finished_at=str(payload.get("finished_at", "")),
        )


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
    tool_calls: list[ToolCallRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.recording_path = self.require_text(self.recording_path, "recording_path")
        self.response = self.require_text(self.response, "response")
        self.tool_calls = [
            record
            if isinstance(record, ToolCallRecord)
            else ToolCallRecord.from_dict(record)
            for record in self.tool_calls
        ]

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
            "tool_calls": [record.to_dict() for record in self.tool_calls],
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
            tool_calls=[
                ToolCallRecord.from_dict(record)
                for record in payload.get("tool_calls", [])
            ],
            **common,
        )
    raise ValidationError(f"Unsupported interaction type: {interaction_type!r}")
