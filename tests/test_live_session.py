import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.exceptions.app_exceptions import ValidationError
from src.services.live_session import LiveSessionController


class FakeRecorder:
    def capture_turn(self, recording_path: str, stop_event) -> None:
        Path(recording_path).touch()


class SilentRecorder:
    def capture_turn(self, recording_path: str, stop_event) -> None:
        del recording_path, stop_event
        raise ValidationError("No speech was detected.")


class FakeOrchestrator:
    def __init__(self) -> None:
        self.opened_modes: list[str] = []
        self.run_calls: list[dict[str, object]] = []

    def open_session(self, mode: str):
        self.opened_modes.append(mode)
        return {"mode": mode}

    def run_mode(self, mode: str, **context):
        self.run_calls.append({"mode": mode, **context})
        status_callback = context["status_callback"]
        status_callback("transcribing", "Transcribing...")
        status_callback("generating", "Writing a reply...")
        status_callback("speaking", "Preparing speech...")
        return SimpleNamespace(speech_path="reply.wav")


class FakePlaybackService:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.stopped = False

    def play_blocking(self, audio_path: str, stop_event=None) -> str:
        self.calls.append(audio_path)
        if stop_event is not None:
            stop_event.set()
        return audio_path

    def stop(self) -> None:
        self.stopped = True


class LiveSessionControllerTests(unittest.TestCase):
    def test_live_turn_emits_split_runtime_states_before_playback(self) -> None:
        statuses: list[tuple[str, str]] = []
        orchestrator = FakeOrchestrator()
        playback_service = FakePlaybackService()

        with tempfile.TemporaryDirectory() as temp_dir:
            controller = LiveSessionController(
                orchestrator=orchestrator,
                recorder=FakeRecorder(),
                playback_service=playback_service,
                on_status=lambda state, message: statuses.append((state, message)),
            )

            controller.start()

            thread = controller._thread
            if thread is not None:
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())

        self.assertEqual(orchestrator.opened_modes, ["live"])
        self.assertEqual(playback_service.calls, ["reply.wav"])
        self.assertTrue(callable(orchestrator.run_calls[0]["status_callback"]))
        self.assertEqual(
            statuses,
            [
                ("listening", "Listening..."),
                ("transcribing", "Transcribing..."),
                ("generating", "Writing a reply..."),
                ("speaking", "Preparing speech..."),
                ("speaking", "Speaking..."),
                ("idle", "Live is idle."),
            ],
        )

    def test_no_speech_timeout_goes_idle_instead_of_retrying(self) -> None:
        statuses: list[tuple[str, str]] = []
        orchestrator = FakeOrchestrator()
        playback_service = FakePlaybackService()

        with tempfile.TemporaryDirectory() as temp_dir:
            controller = LiveSessionController(
                orchestrator=orchestrator,
                recorder=SilentRecorder(),
                playback_service=playback_service,
                on_status=lambda state, message: statuses.append((state, message)),
            )

            controller.start()

            thread = controller._thread
            if thread is not None:
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())

        self.assertEqual(orchestrator.opened_modes, ["live"])
        self.assertEqual(orchestrator.run_calls, [])
        self.assertEqual(playback_service.calls, [])
        self.assertEqual(
            statuses,
            [
                ("listening", "Listening..."),
                ("idle", "No speech detected. Live is idle."),
            ],
        )

    def test_missing_speech_detector_shows_setup_message(self) -> None:
        statuses: list[tuple[str, str]] = []
        orchestrator = FakeOrchestrator()
        playback_service = FakePlaybackService()
        message = (
            "Speech detection is unavailable. Run `python -m pip install -r "
            "requirements.txt`, then restart Glance."
        )

        controller = LiveSessionController(
            orchestrator=orchestrator,
            recorder=None,
            playback_service=playback_service,
            on_status=lambda state, message: statuses.append((state, message)),
            unavailable_message=message,
        )

        controller.start()

        self.assertIsNone(controller._thread)
        self.assertEqual(orchestrator.opened_modes, [])
        self.assertEqual(playback_service.calls, [])
        self.assertEqual(statuses, [("idle", message)])


if __name__ == "__main__":
    unittest.main()
