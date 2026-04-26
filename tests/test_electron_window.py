import logging
import os
import tempfile
import unittest
from pathlib import Path

from src.ui import electron_window
from src.ui.electron_window import ElectronShellController


class ElectronShellControllerTests(unittest.TestCase):
    def test_quit_requested_event_calls_owner_callback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "electron").mkdir()
            (project_root / "electron" / "main.js").write_text(
                "",
                encoding="utf-8",
            )
            electron_binary = project_root / "electron-bin"
            electron_binary.write_text("", encoding="utf-8")

            previous_binary = os.environ.get("GLANCE_ELECTRON_BIN")
            os.environ["GLANCE_ELECTRON_BIN"] = str(electron_binary)
            quit_requests = []
            try:
                controller = ElectronShellController(
                    project_root=project_root,
                    bridge_url="http://127.0.0.1:8765",
                    bridge_token="secret-token",
                    logger=logging.getLogger("test.electron"),
                    on_quit_requested=lambda: quit_requests.append(True),
                )

                controller._apply_process_event({"type": "quit-requested"})
            finally:
                if previous_binary is None:
                    os.environ.pop("GLANCE_ELECTRON_BIN", None)
                else:
                    os.environ["GLANCE_ELECTRON_BIN"] = previous_binary

        self.assertEqual(quit_requests, [True])

    def test_bridge_token_is_passed_to_electron_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "electron").mkdir()
            (project_root / "electron" / "main.js").write_text(
                "",
                encoding="utf-8",
            )
            electron_binary = project_root / "electron-bin"
            electron_binary.write_text("", encoding="utf-8")

            previous_binary = os.environ.get("GLANCE_ELECTRON_BIN")
            os.environ["GLANCE_ELECTRON_BIN"] = str(electron_binary)
            captured_env = {}

            class FakeProcess:
                stdin = None
                stdout = None
                stderr = None

                def poll(self):
                    return None

            original_popen = electron_window.subprocess.Popen

            def fake_popen(*_args, **kwargs):
                captured_env.update(kwargs["env"])
                return FakeProcess()

            electron_window.subprocess.Popen = fake_popen
            try:
                controller = ElectronShellController(
                    project_root=project_root,
                    bridge_url="http://127.0.0.1:8765",
                    bridge_token="secret-token",
                    logger=logging.getLogger("test.electron"),
                )

                controller._ensure_running()
            finally:
                electron_window.subprocess.Popen = original_popen
                if previous_binary is None:
                    os.environ.pop("GLANCE_ELECTRON_BIN", None)
                else:
                    os.environ["GLANCE_ELECTRON_BIN"] = previous_binary

        self.assertEqual(captured_env["GLANCE_BRIDGE_URL"], "http://127.0.0.1:8765")
        self.assertEqual(captured_env["GLANCE_BRIDGE_TOKEN"], "secret-token")


if __name__ == "__main__":
    unittest.main()
