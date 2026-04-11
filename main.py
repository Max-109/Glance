from src.core.orchestrator import build_orchestrator
from src.ui.console_ui import ConsoleUI


def main() -> None:
    orchestrator = build_orchestrator()
    ConsoleUI(orchestrator).run()


if __name__ == "__main__":
    main()
