from __future__ import annotations

import math
import wave
from pathlib import Path


ToneStep = tuple[float | None, float, float]


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

        return self._write_wav(output_path, sample_rate=sample_rate, samples=bytes(samples))

    def write_live_mode_cues(self, output_dir: Path) -> dict[str, Path]:
        return {
            "start": self._write_tone_sequence(
                output_dir / "live-start.wav",
                [
                    (659.25, 0.04, 0.16),
                    (None, 0.018, 0.0),
                    (987.77, 0.085, 0.22),
                ],
            ),
            "reply_ready": self._write_tone_sequence(
                output_dir / "live-reply-ready.wav",
                [
                    (783.99, 0.035, 0.14),
                    (1174.66, 0.075, 0.24),
                ],
            ),
            "cancel": self._write_tone_sequence(
                output_dir / "live-cancel.wav",
                [
                    (698.46, 0.034, 0.13),
                    (None, 0.014, 0.0),
                    (523.25, 0.082, 0.18),
                ],
            ),
        }

    def _write_tone_sequence(
        self,
        output_path: Path,
        steps: list[ToneStep],
        *,
        sample_rate: int = 24000,
    ) -> Path:
        samples = bytearray()
        for frequency_hz, duration_seconds, volume in steps:
            frame_count = max(1, int(duration_seconds * sample_rate))
            for index in range(frame_count):
                if frequency_hz is None or volume <= 0:
                    amplitude = 0
                else:
                    envelope = min(index / (sample_rate * 0.006), 1.0)
                    tail_index = frame_count - index
                    envelope *= min(tail_index / (sample_rate * 0.035), 1.0)
                    fundamental = math.sin(
                        2 * math.pi * frequency_hz * index / sample_rate
                    )
                    harmonic = 0.22 * math.sin(
                        2 * math.pi * frequency_hz * 2 * index / sample_rate
                    )
                    sample = (fundamental + harmonic) / 1.22
                    amplitude = int(sample * volume * envelope * 32767)
                samples.extend(amplitude.to_bytes(2, byteorder="little", signed=True))

        return self._write_wav(output_path, sample_rate=sample_rate, samples=bytes(samples))

    def _write_wav(self, output_path: Path, *, sample_rate: int, samples: bytes) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples)
        return output_path
