from __future__ import annotations

from time import time_ns
from typing import Any


RUNTIME_BLINK_INTERVAL_MS = {
    "listening": 420,
    "transcribing": 560,
    "generating": 560,
    "speaking": 420,
}


def default_runtime_status() -> dict[str, Any]:
    return {
        "runtimeState": "idle",
        "runtimeMessage": "Live is idle.",
        "runtimeRevision": 0,
        "runtimePhaseStartedAtMs": 0,
        "runtimeBlinkIntervalMs": 0,
        "runtimeErrorFlashUntilMs": 0,
    }


def coerce_runtime_status(status: dict[str, Any]) -> dict[str, Any]:
    normalized = default_runtime_status()
    normalized["runtimeState"] = str(status.get("runtimeState", "")).strip() or "idle"
    normalized["runtimeMessage"] = (
        str(status.get("runtimeMessage", "")).strip() or "Live is idle."
    )
    for field_name in (
        "runtimeRevision",
        "runtimePhaseStartedAtMs",
        "runtimeBlinkIntervalMs",
        "runtimeErrorFlashUntilMs",
    ):
        try:
            normalized[field_name] = max(0, int(status.get(field_name, 0)))
        except (TypeError, ValueError):
            normalized[field_name] = 0
    return normalized


def normalize_runtime_state(state: str) -> str:
    if state in {"listening", "transcribing", "generating", "speaking", "error"}:
        return state
    if state == "processing":
        return "transcribing"
    return "idle"


def current_epoch_ms() -> int:
    return time_ns() // 1_000_000


def state_blink_interval_ms(state: str) -> int:
    return int(RUNTIME_BLINK_INTERVAL_MS.get(state, 0))


def effective_visual_state(*, base_state: str, error_flash_until_ms: int, now_ms: int) -> str:
    if error_flash_until_ms > now_ms:
        return "error"
    return base_state


def frame_for_phase(*, phase_started_at_ms: int, blink_interval_ms: int, now_ms: int) -> int:
    if blink_interval_ms <= 0 or phase_started_at_ms <= 0:
        return 0
    elapsed_ms = max(0, now_ms - phase_started_at_ms)
    return (elapsed_ms // blink_interval_ms) % 2


def next_visual_update_at_ms(
    *,
    phase_started_at_ms: int,
    blink_interval_ms: int,
    error_flash_until_ms: int,
    now_ms: int | None = None,
) -> int | None:
    resolved_now_ms = current_epoch_ms() if now_ms is None else now_ms
    if error_flash_until_ms > resolved_now_ms:
        return error_flash_until_ms
    if blink_interval_ms <= 0 or phase_started_at_ms <= 0:
        return None
    elapsed_ms = max(0, resolved_now_ms - phase_started_at_ms)
    completed_steps = elapsed_ms // blink_interval_ms
    return phase_started_at_ms + ((completed_steps + 1) * blink_interval_ms)
