import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.models.interactions import LiveInteraction, SessionRecord
from src.models.settings import AppSettings
from src.services.providers import LiveSpeechReply
from src.strategies.live_strategy import (
    LiveStrategy,
    ToolNoticeContext,
    compose_tool_notice,
)
from src.tools import ToolCallRequest


class FakeTranscriptionAgent:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, *, audio_path: str) -> str:
        self.calls.append(audio_path)
        return f"transcript for {audio_path}"


class FakePhraseTranscriptionAgent(FakeTranscriptionAgent):
    def __init__(self, transcript: str) -> None:
        super().__init__()
        self.transcript = transcript

    def run(self, *, audio_path: str) -> str:
        self.calls.append(audio_path)
        return self.transcript


class FakeLLMAgent:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_live_speech_reply(
        self,
        *,
        transcript: str,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
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
        raise AssertionError(
            "live strategy should not call prepare_speech_text"
        )


class FakeTTSAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def run(
        self, *, text: str, output_path: str, voice_id: str | None = None
    ) -> str:
        self.calls.append((text, output_path, voice_id))
        return output_path


class FakeToolLLMAgent:
    def __init__(
        self,
        turns: list[SimpleNamespace],
        *,
        prepared_reply_text: str | None = None,
    ) -> None:
        self.turns = list(turns)
        self.tool_payloads: list[list[dict]] = []
        self.message_snapshots: list[list[dict]] = []
        self.audio_paths: list[str] = []
        self.multimodal_turn_count = 0
        self.prepare_inputs: list[str] = []
        self.prepared_reply_text = prepared_reply_text

    def build_live_tool_messages(
        self, *, transcript, conversation_history=None
    ):
        return [
            {"role": "system", "content": "tool system"},
            *list(conversation_history or []),
            {"role": "user", "content": transcript},
        ]

    def build_live_tool_messages_from_audio(
        self, *, audio_path, conversation_history=None
    ):
        self.audio_paths.append(audio_path)
        return [
            {"role": "system", "content": "multimodal tool system"},
            *list(conversation_history or []),
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "listen and use tools"},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": "audio", "format": "wav"},
                    },
                ],
            },
        ]

    def run_tool_turn(self, *, messages, tools, session_id=None):
        self.message_snapshots.append(list(messages))
        self.tool_payloads.append(list(tools))
        return self.turns.pop(0)

    def run_multimodal_tool_turn(self, *, messages, tools, session_id=None):
        self.multimodal_turn_count += 1
        return self.run_tool_turn(
            messages=messages, tools=tools, session_id=session_id
        )

    def prepare_speech_text(self, *, text, session_id=None):
        self.prepare_inputs.append(text)
        return LiveSpeechReply(
            voice_id="UgBBYS2sOqTuMpoF3BR0",
            text=self.prepared_reply_text or f"spoken:{text}",
        )

    def parse_live_speech_reply(self, text):
        return LiveSpeechReply(
            voice_id="UgBBYS2sOqTuMpoF3BR0",
            text=text,
        )

    def generate_live_speech_reply_from_audio(self, **kwargs):
        raise AssertionError("tool mode must use the multimodal tool loop")


class FakeToolScreenCaptureAgent:
    def __init__(self) -> None:
        self.called = False

    def run(self, *, image_path=None, output_path=None):
        self.called = True
        path = Path(output_path or image_path or "capture.png")
        path.write_bytes(b"fake-png")
        return str(path)


class FakeOCRAgent:
    def __init__(self, text: str = "Screen text") -> None:
        self.text = text
        self.image_paths: list[str] = []
        self.instructions: list[str] = []

    def run(self, *, image_path, instruction=""):
        self.image_paths.append(image_path)
        self.instructions.append(instruction)
        return self.text


class FakeClipboardService:
    def __init__(self) -> None:
        self.last_copied_text = ""

    def copy_text(self, text: str) -> None:
        self.last_copied_text = text


def _tool_settings(**overrides) -> AppSettings:
    values = {
        "llm_base_url": "https://api.example.com/v1",
        "llm_model_name": "model-a",
        "tts_base_url": "https://tts.example.com/v1",
        "tools_enabled": True,
    }
    values.update(overrides)
    return AppSettings.from_mapping(values)


