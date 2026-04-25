import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import wave

from src.exceptions.app_exceptions import (
    PermissionDeniedError,
    ValidationError,
)
from src.models.settings import AppSettings
from src.services.audio_devices import AudioDeviceService
import src.services.audio_recording as audio_recording
from src.services.audio_recording import TenVadAudioRecorder
from src.services.audio_recording import build_live_audio_recorder
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
    def test_list_input_devices_includes_default_and_named_inputs(
        self,
    ) -> None:
        service = AudioDeviceService(
            input_devices_provider=lambda: [
                {
                    "name": "Built-in Mic",
                    "max_input_channels": 2,
                    "hostapi": 0,
                },
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
            default_output_provider=lambda: FakeOutputDevice(
                "Default", b"default"
            ),
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


class TenVadAudioRecorderTests(unittest.TestCase):
    def test_ten_vad_frame_conversion_uses_int16_at_hop_size(self) -> None:
        frame = TenVadAudioRecorder._to_ten_vad_frame(
            audio_recording.np.array(
                [[0.0], [0.5], [-1.0]], dtype=audio_recording.np.float32
            )
        )

        self.assertEqual(frame.dtype, audio_recording.np.int16)
        self.assertEqual(frame.shape, (3,))
        self.assertEqual(frame.tolist(), [0, 16383, -32767])

    def test_capture_turn_waits_through_short_pause_and_writes_wav(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "audio_endpoint_patience": "fast",
                "audio_max_wait_seconds": 2,
                "audio_max_turn_length_enabled": False,
                "audio_preroll_seconds": 0.0,
            }
        )
        decisions = [
            (0.0, False),
            (0.0, False),
            (0.92, True),
            (0.94, True),
            (0.95, True),
            (0.0, False),
            (0.93, True),
            *[(0.0, False)] * 12,
        ]

        class FakeVad:
            def __init__(self):
                self.frames = []

            def process(self, frame):
                self.frames.append(frame)
                probability, speech = decisions[
                    min(len(self.frames) - 1, len(decisions) - 1)
                ]
                return audio_recording.VadFrameDecision(probability, speech)

        class FakeInputStream:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, chunk_size):
                return (
                    audio_recording.np.full(
                        (chunk_size, 1),
                        0.2,
                        dtype=audio_recording.np.float32,
                    ),
                    False,
                )

        fake_vad = FakeVad()
        fake_sd = SimpleNamespace(
            InputStream=lambda **kwargs: FakeInputStream()
        )
        recorder = TenVadAudioRecorder(
            settings,
            device_service=SimpleNamespace(
                resolve_input_device=lambda device_id: None
            ),
            vad_factory=lambda: fake_vad,
            sample_rate=160,
            hop_size=16,
            speech_confirmation_frames=3,
            preroll_seconds=0.0,
        )

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(audio_recording, "sd", fake_sd),
        ):
            output_path = recorder.capture_turn(
                str(Path(temp_dir) / "turn.wav")
            )

            self.assertTrue(Path(output_path).exists())
            with wave.open(output_path, "rb") as wav_file:
                self.assertEqual(wav_file.getframerate(), 160)
                self.assertEqual(wav_file.getnchannels(), 1)
                self.assertGreater(wav_file.getnframes(), 0)
            self.assertGreaterEqual(len(fake_vad.frames), 10)

    def test_capture_turn_times_out_without_confirmed_speech(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "audio_max_wait_seconds": 1,
            }
        )

        class FakeVad:
            def process(self, frame):
                return audio_recording.VadFrameDecision(0.0, False)

        class FakeInputStream:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, chunk_size):
                return (
                    audio_recording.np.zeros(
                        (chunk_size, 1),
                        dtype=audio_recording.np.float32,
                    ),
                    False,
                )

        fake_sd = SimpleNamespace(
            InputStream=lambda **kwargs: FakeInputStream()
        )
        clock_values = iter([0.0, 0.3, 0.7, 1.2])
        recorder = TenVadAudioRecorder(
            settings,
            device_service=SimpleNamespace(
                resolve_input_device=lambda device_id: None
            ),
            vad_factory=lambda: FakeVad(),
            hop_size=16,
        )

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(audio_recording, "sd", fake_sd),
            patch.object(
                audio_recording,
                "perf_counter",
                side_effect=lambda: next(clock_values),
            ),
        ):
            with self.assertRaises(ValidationError) as error_context:
                recorder.capture_turn(str(Path(temp_dir) / "turn.wav"))

        self.assertEqual(
            str(error_context.exception), "No speech was detected."
        )

    def test_live_recorder_factory_requires_speech_detection(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        with patch.object(
            audio_recording,
            "TenVadEngine",
            side_effect=PermissionDeniedError(
                audio_recording.SPEECH_DETECTION_SETUP_MESSAGE
            ),
        ):
            with self.assertRaises(PermissionDeniedError) as error_context:
                build_live_audio_recorder(settings)

        self.assertEqual(
            str(error_context.exception),
            audio_recording.SPEECH_DETECTION_SETUP_MESSAGE,
        )

    def test_live_recorder_factory_checks_speech_detection_before_capture(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            }
        )

        with patch.object(
            audio_recording,
            "TenVadEngine",
            return_value=object(),
        ) as engine_factory:
            recorder = build_live_audio_recorder(settings)

        engine_factory.assert_called_once_with(hop_size=256, threshold=0.5)
        self.assertIsInstance(recorder, TenVadAudioRecorder)


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

            self.assertEqual(
                set(cue_paths.keys()),
                {
                    "start",
                    "reply_ready",
                    "cancel",
                    "ocr_complete",
                    "quick_ocr_complete",
                },
            )
            self.assertTrue(cue_paths["start"].exists())
            self.assertTrue(cue_paths["reply_ready"].exists())
            self.assertTrue(cue_paths["cancel"].exists())
            self.assertTrue(cue_paths["ocr_complete"].exists())
            self.assertTrue(cue_paths["quick_ocr_complete"].exists())

            with wave.open(str(cue_paths["start"]), "rb") as start_file:
                self.assertEqual(start_file.getnchannels(), 1)
                self.assertEqual(start_file.getframerate(), 24000)
                self.assertGreater(start_file.getnframes(), 0)

            with wave.open(
                str(cue_paths["reply_ready"]), "rb"
            ) as reply_ready_file:
                self.assertEqual(reply_ready_file.getnchannels(), 1)
                self.assertEqual(reply_ready_file.getframerate(), 24000)
                self.assertGreater(reply_ready_file.getnframes(), 0)

            with wave.open(str(cue_paths["cancel"]), "rb") as cancel_file:
                self.assertEqual(cancel_file.getnchannels(), 1)
                self.assertEqual(cancel_file.getframerate(), 24000)
                self.assertGreater(cancel_file.getnframes(), 0)

            with wave.open(str(cue_paths["ocr_complete"]), "rb") as ocr_file:
                self.assertEqual(ocr_file.getnchannels(), 1)
                self.assertEqual(ocr_file.getframerate(), 24000)
                self.assertGreater(ocr_file.getnframes(), 0)

            with wave.open(
                str(cue_paths["quick_ocr_complete"]), "rb"
            ) as quick_ocr_file:
                self.assertEqual(quick_ocr_file.getnchannels(), 1)
                self.assertEqual(quick_ocr_file.getframerate(), 24000)
                self.assertGreater(quick_ocr_file.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
