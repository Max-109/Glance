from __future__ import annotations

import logging
import wave
from collections import deque
from pathlib import Path
from threading import Event
from time import perf_counter

from src.exceptions.app_exceptions import PermissionDeniedError, ValidationError
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


class ThresholdAudioRecorder:
    def __init__(
        self,
        settings: AppSettings,
        *,
        device_service: AudioDeviceService | None = None,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        activation_threshold: float | None = None,
        silence_seconds: float | None = None,
        max_wait_seconds: float | None = None,
        max_record_seconds: float | None = None,
        preroll_seconds: float | None = None,
    ) -> None:
        self._settings = settings
        self._device_service = device_service or AudioDeviceService()
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        self._activation_threshold = (
            settings.audio_activation_threshold
            if activation_threshold is None
            else activation_threshold
        )
        self._silence_timeout_enabled = True
        self._silence_seconds = (
            settings.audio_silence_seconds
            if silence_seconds is None
            else silence_seconds
        )
        self._max_wait_enabled = settings.audio_wait_for_speech_enabled
        self._max_wait_seconds = (
            settings.audio_max_wait_seconds
            if max_wait_seconds is None
            else max_wait_seconds
        )
        self._max_record_enabled = settings.audio_max_turn_length_enabled
        self._max_record_seconds = (
            settings.audio_max_record_seconds
            if max_record_seconds is None
            else max_record_seconds
        )
        self._preroll_enabled = settings.audio_preroll_enabled
        self._preroll_seconds = (
            settings.audio_preroll_seconds
            if preroll_seconds is None
            else preroll_seconds
        )

    def capture_turn(self, output_path: str, stop_event: Event | None = None) -> str:
        self._ensure_available()
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if stop_event and stop_event.is_set():
            raise ValidationError("Recording stopped before capture began.")

        pre_roll_limit = (
            max(1, int(self._preroll_seconds * self._sample_rate / self._chunk_size))
            if self._preroll_enabled
            else 0
        )
        pre_roll_frames: deque = deque(maxlen=pre_roll_limit)
        frames: list = []
        silence_chunk_limit = (
            max(1, int(self._silence_seconds * self._sample_rate / self._chunk_size))
            if self._silence_timeout_enabled
            else None
        )
        max_record_chunks = (
            max(1, int(self._max_record_seconds * self._sample_rate / self._chunk_size))
            if self._max_record_enabled
            else None
        )
        silence_chunks = 0
        started = False
        wait_started_at = perf_counter()
        overflowed_chunks = 0

        device = self._device_service.resolve_input_device(
            self._settings.audio_input_device
        )

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                blocksize=self._chunk_size,
                device=device,
            ) as stream:
                while True:
                    if stop_event and stop_event.is_set():
                        raise ValidationError("Recording stopped.")

                    block, overflowed = stream.read(self._chunk_size)
                    elapsed_wait = perf_counter() - wait_started_at
                    if overflowed:
                        overflowed_chunks += 1
                        if (
                            not started
                            and self._max_wait_enabled
                            and elapsed_wait >= self._max_wait_seconds
                        ):
                            logger.info(
                                "Live capture wait expired after %.2f s with %d overflowed chunks",
                                elapsed_wait,
                                overflowed_chunks,
                            )
                            raise ValidationError("No speech was detected.")
                        continue

                    level = self._level(block)
                    copied_block = block.copy()

                    if not started:
                        pre_roll_frames.append(copied_block)
                        if level >= self._activation_threshold:
                            started = True
                            frames.extend(pre_roll_frames)
                            silence_chunks = 0
                            continue
                        if (
                            self._max_wait_enabled
                            and elapsed_wait >= self._max_wait_seconds
                        ):
                            logger.info(
                                "Live capture wait expired after %.2f s with %d overflowed chunks",
                                elapsed_wait,
                                overflowed_chunks,
                            )
                            raise ValidationError("No speech was detected.")
                        continue

                    frames.append(copied_block)
                    if level < self._activation_threshold:
                        silence_chunks += 1
                    else:
                        silence_chunks = 0

                    if (
                        silence_chunk_limit is not None
                        and silence_chunks >= silence_chunk_limit
                    ):
                        break
                    if max_record_chunks is not None and len(frames) >= max_record_chunks:
                        break
        except OSError as exc:  # pragma: no cover - depends on device permissions.
            raise PermissionDeniedError(
                "Microphone capture failed. Check microphone permission and device access."
            ) from exc

        if not frames:
            raise ValidationError("No speech was detected.")

        payload = np.concatenate(frames, axis=0)
        payload = np.clip(payload, -1.0, 1.0)
        pcm = (payload * 32767).astype(np.int16)
        with wave.open(str(target_path), "wb") as wav_file:
            wav_file.setnchannels(self._channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(pcm.tobytes())
        return str(target_path)

    def _ensure_available(self) -> None:
        if sd is None or np is None:
            raise PermissionDeniedError(
                "Audio capture requires the 'sounddevice' and 'numpy' packages."
            )

    @staticmethod
    def _level(block) -> float:
        return float(np.sqrt(np.mean(np.square(block))))
