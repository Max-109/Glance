import tempfile
import unittest
from pathlib import Path

from src.models.interactions import LiveInteraction, SessionRecord
from src.services.providers import LiveSpeechReply
from src.strategies.live_strategy import LiveStrategy


class FakeTranscriptionAgent:
    def run(self, *, audio_path: str) -> str:
        return f"transcript for {audio_path}"


class FakeLLMAgent:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_live_speech_reply(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> LiveSpeechReply:
        self.calls.append(
            {
                "mode": "live",
                "transcript": transcript,
                "conversation_history": conversation_history or [],
            }
        )
        return LiveSpeechReply(
            voice_id="UgBBYS2sOqTuMpoF3BR0",
            text="[curious] Hello there!",
        )

    def prepare_speech_text(
        self, *, text: str
    ) -> str:  # pragma: no cover - regression guard.
        raise AssertionError("live strategy should not call prepare_speech_text")


class FakeTTSAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def run(self, *, text: str, output_path: str, voice_id: str | None = None) -> str:
        self.calls.append((text, output_path, voice_id))
        return output_path


class LiveStrategyTests(unittest.TestCase):
    def test_execute_uses_single_llm_reply_for_tts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            llm_agent = FakeLLMAgent()
            tts_agent = FakeTTSAgent()
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=llm_agent,
                tts_agent=tts_agent,
                audio_dir=Path(temp_dir),
            )

            interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertEqual(
            llm_agent.calls,
            [
                {
                    "mode": "live",
                    "transcript": "transcript for input.wav",
                    "conversation_history": [],
                }
            ],
        )
        self.assertEqual(
            tts_agent.calls[0][0],
            "[curious] Hello there!...",
        )
        self.assertTrue(tts_agent.calls[0][1].endswith(".wav"))
        self.assertEqual(tts_agent.calls[0][2], "UgBBYS2sOqTuMpoF3BR0")
        self.assertEqual(interaction.response, "[curious] Hello there!")
        self.assertTrue(interaction.speech_path.endswith(".wav"))

    def test_execute_replays_prior_live_turns_into_conversation_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            llm_agent = FakeLLMAgent()
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=llm_agent,
                tts_agent=FakeTTSAgent(),
                audio_dir=Path(temp_dir),
            )
            session = SessionRecord(mode="live")
            session.add_interaction(
                LiveInteraction(
                    mode="live",
                    recording_path="first.wav",
                    transcript="first user turn",
                    response="first assistant reply",
                    speech_path="first-reply.wav",
                )
            )

            strategy.execute({"recording_path": "input.wav", "session": session})

        self.assertEqual(
            llm_agent.calls[0]["conversation_history"],
            [
                {"role": "user", "content": "first user turn"},
                {"role": "assistant", "content": "first assistant reply"},
            ],
        )

    def test_execute_emits_stage_updates_for_transcribe_reply_and_voice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stages: list[tuple[str, str]] = []
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=FakeLLMAgent(),
                tts_agent=FakeTTSAgent(),
                audio_dir=Path(temp_dir),
            )

            strategy.execute(
                {
                    "recording_path": "input.wav",
                    "status_callback": lambda state, message: stages.append(
                        (state, message)
                    ),
                }
            )

        self.assertEqual(
            stages,
            [
                ("transcribing", "Transcribing..."),
                ("generating", "Writing a reply..."),
                ("speaking", "Preparing speech..."),
            ],
        )


if __name__ == "__main__":
    unittest.main()
