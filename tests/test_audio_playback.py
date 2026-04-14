import tempfile
from threading import Event, Lock
import unittest
from pathlib import Path

from src.services import audio_playback


class FakeTimer:
    def __init__(self) -> None:
        self.active = False
        self.started_delays: list[int] = []

    def stop(self) -> None:
        self.active = False

    def start(self, delay_ms: int) -> None:
        self.active = True
        self.started_delays.append(delay_ms)

    def isActive(self) -> bool:
        return self.active


class FakeQMediaPlayer:
    EndOfMedia = object()
    InvalidMedia = object()
    PlayingState = object()
    StoppedState = object()


class FakeQAudio:
    IdleState = object()
    StoppedState = object()
    NoError = object()


class FakeSignal:
    def disconnect(self, *_args, **_kwargs) -> None:
        return None


class FakeAudioSink:
    def __init__(self, *, error=None) -> None:
        self.stateChanged = FakeSignal()
        self._error = error
        self.reset_called = False
        self.stop_called = False

    def error(self):
        return self._error

    def reset(self) -> None:
        self.reset_called = True

    def stop(self) -> None:
        self.stop_called = True

    def deleteLater(self) -> None:
        return None


class FakeAudioBuffer:
    def close(self) -> None:
        return None

    def deleteLater(self) -> None:
        return None


class AudioPlaybackServiceStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_qmedia_player = audio_playback.QMediaPlayer
        self._original_qaudio = audio_playback.QAudio
        self._original_qtimer = audio_playback.QTimer
        audio_playback.QMediaPlayer = FakeQMediaPlayer
        audio_playback.QAudio = FakeQAudio
        audio_playback.QTimer = object()

    def tearDown(self) -> None:
        audio_playback.QMediaPlayer = self._original_qmedia_player
        audio_playback.QAudio = self._original_qaudio
        audio_playback.QTimer = self._original_qtimer

    def test_end_of_media_schedules_finish_using_remaining_duration(self) -> None:
        service = self._make_service()
        service._active_playback_id = 7
        service._playback_started = True
        service._position_ms = 700
        service._duration_ms = 900

        service._on_media_status_changed(FakeQMediaPlayer.EndOfMedia)

        self.assertTrue(service._end_of_media_seen)
        self.assertEqual(service._finish_timer_playback_id, 7)
        self.assertEqual(service._finish_timer_delay_ms, 450)
        self.assertEqual(service._finish_timer.started_delays, [450])

    def test_finish_timer_ignores_stale_playback(self) -> None:
        service = self._make_service()
        completion_event = Event()
        service._active_playback_id = 2
        service._completion_event = completion_event
        service._completion_playback_id = 2
        service._finish_timer_playback_id = 1
        service._end_of_media_seen = True
        service._playback_started = True

        service._on_finish_timer_timeout()

        self.assertFalse(completion_event.is_set())
        self.assertEqual(service._active_playback_id, 2)
        self.assertIs(service._completion_event, completion_event)

    def test_finish_timer_completes_matching_playback(self) -> None:
        service = self._make_service()
        completion_event = Event()
        service._active_playback_id = 4
        service._completion_event = completion_event
        service._completion_playback_id = 4
        service._finish_timer_playback_id = 4
        service._end_of_media_seen = True
        service._playback_started = True

        service._on_finish_timer_timeout()

        self.assertTrue(completion_event.is_set())
        self.assertIsNone(service._active_playback_id)
        self.assertIsNone(service._completion_event)
        self.assertIsNone(service._completion_playback_id)

    def test_invalid_media_finishes_with_error(self) -> None:
        service = self._make_service()
        completion_event = Event()
        service._active_playback_id = 9
        service._completion_event = completion_event
        service._completion_playback_id = 9

        service._on_media_status_changed(FakeQMediaPlayer.InvalidMedia)

        self.assertTrue(completion_event.is_set())
        self.assertEqual(
            service._error_message,
            "Audio playback failed because the media file was invalid.",
        )

    def test_audio_sink_idle_state_drains_then_finishes_wav_playback(self) -> None:
        service = self._make_service()
        completion_event = Event()
        audio_sink = FakeAudioSink(error=FakeQAudio.NoError)
        service._playback_backend = "sink"
        service._active_playback_id = 5
        service._completion_event = completion_event
        service._completion_playback_id = 5
        service._audio_sink = audio_sink
        service._audio_buffer = FakeAudioBuffer()

        service._on_audio_sink_state_changed(FakeQAudio.IdleState)

        self.assertTrue(audio_sink.stop_called)
        self.assertTrue(completion_event.is_set())
        self.assertEqual(service._playback_backend, "")
        self.assertIsNone(service._audio_sink)

    def test_audio_sink_error_finishes_with_error(self) -> None:
        service = self._make_service()
        completion_event = Event()
        service._playback_backend = "sink"
        service._active_playback_id = 6
        service._completion_event = completion_event
        service._completion_playback_id = 6
        service._audio_sink = FakeAudioSink(error="boom")
        service._audio_buffer = FakeAudioBuffer()

        service._on_audio_sink_state_changed(FakeQAudio.StoppedState)

        self.assertTrue(completion_event.is_set())
        self.assertEqual(service._error_message, "WAV audio playback failed.")

    def test_should_use_audio_sink_only_for_real_riff_wave_files(self) -> None:
        service = self._make_service()
        service._wav_playback_available = lambda: True
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "reply.wav"
            fake_wav_path = Path(temp_dir) / "reply-fake.wav"
            wav_path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
            fake_wav_path.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

            self.assertTrue(service._should_use_audio_sink(str(wav_path)))
            self.assertFalse(service._should_use_audio_sink(str(fake_wav_path)))

    @staticmethod
    def _make_service() -> audio_playback.QtAudioPlaybackService:
        service = object.__new__(audio_playback.QtAudioPlaybackService)
        service._lock = Lock()
        service._completion_event = None
        service._completion_playback_id = None
        service._error_message = ""
        service._playback_sequence = 0
        service._active_playback_id = None
        service._playback_started = False
        service._end_of_media_seen = False
        service._stopped_after_playback = False
        service._position_ms = 0
        service._duration_ms = 0
        service._finish_timer_playback_id = None
        service._finish_timer_delay_ms = None
        service._finish_timer = FakeTimer()
        service._player = object()
        service._audio_sink = None
        service._audio_buffer = None
        service._audio_bytes = None
        service._audio_sink_state_connected = False
        service._playback_backend = "media"
        return service


if __name__ == "__main__":
    unittest.main()
