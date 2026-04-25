from __future__ import annotations

from collections.abc import Callable
from threading import Event

from src.exceptions.app_exceptions import PermissionDeniedError
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


class AudioMonitorService:
    def __init__(
        self,
        settings: AppSettings,
        *,
        device_service: AudioDeviceService | None = None,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
    ) -> None:
        self._settings = settings
        self._device_service = device_service or AudioDeviceService()
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size

    def monitor_levels(
        self,
        on_level: Callable[[float], None],
        *,
        stop_event: Event | None = None,
    ) -> None:
        self._ensure_available()
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
                while stop_event is None or not stop_event.is_set():
                    block, overflowed = stream.read(self._chunk_size)
                    if overflowed:
                        continue
                    on_level(self._normalized_level(block))
        except (
            OSError
        ) as exc:  # pragma: no cover - depends on device permissions.
            raise PermissionDeniedError(
                "Microphone monitoring failed. Check microphone permission "
                "and device access."
            ) from exc

    def _ensure_available(self) -> None:
        if sd is None or np is None:
            raise PermissionDeniedError(
                "Microphone monitoring requires the 'sounddevice' and 'numpy' "
                "packages."
            )

    @staticmethod
    def _normalized_level(block) -> float:
        level = float(np.sqrt(np.mean(np.square(block))))
        return max(0.0, min(level, 1.0))
