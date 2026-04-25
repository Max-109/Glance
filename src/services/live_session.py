from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path
import tempfile
from threading import Event, Lock, Thread, current_thread
from time import perf_counter

from src.core.orchestrator import Orchestrator
from src.exceptions.app_exceptions import GlanceError, ValidationError


logger = logging.getLogger("glance.live")


class LiveSessionController:
    def __init__(
        self,
        orchestrator: Orchestrator | None,
        recorder,
        playback_service,
        *,
        on_status: Callable[[str, str], None] | None = None,
        unavailable_message: str = "",
    ) -> None:
        self._orchestrator = orchestrator
        self._recorder = recorder
        self._playback_service = playback_service
        self._on_status = on_status
        self._state = "idle"
        self._unavailable_message = str(unavailable_message).strip()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._session = None
        self._lock = Lock()

    @property
    def state(self) -> str:
        return self._state

    def set_orchestrator(self, orchestrator: Orchestrator | None) -> None:
        with self._lock:
            self._orchestrator = orchestrator

    def set_recorder(self, recorder, unavailable_message: str = "") -> None:
        with self._lock:
            self._recorder = recorder
            self._unavailable_message = str(unavailable_message).strip()

    def set_output_device(self, output_device_id: str) -> None:
        with self._lock:
            set_output_device = getattr(
                self._playback_service,
                "set_output_device_id",
                None,
            )
            if callable(set_output_device):
                set_output_device(output_device_id)

    def set_status_callback(self, callback: Callable[[str, str], None] | None) -> None:
        self._on_status = callback

    def toggle(self) -> None:
        if self._thread and self._thread.is_alive():
            self.stop()
            return
        self.start()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if self._orchestrator is None:
            self._set_status(
                "idle",
                "Finish setting up your providers to use Live.",
            )
            return
        if self._recorder is None:
            self._set_status(
                "idle",
                self._unavailable_message
                or "Live can't start with the current audio settings.",
            )
            return
        self._stop_event.clear()
        self._session = self._orchestrator.open_session("live")
        logger.info("Starting live session")
        self._thread = Thread(
            target=self._run_loop, name="glance-live-session", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        logger.info("Stopping live session")
        self._stop_event.set()
        self._playback_service.stop()
        thread = self._thread
        if thread and thread.is_alive() and thread is not current_thread():
            thread.join(timeout=1.5)
        self._session = None
        self._set_status("idle", "Live stopped.")

    def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                temp_file = tempfile.NamedTemporaryFile(
                    prefix="glance-live-input-",
                    suffix=".wav",
                    delete=False,
                )
                temp_file.close()
                recording_temp_path = Path(temp_file.name)
                turn_started_at = perf_counter()
                capture_elapsed_ms = 0.0
                pipeline_elapsed_ms = 0.0
                playback_elapsed_ms = 0.0
                self._set_status("listening", "Listening...")
                capture_started_at = perf_counter()
                try:
                    self._recorder.capture_turn(
                        temp_file.name,
                        stop_event=self._stop_event,
                    )
                except ValidationError as exc:
                    _cleanup_temp_file(recording_temp_path)
                    if self._stop_event.is_set():
                        break
                    if str(exc) == "No speech was detected.":
                        logger.info("No speech detected before wait timeout; going idle")
                        self._set_status("idle", "No speech detected. Live is idle.")
                        break
                    self._set_status("idle", str(exc))
                    break

                capture_elapsed_ms = _elapsed_ms(capture_started_at)

                if self._stop_event.is_set():
                    _cleanup_temp_file(recording_temp_path)
                    break

                pipeline_started_at = perf_counter()
                try:
                    interaction = self._orchestrator.run_mode(
                        "live",
                        session=self._session,
                        recording_path=temp_file.name,
                        status_callback=self._set_status,
                        announce_audio_callback=self._play_inline_notice,
                    )
                except GlanceError as exc:
                    _cleanup_temp_file(recording_temp_path)
                    logger.exception("Live mode failed")
                    self._set_status("idle", f"Live failed: {exc}")
                    break

                pipeline_elapsed_ms = _elapsed_ms(pipeline_started_at)

                if self._stop_event.is_set():
                    break

                self._set_status("speaking", "Speaking...")
                playback_started_at = perf_counter()
                try:
                    self._playback_service.play_blocking(
                        interaction.speech_path,
                        stop_event=self._stop_event,
                    )
                except GlanceError as exc:
                    logger.exception("Playback failed")
                    self._set_status("idle", f"Playback failed: {exc}")
                    break
                except (
                    Exception
                ) as exc:  # pragma: no cover - defensive runtime logging.
                    logger.exception("Unexpected playback failure")
                    self._set_status("idle", f"Playback failed: {exc}")
                    break

                playback_elapsed_ms = _elapsed_ms(playback_started_at)
                logger.info(
                    "live turn completed\ncapture    %.1f ms\npipeline   %.1f ms\nplayback   %.1f ms\ntotal      %.1f ms",
                    capture_elapsed_ms,
                    pipeline_elapsed_ms,
                    playback_elapsed_ms,
                    _elapsed_ms(turn_started_at),
                )
        except Exception as exc:  # pragma: no cover - defensive runtime logging.
            logger.exception("Unexpected live session failure")
            self._set_status("idle", f"Live failed: {exc}")
        finally:
            self._stop_event.set()
            self._thread = None
            self._session = None
            if self._state != "idle":
                self._set_status("idle", "Live is idle.")

    def _set_status(self, state: str, message: str) -> None:
        self._state = state
        if self._on_status is not None:
            self._on_status(state, message)

    def _play_inline_notice(self, audio_path: str) -> None:
        if self._stop_event.is_set():
            return
        try:
            self._playback_service.play_blocking(
                audio_path,
                stop_event=self._stop_event,
            )
        except GlanceError:
            raise


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 1)


def _cleanup_temp_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
