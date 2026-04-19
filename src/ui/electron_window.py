from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot


class ElectronUnavailableError(RuntimeError):
    pass


def find_electron_binary(project_root: Path) -> Path | None:
    candidates = [
        os.environ.get("GLANCE_ELECTRON_BIN"),
        str(project_root / "node_modules" / ".bin" / "electron"),
        shutil.which("electron"),
        "/Applications/Electron.app/Contents/MacOS/Electron",
        str(Path.home() / "Applications" / "Electron.app" / "Contents" / "MacOS" / "Electron"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            return candidate_path
    return None


class ElectronShellController(QObject):
    visibleChanged = Signal()
    _processEventReceived = Signal(object)

    def __init__(
        self,
        *,
        project_root: Path,
        bridge_url: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self._project_root = project_root
        self._bridge_url = bridge_url
        self._logger = logger
        self._entrypoint = project_root / "electron" / "main.js"
        self._electron_binary = find_electron_binary(project_root)
        if not self._entrypoint.exists():
            raise ElectronUnavailableError(
                f"Electron entrypoint is missing: {self._entrypoint}"
            )
        if self._electron_binary is None:
            raise ElectronUnavailableError(
                "No Electron binary was found. Install Electron locally or set GLANCE_ELECTRON_BIN."
            )

        self._visible = False
        self._x = 120
        self._y = 48
        self._width = 924
        self._height = 741
        self._process: subprocess.Popen[str] | None = None
        self._stdin_lock = Lock()
        self._processEventReceived.connect(self._apply_process_event)

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def setX(self, x: int) -> None:
        self._x = int(x)

    def setY(self, y: int) -> None:
        self._y = int(y)

    def setIcon(self, icon: object) -> None:
        del icon

    def isVisible(self) -> bool:
        return self._visible

    def show(self) -> None:
        self._ensure_running()
        self._send_command(
            {
                "type": "show",
                "bounds": self._bounds_payload(),
                "focus": True,
            }
        )

    def hide(self) -> None:
        if self._process is None:
            self._set_visible(False)
            return
        self._send_command({"type": "hide"})

    def raise_(self) -> None:
        if self._process is None:
            return
        self._send_command({"type": "focus"})

    def requestActivate(self) -> None:
        if self._process is None:
            return
        self._send_command({"type": "focus"})

    def close(self) -> None:
        if self._process is None:
            return
        try:
            self._send_command({"type": "terminate"})
            self._process.wait(timeout=2)
        except Exception:
            self._process.kill()
        finally:
            self._process = None
            self._set_visible(False)

    def _ensure_running(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return

        environment = os.environ.copy()
        environment["GLANCE_BRIDGE_URL"] = self._bridge_url
        environment["GLANCE_PROJECT_ROOT"] = str(self._project_root)
        environment["GLANCE_WINDOW_WIDTH"] = str(self._width)
        environment["GLANCE_WINDOW_HEIGHT"] = str(self._height)

        self._logger.info(
            "Launching Electron settings shell: %s %s",
            self._electron_binary,
            self._entrypoint,
        )
        self._process = subprocess.Popen(
            [str(self._electron_binary), str(self._entrypoint)],
            cwd=self._project_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=environment,
        )
        Thread(
            target=self._read_stdout,
            name="glance-electron-stdout",
            daemon=True,
        ).start()
        Thread(
            target=self._read_stderr,
            name="glance-electron-stderr",
            daemon=True,
        ).start()

    def _read_stdout(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                self._logger.info("[electron] %s", line)
                continue
            self._processEventReceived.emit(payload)

        self._processEventReceived.emit({"type": "closed"})

    def _read_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        for raw_line in process.stderr:
            line = raw_line.strip()
            if line:
                self._logger.warning("[electron] %s", line)

    def _send_command(self, payload: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            return
        with self._stdin_lock:
            process.stdin.write(json.dumps(payload) + "\n")
            process.stdin.flush()

    def _bounds_payload(self) -> dict[str, int]:
        return {
            "x": self._x,
            "y": self._y,
            "width": self._width,
            "height": self._height,
        }

    def _set_visible(self, visible: bool) -> None:
        if self._visible == visible:
            return
        self._visible = visible
        self.visibleChanged.emit()

    @Slot(object)
    def _apply_process_event(self, payload: object) -> None:
        event = dict(payload)
        event_type = str(event.get("type", "")).strip()
        if event_type == "visible":
            self._set_visible(bool(event.get("visible")))
            return
        if event_type == "bounds":
            bounds = event.get("bounds", {})
            if isinstance(bounds, dict):
                self._width = int(bounds.get("width", self._width))
                self._height = int(bounds.get("height", self._height))
            return
        if event_type == "ready":
            self._logger.info("Electron settings shell is ready.")
            return
        if event_type == "closed":
            self._process = None
            self._set_visible(False)
            return
        if event_type == "error":
            self._logger.error("Electron shell error: %s", event.get("message", ""))
