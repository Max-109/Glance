import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.models.interactions import LiveInteraction, SessionRecord
from src.models.settings import AppSettings
from src.services.memory_manager import MemoryManager
from src.services.providers import LiveSpeechReply
from src.strategies import live_strategy as live_strategy_module
from src.strategies.live_strategy import (
    LiveStrategy,
    static_live_speech_file_name,
)


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
        del session_id
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
        del text
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
        self.enabled_tool_name_sets: list[set[str]] = []
        self.audio_paths: list[str] = []
        self.multimodal_turn_count = 0
        self.prepare_inputs: list[str] = []
        self.prepared_reply_text = prepared_reply_text

    def build_live_tool_messages(
        self, *, transcript, conversation_history=None, enabled_tool_names=None
    ):
        self.enabled_tool_name_sets.append(set(enabled_tool_names or set()))
        return [
            {"role": "system", "content": "tool system"},
            *list(conversation_history or []),
            {"role": "user", "content": transcript},
        ]

    def build_live_tool_messages_from_audio(
        self, *, audio_path, conversation_history=None, enabled_tool_names=None
    ):
        self.enabled_tool_name_sets.append(set(enabled_tool_names or set()))
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
        del session_id
        self.message_snapshots.append(list(messages))
        self.tool_payloads.append(list(tools))
        return self.turns.pop(0)

    def run_multimodal_tool_turn(self, *, messages, tools, session_id=None):
        del session_id
        self.multimodal_turn_count += 1
        return self.run_tool_turn(
            messages=messages, tools=tools
        )

    def prepare_speech_text(self, *, text, session_id=None):
        del session_id
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
        del kwargs
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


