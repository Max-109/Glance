from __future__ import annotations

from src.exceptions.app_exceptions import GlanceError


class ConsoleUI:
    def __init__(self, orchestrator) -> None:
        self._orchestrator = orchestrator

    def run(self) -> None:
        print("Glance console shell")
        print("1. Quick Ask")
        print("2. Read Screen")
        print("3. Live")
        print("4. View history")
        print("5. Exit")

        while True:
            choice = input("Select an option: ").strip()
            if choice == "1":
                self._run_quick_mode()
            elif choice == "2":
                self._run_ocr_mode()
            elif choice == "3":
                self._run_live_mode()
            elif choice == "4":
                self._show_history()
            elif choice == "5":
                print("Goodbye.")
                return
            else:
                print("Invalid option.")

    def _run_quick_mode(self) -> None:
        image_path = input("Image path: ").strip()
        question = input("Optional question: ").strip()
        try:
            interaction = self._orchestrator.run_mode(
                "quick",
                image_path=image_path,
                question=question,
            )
        except GlanceError as exc:
            print(f"Quick Ask failed: {exc}")
            return
        print(interaction.answer)

    def _run_ocr_mode(self) -> None:
        image_path = input("Image path: ").strip()
        try:
            interaction = self._orchestrator.run_mode("ocr", image_path=image_path)
        except GlanceError as exc:
            print(f"Read Screen failed: {exc}")
            return
        print(interaction.extracted_text)

    def _run_live_mode(self) -> None:
        recording_path = input("Recorded audio path: ").strip()
        try:
            interaction = self._orchestrator.run_mode(
                "live",
                recording_path=recording_path,
            )
        except GlanceError as exc:
            print(f"Live failed: {exc}")
            return
        print(interaction.response)

    def _show_history(self) -> None:
        sessions = self._orchestrator.list_history()
        if not sessions:
            print("No history yet.")
            return
        for session in sessions:
            print(
                f"[{session.mode}] {session.created_at} ({len(session.interactions)} interactions)"
            )
            for interaction in session.interactions:
                print(f"  - {interaction.summary()}")
