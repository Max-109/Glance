from __future__ import annotations

import math
import wave
from pathlib import Path


class AudioTestSignalService:
    def write_test_tone(
        self,
        output_path: Path,
        *,
        duration_seconds: float = 0.45,
        sample_rate: int = 24000,
        frequency_hz: float = 523.25,
        volume: float = 0.35,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame_count = max(1, int(duration_seconds * sample_rate))
        samples = bytearray()
        for index in range(frame_count):
            envelope = min(index / (sample_rate * 0.03), 1.0)
            tail_index = frame_count - index
            envelope *= min(tail_index / (sample_rate * 0.05), 1.0)
            sample = math.sin(2 * math.pi * frequency_hz * index / sample_rate)
            amplitude = int(sample * volume * envelope * 32767)
            samples.extend(amplitude.to_bytes(2, byteorder="little", signed=True))

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(bytes(samples))
        return output_path