def _tool_turn(*, content: str = "", tool_calls=None) -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        tool_calls=list(tool_calls or []),
        assistant_message={
            "role": "assistant",
            "content": content or None,
            "tool_calls": [] if tool_calls else None,
        },
    )


def _tool_call(name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(
        call_id=f"call-{name}", name=name, arguments=arguments
    )


def _notice_call(name: str, arguments: dict) -> ToolCallRequest:
    return ToolCallRequest(
        call_id=f"call-{name}", name=name, arguments=arguments
    )


class LiveStrategyTests(unittest.TestCase):
    def test_execute_uses_single_llm_reply_for_tts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            llm_agent = FakeLLMAgent()
            tts_agent = FakeTTSAgent()
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=llm_agent,
                tts_agent=tts_agent,
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

    def test_execute_replays_prior_live_turns_into_conversation_history(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            llm_agent = FakeLLMAgent()
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=llm_agent,
                tts_agent=FakeTTSAgent(),
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

            strategy.execute(
                {"recording_path": "input.wav", "session": session}
            )

        self.assertEqual(
            llm_agent.calls[0]["conversation_history"],
            [
                {"role": "user", "content": "first user turn"},
                {"role": "assistant", "content": "first assistant reply"},
            ],
        )

    def test_execute_emits_stage_updates_for_transcribe_reply_and_voice(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stages: list[tuple[str, str]] = []
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=FakeLLMAgent(),
                tts_agent=FakeTTSAgent(),
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

    def test_multimodal_tool_uses_audio_screenshot_and_sends_image(
        self,
    ) -> None:
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    tool_calls=[
                        _tool_call(
                            "take_screenshot", {"reason": "inspect code"}
                        )
                    ]
                ),
                _tool_turn(content="The screen shows a Python function."),
            ]
        )
        tts_agent = FakeTTSAgent()
        screen_capture_agent = FakeToolScreenCaptureAgent()
        transcription_agent = FakeTranscriptionAgent()
        notices: list[str] = []
        stages: list[tuple[str, str]] = []
        strategy = LiveStrategy(
            transcription_agent=transcription_agent,
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            screen_capture_agent=screen_capture_agent,
            settings=_tool_settings(multimodal_live_enabled=True),
        )

        interaction = strategy.execute(
            {
                "recording_path": "input.wav",
                "tool_notice_callback": notices.append,
                "status_callback": lambda state, message: stages.append(
                    (state, message)
                ),
            }
        )

        self.assertEqual(interaction.transcript, "")
        self.assertEqual(transcription_agent.calls, [])
        self.assertEqual(llm_agent.audio_paths, ["input.wav"])
        self.assertEqual(llm_agent.multimodal_turn_count, 2)
        self.assertEqual(
            stages[:2],
            [
                ("generating", "Listening and checking..."),
                ("speaking", "I'll take a quick screenshot of your code."),
            ],
        )
        self.assertNotIn(("transcribing", "Transcribing..."), stages)
        self.assertTrue(screen_capture_agent.called)
        self.assertEqual(
            notices, ["I'll take a quick screenshot of your code."]
        )
        self.assertEqual(llm_agent.prepare_inputs, [])
        self.assertEqual(
            interaction.response, "The screen shows a Python function."
        )
        self.assertEqual(interaction.tool_calls[0].status, "success")
        self.assertEqual(
            interaction.tool_calls[0].tool_name, "take_screenshot"
        )
        self.assertEqual(
            tts_agent.calls[0][0],
            "The screen shows a Python function....",
        )
        second_turn_messages = llm_agent.message_snapshots[1]
        self.assertTrue(_messages_include_image(second_turn_messages))

    def test_text_tool_mode_still_transcribes_when_multimodal_is_off(
        self,
    ) -> None:
        llm_agent = FakeToolLLMAgent([_tool_turn(content="No tool needed.")])
        transcription_agent = FakeTranscriptionAgent()
        strategy = LiveStrategy(
            transcription_agent=transcription_agent,
            llm_agent=llm_agent,
            tts_agent=FakeTTSAgent(),
            screen_capture_agent=FakeToolScreenCaptureAgent(),
            settings=_tool_settings(multimodal_live_enabled=False),
        )

        interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertEqual(transcription_agent.calls, ["input.wav"])
        self.assertEqual(llm_agent.audio_paths, [])
        self.assertEqual(interaction.transcript, "transcript for input.wav")
        self.assertEqual(interaction.response, "spoken:No tool needed.")

    def test_tool_mode_uses_original_answer_when_speech_prep_drifts(
        self,
    ) -> None:
        final_answer = (
            "You're working in a text editor. It looks like you're looking "
            "at log files for a python3 main.py script."
        )
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    tool_calls=[
                        _tool_call(
                            "take_screenshot",
                            {"reason": "inspect what the user sees"},
                        )
                    ]
                ),
                _tool_turn(content=final_answer),
            ],
            prepared_reply_text=(
                "[chuckles] You caught me deep in the weeds here. I was "
                "tracking down a stubborn latency spike."
            ),
        )
        tts_agent = FakeTTSAgent()
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            screen_capture_agent=FakeToolScreenCaptureAgent(),
            settings=_tool_settings(),
        )

        interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertEqual(llm_agent.prepare_inputs, [final_answer])
        self.assertEqual(interaction.response, final_answer)
        self.assertEqual(tts_agent.calls[0][0], f"{final_answer}...")

    def test_tool_mode_exposes_only_enabled_tools_to_provider(self) -> None:
        llm_agent = FakeToolLLMAgent([_tool_turn(content="No tool needed.")])
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=FakeTTSAgent(),
            screen_capture_agent=FakeToolScreenCaptureAgent(),
            settings=_tool_settings(
                tool_take_screenshot_policy="deny",
                tool_ocr_policy="deny",
                tool_web_search_policy="allow",
                tool_web_fetch_policy="deny",
            ),
        )

        strategy.execute({"recording_path": "input.wav"})

        tool_names = [
            payload["function"]["name"]
            for payload in llm_agent.tool_payloads[0]
        ]
        self.assertEqual(tool_names, ["web_search", "end_live_session"])

    def test_live_control_tool_is_available_when_runtime_tools_are_off(
        self,
    ) -> None:
        llm_agent = FakeToolLLMAgent([_tool_turn(content="No tool needed.")])
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=FakeTTSAgent(),
            settings=_tool_settings(tools_enabled=False),
        )

        strategy.execute({"recording_path": "input.wav"})

        tool_names = [
            payload["function"]["name"]
            for payload in llm_agent.tool_payloads[0]
        ]
        self.assertEqual(tool_names, ["end_live_session"])

    def test_tool_mode_ocr_tool_captures_extracts_and_copies_screen_text(
        self,
    ) -> None:
        screen_capture_agent = FakeToolScreenCaptureAgent()
        ocr_agent = FakeOCRAgent("Here is the extracted text:\nRead me")
        clipboard_service = FakeClipboardService()
        notices: list[str] = []
        stages: list[tuple[str, str]] = []
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    tool_calls=[
                        _tool_call(
                            "ocr_screen",
                            {
                                "instruction": (
                                    "Extract only the YouTube video headline."
                                ),
                                "reason": "read text",
                            },
                        ),
                    ]),
                _tool_turn(content="This turn should not run."),
            ])
        tts_agent = FakeTTSAgent()
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            screen_capture_agent=screen_capture_agent,
            ocr_agent=ocr_agent,
            clipboard_service=clipboard_service,
            settings=_tool_settings(),
        )

        interaction = strategy.execute(
            {
                "recording_path": "input.wav",
                "tool_notice_callback": notices.append,
                "status_callback": lambda state, message: stages.append(
                    (state, message)
                ),
            }
        )

        self.assertTrue(screen_capture_agent.called)
        self.assertEqual(clipboard_service.last_copied_text, "Read me")
        self.assertEqual(
            ocr_agent.instructions,
            ["Extract only the YouTube video headline."],
        )
        self.assertEqual(len(llm_agent.message_snapshots), 1)
        self.assertEqual(
            llm_agent.prepare_inputs,
            ["Done, I copied it to your clipboard. Anything else?"],
        )
        self.assertEqual(
            tts_agent.calls[0][0],
            "spoken:Done, I copied it to your clipboard. Anything else?...",
        )
        self.assertEqual(notices, [])
        self.assertIn(("idle", "OCR copied text to clipboard."), stages)
        self.assertEqual(interaction.tool_calls[0].tool_name, "ocr_screen")
        self.assertEqual(interaction.tool_calls[0].status, "success")
        self.assertEqual(
            interaction.response,
            "spoken:Done, I copied it to your clipboard. Anything else?",
        )
        self.assertTrue(interaction.speech_path.endswith(".wav"))

    def test_end_live_session_tool_returns_terminal_live_turn(self) -> None:
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    tool_calls=[
                        _tool_call(
                            "end_live_session",
                            {"reason": "user said no"},
                        )
                    ]
                )
            ]
        )
        tts_agent = FakeTTSAgent()
        stages: list[tuple[str, str]] = []
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            settings=_tool_settings(tools_enabled=False),
        )

        interaction = strategy.execute(
            {
                "recording_path": "input.wav",
                "status_callback": lambda state, message: stages.append(
                    (state, message)
                ),
            }
        )

        self.assertEqual(tts_agent.calls, [])
        self.assertEqual(interaction.response, "Live ended.")
        self.assertEqual(interaction.speech_path, "")
        self.assertEqual(
            interaction.tool_calls[0].tool_name,
            "end_live_session",
        )
        self.assertIn(("idle", "Live ended."), stages)

    def test_thanks_after_ocr_confirmation_ends_without_model_turn(
        self,
    ) -> None:
        llm_agent = FakeToolLLMAgent([])
        tts_agent = FakeTTSAgent()
        session = SessionRecord(mode="live")
        session.add_interaction(
            LiveInteraction(
                mode="live",
                recording_path="ocr.wav",
                transcript="copy the headline",
                response="Done, I copied it to your clipboard. Anything else?",
                speech_path="reply.wav",
            )
        )
        stages: list[tuple[str, str]] = []
        strategy = LiveStrategy(
            transcription_agent=FakePhraseTranscriptionAgent("thank you"),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            settings=_tool_settings(),
        )

        interaction = strategy.execute(
            {
                "recording_path": "thank-you.wav",
                "session": session,
                "status_callback": lambda state, message: stages.append(
                    (state, message)
                ),
            }
        )

        self.assertEqual(llm_agent.message_snapshots, [])
        self.assertEqual(tts_agent.calls, [])
        self.assertEqual(interaction.response, "Live ended.")
        self.assertEqual(interaction.speech_path, "")
        self.assertEqual(interaction.tool_calls[0].tool_name, "end_live_session")
        self.assertIn(("idle", "Live ended."), stages)

    def test_model_closing_reply_after_ocr_confirmation_ends_session(
        self,
    ) -> None:
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    content=(
                        "VOICE_ID: Mark\n\n[smile] No problem at all! Let me "
                        "know if you need anything else, otherwise have a "
                        "great day!"
                    )
                )
            ]
        )
        tts_agent = FakeTTSAgent()
        stages: list[tuple[str, str]] = []
        session = SessionRecord(mode="live")
        session.add_interaction(
            LiveInteraction(
                mode="live",
                recording_path="ocr.wav",
                transcript="copy the headline",
                response="Done, I copied it to your clipboard. Anything else?",
                speech_path="reply.wav",
            )
        )
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            settings=_tool_settings(multimodal_live_enabled=True),
        )

        interaction = strategy.execute(
            {
                "recording_path": "input.wav",
                "session": session,
                "status_callback": lambda state, message: stages.append(
                    (state, message)
                ),
            }
        )

        self.assertEqual(tts_agent.calls, [])
        self.assertEqual(interaction.response, "Live ended.")
        self.assertEqual(interaction.speech_path, "")
        self.assertEqual(interaction.tool_calls[0].tool_name, "end_live_session")
        self.assertIn(("idle", "Live ended."), stages)

    def test_ocr_tool_notice_is_silent(self) -> None:
        notice = compose_tool_notice(
            _notice_call("ocr_screen", {"reason": "read text"}),
            ToolNoticeContext(user_context="extract the text"),
        )

        self.assertEqual(notice, "")

    def test_tool_mode_invalid_arguments_do_not_execute_tool(self) -> None:
        screen_capture_agent = FakeToolScreenCaptureAgent()
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    tool_calls=[
                        _tool_call("take_screenshot", {"unexpected": "value"})
                    ]
                ),
                _tool_turn(
                    content="I cannot inspect the screen from that call."
                ),
            ]
        )
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=FakeTTSAgent(),
            screen_capture_agent=screen_capture_agent,
            settings=_tool_settings(),
        )

        interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertFalse(screen_capture_agent.called)
        self.assertEqual(interaction.tool_calls[0].status, "error")
        self.assertIn("Unexpected argument", interaction.tool_calls[0].error)
        self.assertEqual(
            llm_agent.prepare_inputs,
            ["I cannot inspect the screen from that call."],
        )

    def test_tool_mode_keeps_parallel_tool_results_before_image_followups(
        self,
    ) -> None:
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    tool_calls=[
                        _tool_call(
                            "take_screenshot", {"reason": "inspect code"}
                        ),
                        _tool_call("unknown_tool", {}),
                    ]
                ),
                _tool_turn(content="I used the available context."),
            ]
        )
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=FakeTTSAgent(),
            screen_capture_agent=FakeToolScreenCaptureAgent(),
            settings=_tool_settings(),
        )

        strategy.execute({"recording_path": "input.wav"})

        second_turn_roles = [
            message["role"] for message in llm_agent.message_snapshots[1]
        ]
        self.assertEqual(second_turn_roles[-3:], ["tool", "tool", "user"])

    def test_search_notice_mentions_weather_location(self) -> None:
        notice = compose_tool_notice(
            _notice_call(
                "web_search", {"query": "current weather in Vilnius"}
            ),
            ToolNoticeContext(user_context="what is the weather in Vilnius"),
        )

        self.assertEqual(notice, "I'm checking the weather in Vilnius.")

    def test_repeated_generic_search_notice_is_suppressed(self) -> None:
        context = ToolNoticeContext(user_context="look that up")
        call = _notice_call(
            "web_search", {"query": "what is Gemini 3.1 Flash"}
        )
        next_call = _notice_call("web_search", {"query": "what is Flash Lite"})

        notice = compose_tool_notice(call, context)
        context.mark_spoken(call, notice)

        self.assertEqual(notice, "I'm checking that.")
        self.assertEqual(compose_tool_notice(next_call, context), "")

    def test_open_after_search_mentions_short_source(self) -> None:
        context = ToolNoticeContext()
        context.last_search_results = [
            {
                "title": "Vilnius Weather Forecast",
                "url": "https://weather.com/weather/today/l/Vilnius",
                "site_name": "Weather.com",
            }
        ]

        notice = compose_tool_notice(
            _notice_call(
                "web_fetch",
                {"url": "https://weather.com/weather/today/l/Vilnius"},
            ),
            context,
        )

        self.assertEqual(notice, "I found Weather.com. I'm opening it.")

    def test_open_after_search_uses_result_for_ugly_source(self) -> None:
        context = ToolNoticeContext()
        context.last_search_results = [
            {
                "title": "Weather thing",
                "url": "https://very-long-dashed-source-name.example.com/page",
                "site_name": "Very Long Dashed Source Name",
            }
        ]

        notice = compose_tool_notice(
            _notice_call(
                "web_fetch",
                {
                    "url": (
                        "https://very-long-dashed-source-name.example.com/"
                        "page"
                    )
                },
            ),
            context,
        )

        self.assertEqual(notice, "I found a result. I'm opening it.")

    def test_screenshot_notice_uses_reason(self) -> None:
        cases = [
            ("inspect code", "I'll take a quick screenshot of your code."),
            (
                "read the traceback error",
                "I'll take a quick screenshot of the error.",
            ),
            (
                "look at the screen",
                "I'll take a quick screenshot of your screen.",
            ),
            ("", "I'll take a quick screenshot."),
        ]

        for reason, expected in cases:
            with self.subTest(reason=reason):
                self.assertEqual(
                    compose_tool_notice(
                        _notice_call("take_screenshot", {"reason": reason}),
                        ToolNoticeContext(),
                    ),
                    expected,
                )


def _messages_include_image(messages: list[dict]) -> bool:
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                return True
    return False


if __name__ == "__main__":
    unittest.main()
