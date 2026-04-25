from __future__ import annotations

import platform
import subprocess

from src.exceptions.app_exceptions import ProviderError


class ClipboardService:
    def copy_text(self, text: str) -> None:
        system = platform.system().lower()
        try:
            if system == "darwin":
                subprocess.run(
                    ["pbcopy"],
                    input=text,
                    text=True,
                    check=True,
                )
                return
            if system == "windows":
                subprocess.run(
                    ["clip"],
                    input=text,
                    text=True,
                    check=True,
                    shell=True,
                )
                return
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ProviderError(
                "Clipboard copy failed on this platform."
            ) from exc
