from __future__ import annotations

import sys

from src.core.orchestrator import build_orchestrator
from src.ui.console_ui import ConsoleUI


def main() -> None:
    if "--cli" in sys.argv:
        orchestrator = build_orchestrator()
        ConsoleUI(orchestrator).run()
        return

    try:
        from src.ui.qt_app import run_settings_app
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("PySide6"):
            orchestrator = build_orchestrator()
            ConsoleUI(orchestrator).run()
            return
        raise

    run_settings_app()


if __name__ == "__main__":
    main()
