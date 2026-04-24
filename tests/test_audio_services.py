import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import wave

from src.exceptions.app_exceptions import ValidationError
from src.models.settings import AppSettings
from src.services.audio_devices import AudioDeviceService
import src.services.audio_recording as audio_recording
from src.services.audio_recording import ThresholdAudioRecorder
from src.services.audio_signal import AudioTestSignalService


class FakeOutputDevice:
    def __init__(self, description: str, device_id: bytes) -> None:
        self._description = description
        self._device_id = device_id

    def description(self) -> str:
        return self._description

    def id(self) -> bytes:
        return self._device_id


class AudioDeviceServiceTests(unittest.TestCase):
    def test_list_input_devices_includes_default_and_named_inputs(self) -> None:
        service = AudioDeviceService(
            input_devices_provider=lambda: [
                {"name": "Built-in Mic", "max_input_channels": 2, "hostapi": 0},
                {"name": "Speakers", "max_input_channels": 0, "hostapi": 0},
            ],
            host_apis_provider=lambda: [{"name": "Core Audio"}],
        )

        options = service.list_input_devices()

        self.assertEqual(options[0].value, "default")
        self.assertEqual(options[1].value, "input:0")
        self.assertEqual(options[1].label, "Built-in Mic (Core Audio)")

    def test_list_output_devices_uses_friendly_labels(self) -> None:
        service = AudioDeviceService(
            output_devices_provider=lambda: [
                FakeOutputDevice("Studio Display", b"display"),
            ],
            default_output_provider=lambda: FakeOutputDevice("Default", b"default"),
        )

        options = service.list_output_devices()

        self.assertEqual(options[0].label, "System Default Output")
        self.assertEqual(options[1].label, "Studio Display")
        self.assertEqual(options[1].value, "output:646973706c6179")

    def test_resolve_output_device_matches_saved_identifier(self) -> None:
        built_in = FakeOutputDevice("Studio Display", b"display")
        default = FakeOutputDevice("Default", b"default")
        service = AudioDeviceService(
            output_devices_provider=lambda: [built_in],
            default_output_provider=lambda: default,
        )

        device = service.resolve_output_device("output:646973706c6179")

        self.assertIs(device, built_in)
        self.assertIs(service.resolve_output_device("default"), default)


class ThresholdAudioRecorderTests(unittest.TestCase):
    def test_recorder_uses_settings_backed_audio_thresholds(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "audio_activation_threshold": 0.05,
                "audio_silence_timeout_enabled": False,
                "audio_silence_seconds": 1.25,
                "audio_wait_for_speech_enabled": False,
                "audio_max_wait_seconds": 9.5,
                "audio_max_turn_length_enabled": False,
                "audio_max_record_seconds": 18.0,
                "audio_preroll_enabled": False,
                "audio_preroll_seconds": 0.4,
            }
        )

        recorder = ThresholdAudioRecorder(settings)

        self.assertEqual(recorder._activation_threshold, 0.05)
        self.assertTrue(recorder._silence_timeout_enabled)
        self.assertEqual(recorder._silence_seconds, 1.25)
        self.assertFalse(recorder._max_wait_enabled)
        self.assertEqual(recorder._max_wait_seconds, 9.5)
        self.assertFalse(recorder._max_record_enabled)
        self.assertEqual(recorder._max_record_seconds, 18.0)
        self.assertFalse(recorder._preroll_enabled)
        self.assertEqual(recorder._preroll_seconds, 0.4)

    def test_capture_turn_respects_wait_timeout_during_input_overflow(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "audio_max_wait_seconds": 1.5,
            }
        )
        recorder = ThresholdAudioRecorder(
            settings,
            device_service=SimpleNamespace(resolve_input_device=lambda device_id: None),
        )
        recorder._level = lambda block: 0.0

        class FakeBlock:
            def copy(self):
                return self

        class FakeInputStream:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, chunk_size):
                del chunk_size
                return FakeBlock(), True

        fake_sd = SimpleNamespace(InputStream=lambda **kwargs: FakeInputStream())
        clock_values = iter([0.0, 0.6, 1.2, 1.8])

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            audio_recording, "sd", fake_sd
        ), patch.object(audio_recording, "np", object()), patch.object(
            audio_recording,
            "perf_counter",
            side_effect=lambda: next(clock_values),
        ):
            with self.assertRaises(ValidationError) as error_context:
                recorder.capture_turn(str(Path(temp_dir) / "input.wav"))

        self.assertEqual(str(error_context.exception), "No speech was detected.")


class AudioTestSignalServiceTests(unittest.TestCase):
    def test_write_test_tone_creates_non_empty_wav(self) -> None:
        service = AudioTestSignalService()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "speaker-test.wav"

            written_path = service.write_test_tone(output_path)

            self.assertEqual(written_path, output_path)
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 44)

    def test_write_live_mode_cues_creates_all_live_mode_wavs(self) -> None:
        service = AudioTestSignalService()
        with tempfile.TemporaryDirectory() as temp_dir:
            cue_paths = service.write_live_mode_cues(Path(temp_dir))

            self.assertEqual(set(cue_paths.keys()), {"start", "reply_ready", "cancel"})
            self.assertTrue(cue_paths["start"].exists())
            self.assertTrue(cue_paths["reply_ready"].exists())
            self.assertTrue(cue_paths["cancel"].exists())

            with wave.open(str(cue_paths["start"]), "rb") as start_file:
                self.assertEqual(start_file.getnchannels(), 1)
                self.assertEqual(start_file.getframerate(), 24000)
                self.assertGreater(start_file.getnframes(), 0)

            with wave.open(str(cue_paths["reply_ready"]), "rb") as reply_ready_file:
                self.assertEqual(reply_ready_file.getnchannels(), 1)
                self.assertEqual(reply_ready_file.getframerate(), 24000)
                self.assertGreater(reply_ready_file.getnframes(), 0)

            with wave.open(str(cue_paths["cancel"]), "rb") as cancel_file:
                self.assertEqual(cancel_file.getnchannels(), 1)
                self.assertEqual(cancel_file.getframerate(), 24000)
                self.assertGreater(cancel_file.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
