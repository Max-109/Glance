import unittest

from src.ui.runtime_visual import (
    coerce_runtime_status,
    effective_visual_state,
    frame_for_phase,
    next_visual_update_at_ms,
    normalize_runtime_state,
)


class RuntimeStatusSyncTests(unittest.TestCase):
    def test_coerce_runtime_status_applies_defaults_and_non_negative_numbers(self) -> None:
        status = coerce_runtime_status(
            {
                "runtimeState": " speaking ",
                "runtimeMessage": " Ready ",
                "runtimeRevision": -4,
                "runtimePhaseStartedAtMs": "1500",
                "runtimeBlinkIntervalMs": "420",
                "runtimeErrorFlashUntilMs": None,
            }
        )

        self.assertEqual(
            status,
            {
                "runtimeState": "speaking",
                "runtimeMessage": "Ready",
                "runtimeRevision": 0,
                "runtimePhaseStartedAtMs": 1500,
                "runtimeBlinkIntervalMs": 420,
                "runtimeErrorFlashUntilMs": 0,
            },
        )

    def test_normalize_tray_state_maps_processing_to_transcribing(self) -> None:
        self.assertEqual(normalize_runtime_state("processing"), "transcribing")

    def test_frame_for_phase_uses_shared_phase_start_timestamp(self) -> None:
        self.assertEqual(
            frame_for_phase(
                phase_started_at_ms=1_000,
                blink_interval_ms=420,
                now_ms=1_500,
            ),
            1,
        )

    def test_next_visual_update_waits_for_error_flash_to_finish(self) -> None:
        self.assertEqual(
            next_visual_update_at_ms(
                phase_started_at_ms=1_000,
                blink_interval_ms=420,
                error_flash_until_ms=2_200,
                now_ms=1_050,
            ),
            2_200,
        )

    def test_next_visual_update_snaps_to_next_blink_boundary(self) -> None:
        self.assertEqual(
            next_visual_update_at_ms(
                phase_started_at_ms=1_000,
                blink_interval_ms=420,
                error_flash_until_ms=0,
                now_ms=1_050,
            ),
            1_420,
        )

    def test_effective_visual_state_uses_error_override_until_timeout(self) -> None:
        self.assertEqual(
            effective_visual_state(
                base_state="speaking",
                error_flash_until_ms=2_000,
                now_ms=1_500,
            ),
            "error",
        )
        self.assertEqual(
            effective_visual_state(
                base_state="speaking",
                error_flash_until_ms=2_000,
                now_ms=2_000,
            ),
            "speaking",
        )


if __name__ == "__main__":
    unittest.main()
