from __future__ import annotations

import logging
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from time import perf_counter
from typing import Any

from src.exceptions.app_exceptions import (
    PermissionDeniedError,
    ValidationError,
)
from src.models.settings import AppSettings
from src.services.audio_devices import AudioDeviceService

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional runtime dependency.
    np = None

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional runtime dependency.
    sd = None


logger = logging.getLogger("glance.audio")
SPEECH_DETECTION_SETUP_MESSAGE = (
    "Speech detection is unavailable. Run `python -m pip install -r "
    "requirements.txt`, then restart Glance."
)


def build_live_audio_recorder(settings: AppSettings):
    TenVadEngine(hop_size=256, threshold=settings.audio_vad_threshold)
    return TenVadAudioRecorder(settings)


@dataclass(frozen=True)
class VadFrameDecision:
    probability: float
    speech: bool


class TenVadEngine:
    def __init__(self, *, hop_size: int, threshold: float) -> None:
        try:
            from ten_vad import TenVad
        except Exception as exc:  # pragma: no cover - optional dependency.
            raise PermissionDeniedError(
                SPEECH_DETECTION_SETUP_MESSAGE
            ) from exc

        try:
            self._vad = TenVad(hop_size, threshold)
        except (
            Exception
        ) as exc:  # pragma: no cover - native library dependent.
            raise PermissionDeniedError(
                SPEECH_DETECTION_SETUP_MESSAGE
            ) from exc

    def process(self, frame) -> VadFrameDecision:
        probability, speech_flag = self._vad.process(frame)
        return VadFrameDecision(float(probability), bool(speech_flag))