class LiveStrategyTests(unittest.TestCase):
    def test_execute_uses_single_llm_reply_for_tts(self) -> None:
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

        strategy.execute({"recording_path": "input.wav", "session": session})

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
                    content="Pažiūrėsiu į kodą.",
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
        announced: list[str] = []
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
                "announce_audio_callback": announced.append,
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
                ("speaking", "Pažiūrėsiu į kodą."),
            ],
        )
        self.assertNotIn(("transcribing", "Transcribing..."), stages)
        self.assertTrue(screen_capture_agent.called)
        self.assertEqual(notices, ["Pažiūrėsiu į kodą."])
        self.assertEqual(announced, [tts_agent.calls[0][1]])
        self.assertEqual(llm_agent.prepare_inputs, [])
        self.assertEqual(
            interaction.response, "The screen shows a Python function."
        )
        self.assertEqual(interaction.tool_calls[0].status, "success")
        self.assertEqual(
            interaction.tool_calls[0].tool_name, "take_screenshot"
        )
        self.assertEqual(
            tts_agent.calls[1][0],
            "The screen shows a Python function....",
        )

    def test_tool_progress_uses_model_spoken_english_content(self) -> None:
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    content="I’ll check the screen now.",
                    tool_calls=[
                        _tool_call(
                            "take_screenshot", {"reason": "inspect screen"}
                        )
                    ],
                ),
                _tool_turn(content="I used the screen context."),
            ]
        )
        tts_agent = FakeTTSAgent()
        notices: list[str] = []
        announced: list[str] = []
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            screen_capture_agent=FakeToolScreenCaptureAgent(),
            settings=_tool_settings(),
        )

        strategy.execute(
            {
                "recording_path": "input.wav",
                "tool_notice_callback": notices.append,
                "announce_audio_callback": announced.append,
            }
        )

        self.assertEqual(notices, ["I’ll check the screen now."])
        self.assertEqual(announced, [tts_agent.calls[0][1]])
        self.assertEqual(
            tts_agent.calls[0][0], "I’ll check the screen now...."
        )
        self.assertEqual(
            tts_agent.calls[1][0], "spoken:I used the screen context...."
        )

    def test_empty_tool_progress_does_not_use_english_fallback(self) -> None:
        llm_agent = FakeToolLLMAgent(
            [
                _tool_turn(
                    tool_calls=[
                        _tool_call(
                            "take_screenshot", {"reason": "inspect screen"}
                        )
                    ],
                ),
                _tool_turn(content="Screen checked."),
            ]
        )
        tts_agent = FakeTTSAgent()
        notices: list[str] = []
        stages: list[tuple[str, str]] = []
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            screen_capture_agent=FakeToolScreenCaptureAgent(),
            settings=_tool_settings(),
        )

        strategy.execute(
            {
                "recording_path": "input.wav",
                "tool_notice_callback": notices.append,
                "status_callback": lambda state, message: stages.append(
                    (state, message)
                ),
            }
        )

        self.assertEqual(notices, [])
        self.assertNotIn(
            ("speaking", "I'll take a quick screenshot of your screen."),
            stages,
        )
        self.assertEqual(tts_agent.calls[0][0], "spoken:Screen checked....")
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

    def test_change_memory_stops_before_model_can_add_duplicate_memory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_manager = MemoryManager(Path(temp_dir) / "memories.json")
            memory_manager.add_memory(
                title="Billing export",
                description="Remember billing CSV export.",
            )
            memory_manager.add_memory(
                title="Billing reminder",
                description="Remember billing email follow-up.",
            )
            llm_agent = FakeToolLLMAgent(
                [
                    _tool_turn(
                        tool_calls=[
                            _tool_call(
                                "change_memory",
                                {
                                    "query": "billing",
                                    "description": "Updated billing note.",
                                },
                            )
                        ]
                    ),
                    _tool_turn(
                        tool_calls=[
                            _tool_call(
                                "add_memory",
                                {
                                    "title": "Duplicate billing",
                                    "description": "Updated billing note.",
                                },
                            )
                        ]
                    ),
                ]
            )
            tts_agent = FakeTTSAgent()
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=llm_agent,
                tts_agent=tts_agent,
                settings=_tool_settings(),
                memory_manager=memory_manager,
            )

            interaction = strategy.execute({"recording_path": "input.wav"})
            memories = memory_manager.list_memories()

        self.assertEqual(len(interaction.tool_calls), 1)
        self.assertEqual(interaction.tool_calls[0].tool_name, "change_memory")
        self.assertEqual(len(llm_agent.message_snapshots), 1)
        self.assertIn("not sure which memory", llm_agent.prepare_inputs[0])
        self.assertEqual(
            interaction.response, f"spoken:{llm_agent.prepare_inputs[0]}"
        )
        self.assertEqual(len(memories), 2)
        self.assertEqual(
            [memory.description for memory in memories],
            [
                "Remember billing email follow-up.",
                "Remember billing CSV export.",
            ],
        )

    def test_change_memory_missing_id_uses_clear_followup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            llm_agent = FakeToolLLMAgent(
                [
                    _tool_turn(
                        tool_calls=[
                            _tool_call(
                                "change_memory",
                                {
                                    "memory_id": (
                                        "tool-call-id-not-memory-id"
                                    ),
                                    "description": "Updated note.",
                                },
                            )
                        ]
                    )
                ]
            )
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=llm_agent,
                tts_agent=FakeTTSAgent(),
                settings=_tool_settings(),
                memory_manager=MemoryManager(
                    Path(temp_dir) / "memories.json"
                ),
            )

            interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertEqual(interaction.tool_calls[0].status, "error")
        self.assertIn("not find", llm_agent.prepare_inputs[0])

    def test_speech_drift_meaning_words_ignore_common_stopwords(self) -> None:
        self.assertEqual(
            live_strategy_module._meaning_words(
                "The quick answer and the result looks like this"
            ),
            ["quick", "answer", "result"],
        )

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
        self.assertEqual(
            llm_agent.enabled_tool_name_sets[0],
            {"web_search", "end_live_session"},
        )

    def test_tools_disabled_uses_normal_live_reply_without_provider_tools(
        self,
    ) -> None:
        llm_agent = FakeLLMAgent()
        tts_agent = FakeTTSAgent()
        strategy = LiveStrategy(
            transcription_agent=FakeTranscriptionAgent(),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            settings=_tool_settings(tools_enabled=False),
        )

        interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertEqual(len(llm_agent.calls), 1)
        self.assertEqual(
            llm_agent.calls[0]["transcript"], "transcript for input.wav"
        )
        self.assertEqual(interaction.tool_calls, [])
        self.assertEqual(interaction.response, "[curious] Hello there!")

    def test_tools_disabled_weather_request_uses_normal_live_reply(
        self,
    ) -> None:
        llm_agent = FakeLLMAgent()
        strategy = LiveStrategy(
            transcription_agent=FakePhraseTranscriptionAgent(
                "what is the weather in Vilnius"
            ),
            llm_agent=llm_agent,
            tts_agent=FakeTTSAgent(),
            settings=_tool_settings(tools_enabled=False),
        )

        interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertEqual(len(llm_agent.calls), 1)
        self.assertEqual(
            llm_agent.calls[0]["transcript"],
            "what is the weather in Vilnius",
        )
        self.assertEqual(interaction.tool_calls, [])

    def test_tools_disabled_stop_request_ends_locally_without_model_turn(
        self,
    ) -> None:
        llm_agent = FakeLLMAgent()
        tts_agent = FakeTTSAgent()
        session = SessionRecord(mode="live")
        session.add_interaction(
            LiveInteraction(
                mode="live",
                recording_path="previous.wav",
                transcript="copy the headline",
                response="Done, I copied it to your clipboard. Anything else?",
                speech_path="reply.wav",
            )
        )
        strategy = LiveStrategy(
            transcription_agent=FakePhraseTranscriptionAgent("no thanks"),
            llm_agent=llm_agent,
            tts_agent=tts_agent,
            settings=_tool_settings(tools_enabled=False),
        )

        interaction = strategy.execute(
            {"recording_path": "input.wav", "session": session}
        )

        self.assertEqual(llm_agent.calls, [])
        self.assertEqual(tts_agent.calls, [])
        self.assertEqual(interaction.response, "Live ended.")
        self.assertEqual(interaction.speech_path, "")
        self.assertEqual(
            interaction.tool_calls[0].tool_name, "end_live_session"
        )

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
        self.assertEqual(llm_agent.prepare_inputs, [])
        self.assertEqual(
            tts_agent.calls[0][0],
            "Done, I copied it to your clipboard. Anything else?...",
        )
        self.assertEqual(tts_agent.calls[0][2], "UgBBYS2sOqTuMpoF3BR0")
        self.assertEqual(notices, [])
        self.assertIn(("idle", "OCR copied text to clipboard."), stages)
        self.assertEqual(interaction.tool_calls[0].tool_name, "ocr_screen")
        self.assertEqual(interaction.tool_calls[0].status, "success")
        self.assertEqual(
            interaction.response,
            "Done, I copied it to your clipboard. Anything else?",
        )
        self.assertTrue(interaction.speech_path.endswith(".wav"))

    def test_ocr_confirmation_uses_static_speech_file_when_available(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            static_speech_dir = Path(temp_dir)
            static_path = (
                static_speech_dir
                / static_live_speech_file_name(
                    "Done, I copied it to your clipboard. Anything else?",
                    "UgBBYS2sOqTuMpoF3BR0",
                )
            )
            static_path.write_bytes(b"RIFFstatic-confirmation")
            llm_agent = FakeToolLLMAgent(
                [
                    _tool_turn(
                        tool_calls=[
                            _tool_call(
                                "ocr_screen",
                                {"instruction": "Extract the headline."},
                            )
                        ]
                    )
                ]
            )
            tts_agent = FakeTTSAgent()
            strategy = LiveStrategy(
                transcription_agent=FakeTranscriptionAgent(),
                llm_agent=llm_agent,
                tts_agent=tts_agent,
                screen_capture_agent=FakeToolScreenCaptureAgent(),
                ocr_agent=FakeOCRAgent("Headline"),
                clipboard_service=FakeClipboardService(),
                settings=_tool_settings(),
                static_speech_dir=static_speech_dir,
            )

            interaction = strategy.execute({"recording_path": "input.wav"})

        self.assertEqual(tts_agent.calls, [])
        self.assertEqual(interaction.speech_path, str(static_path))
        self.assertEqual(
            interaction.response,
            "Done, I copied it to your clipboard. Anything else?",
        )

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
            settings=_tool_settings(tools_enabled=True),
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
        self.assertEqual(
            interaction.tool_calls[0].tool_name, "end_live_session"
        )
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
        self.assertEqual(
            interaction.tool_calls[0].tool_name, "end_live_session"
        )
        self.assertIn(("idle", "Live ended."), stages)

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