class TenVadAudioRecorder:
    _PATIENCE_WINDOWS = {
        "fast": (0.55, 0.95),
        "balanced": (0.9, 1.4),
        "patient": (1.2, 1.8),
    }

    def __init__(
        self,
        settings: AppSettings,
        *,
        device_service: AudioDeviceService | None = None,
        vad_factory=None,
        sample_rate: int = 16000,
        channels: int = 1,
        hop_size: int = 256,
        speech_confirmation_frames: int = 3,
        preroll_seconds: float | None = None,
    ) -> None:
        self._settings = settings
        self._device_service = device_service or AudioDeviceService()
        self._vad_factory = vad_factory or (
            lambda: TenVadEngine(
                hop_size=hop_size,
                threshold=settings.audio_vad_threshold,
            )
        )
        self._sample_rate = sample_rate
        self._channels = channels
        self._hop_size = hop_size
        self._speech_confirmation_frames = max(1, speech_confirmation_frames)
        self._max_wait_enabled = settings.audio_wait_for_speech_enabled
        self._max_wait_seconds = settings.audio_max_wait_seconds
        self._max_record_enabled = settings.audio_max_turn_length_enabled
        self._max_record_seconds = settings.audio_max_record_seconds
        self._preroll_enabled = settings.audio_preroll_enabled
        self._preroll_seconds = (
            max(0.4, settings.audio_preroll_seconds)
            if preroll_seconds is None
            else preroll_seconds
        )
        self._base_endpoint_seconds, self._extended_endpoint_seconds = (
            self._endpoint_windows(settings.audio_endpoint_patience)
        )

    def capture_turn(
        self, output_path: str, stop_event: Event | None = None
    ) -> str:
        self._ensure_available()
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if stop_event and stop_event.is_set():
            raise ValidationError("Recording stopped before capture began.")

        vad = self._vad_factory()
        pre_roll_limit = (
            max(
                1,
                int(
                    self._preroll_seconds * self._sample_rate / self._hop_size
                ),
            )
            if self._preroll_enabled
            else 0
        )
        pre_roll_frames: deque[Any] = deque(maxlen=pre_roll_limit)
        pending_speech_frames: deque[Any] = deque(
            maxlen=self._speech_confirmation_frames
        )
        pending_speech_decisions: deque[VadFrameDecision] = deque(
            maxlen=self._speech_confirmation_frames
        )
        frames: list[Any] = []
        speech_probabilities: list[float] = []
        trailing_silence_frames = 0
        started = False
        wait_started_at = perf_counter()
        overflowed_chunks = 0

        max_record_frames = (
            max(
                1,
                int(
                    self._max_record_seconds
                    * self._sample_rate
                    / self._hop_size
                ),
            )
            if self._max_record_enabled
            else None
        )

        device = self._device_service.resolve_input_device(
            self._settings.audio_input_device
        )

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                blocksize=self._hop_size,
                device=device,
            ) as stream:
                while True:
                    if stop_event and stop_event.is_set():
                        raise ValidationError("Recording stopped.")

                    block, overflowed = stream.read(self._hop_size)
                    elapsed_wait = perf_counter() - wait_started_at
                    if overflowed:
                        overflowed_chunks += 1
                        if (
                            not started
                            and self._max_wait_enabled
                            and elapsed_wait >= self._max_wait_seconds
                        ):
                            logger.info(
                                "Live TEN VAD wait expired after %.2f s with "
                                "%d overflowed chunks",
                                elapsed_wait,
                                overflowed_chunks,
                            )
                            raise ValidationError("No speech was detected.")
                        continue

                    copied_block = block.copy()
                    vad_frame = self._to_ten_vad_frame(copied_block)
                    decision = vad.process(vad_frame)

                    if not started:
                        pre_roll_frames.append(copied_block)
                        if decision.speech:
                            pending_speech_frames.append(copied_block)
                            pending_speech_decisions.append(decision)
                        else:
                            pending_speech_frames.clear()
                            pending_speech_decisions.clear()

                        if (
                            len(pending_speech_frames)
                            >= self._speech_confirmation_frames
                        ):
                            started = True
                            frames.extend(pre_roll_frames)
                            frames.extend(pending_speech_frames)
                            speech_probabilities.extend(
                                item.probability
                                for item in pending_speech_decisions
                            )
                            trailing_silence_frames = 0
                            continue

                        if (
                            self._max_wait_enabled
                            and elapsed_wait >= self._max_wait_seconds
                        ):
                            logger.info(
                                "Live TEN VAD wait expired after %.2f s with "
                                "%d overflowed chunks",
                                elapsed_wait,
                                overflowed_chunks,
                            )
                            raise ValidationError("No speech was detected.")
                        continue

                    frames.append(copied_block)
                    if decision.speech:
                        speech_probabilities.append(decision.probability)
                        trailing_silence_frames = 0
                    else:
                        trailing_silence_frames += 1

                    speech_seconds = (
                        len(frames) * self._hop_size / self._sample_rate
                    )
                    silence_seconds = (
                        trailing_silence_frames
                        * self._hop_size
                        / self._sample_rate
                    )
                    endpoint_seconds = self._endpoint_seconds(
                        speech_seconds,
                        speech_probabilities,
                    )
                    if silence_seconds >= endpoint_seconds:
                        break
                    if (
                        max_record_frames is not None
                        and len(frames) >= max_record_frames
                    ):
                        break
        except (
            OSError
        ) as exc:  # pragma: no cover - depends on device permissions.
            raise PermissionDeniedError(
                "Microphone capture failed. Check microphone permission and "
                "device access."
            ) from exc

        if not frames:
            raise ValidationError("No speech was detected.")

        self._write_wav(target_path, frames)
        return str(target_path)

    def _endpoint_seconds(
        self,
        speech_seconds: float,
        probabilities: list[float],
    ) -> float:
        if speech_seconds < 1.2:
            return self._extended_endpoint_seconds
        if not probabilities:
            return self._extended_endpoint_seconds
        recent_probability = probabilities[-1]
        average_probability = sum(probabilities) / len(probabilities)
        if recent_probability < 0.62 or average_probability < 0.66:
            return self._extended_endpoint_seconds
        return self._base_endpoint_seconds

    def _endpoint_windows(self, patience: str) -> tuple[float, float]:
        return self._PATIENCE_WINDOWS.get(
            patience,
            self._PATIENCE_WINDOWS["balanced"],
        )

    def _ensure_available(self) -> None:
        if sd is None or np is None:
            raise PermissionDeniedError(
                "Audio capture requires the 'sounddevice' and 'numpy' "
                "packages."
            )

    @staticmethod
    def _to_ten_vad_frame(block):
        payload = np.asarray(block, dtype=np.float32).reshape(-1)
        payload = np.clip(payload, -1.0, 1.0)
        return (payload * 32767).astype(np.int16)

    def _write_wav(self, target_path: Path, frames: list[Any]) -> None:
        payload = np.concatenate(frames, axis=0)
        payload = np.clip(payload, -1.0, 1.0)
        pcm = (payload * 32767).astype(np.int16)
        with wave.open(str(target_path), "wb") as wav_file:
            wav_file.setnchannels(self._channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(pcm.tobytes())
