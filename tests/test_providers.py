import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.models.settings import AppSettings
from src.services.providers import (
    NagaTranscriptionProvider,
    OpenAICompatibleProvider,
    _extract_text_content,
)


class ContentExtractionTests(unittest.TestCase):
    def test_extract_text_content_handles_plain_string(self) -> None:
        self.assertEqual(_extract_text_content("hello"), "hello")

    def test_extract_text_content_handles_part_list(self) -> None:
        content = [
            {"type": "text", "text": "hello"},
            {"type": "text", "text": {"value": "world"}},
        ]

        self.assertEqual(_extract_text_content(content), "hello\nworld")


class ProviderReasoningToggleTests(unittest.TestCase):
    def test_llm_reasoning_kwargs_are_omitted_when_toggle_is_off(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_api_key": "secret",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "llm_reasoning_enabled": False,
                "llm_reasoning": "high",
            }
        )

        with patch.object(
            OpenAICompatibleProvider, "_build_client", return_value=object()
        ):
            provider = OpenAICompatibleProvider(settings)

        self.assertEqual(provider._llm_reasoning_kwargs(), {})
        self.assertEqual(provider._llm_reasoning_label(), "off")

    def test_transcription_reasoning_kwargs_are_omitted_when_toggle_is_off(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "transcription_api_key": "secret",
                "transcription_reasoning_enabled": False,
                "transcription_reasoning": "high",
            }
        )

        with patch.object(
            NagaTranscriptionProvider, "_build_client", return_value=object()
        ):
            provider = NagaTranscriptionProvider(settings)

        self.assertEqual(provider._transcription_reasoning_kwargs(), {})
        self.assertEqual(provider._transcription_reasoning_label(), "off")


class ProviderToolTurnTests(unittest.TestCase):
    def test_run_tool_turn_extracts_tool_calls(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            },
            validate=False,
        )
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider._settings = settings
        tool_call = SimpleNamespace(
            id="call-1",
            function=SimpleNamespace(
                name="web_search",
                arguments='{"query": "latest news"}',
            ),
        )
        completions_create = unittest.mock.Mock(
            return_value=SimpleNamespace(
                usage=None,
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="",
                            tool_calls=[tool_call],
                        )
                    )
                ],
            )
        )
        provider._client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=completions_create)
            )
        )

        turn = provider.run_tool_turn(
            messages=[{"role": "user", "content": "look up current news"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        )

        self.assertEqual(turn.tool_calls[0].name, "web_search")
        self.assertEqual(
            turn.tool_calls[0].arguments, {"query": "latest news"}
        )
        self.assertEqual(
            completions_create.call_args.kwargs["tools"][0]["function"][
                "name"
            ],
            "web_search",
        )
        self.assertEqual(
            completions_create.call_args.kwargs["tool_choice"], "auto"
        )

    def test_openrouter_tool_turn_adds_cache_and_session_options(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://openrouter.ai/api/v1",
                "llm_model_name": "google/gemini-3.1-flash-lite-preview",
                "tts_base_url": "https://tts.example.com/v1",
            },
            validate=False,
        )
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider._settings = settings
        completions_create = unittest.mock.Mock(
            return_value=SimpleNamespace(
                usage=None,
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="done", tool_calls=[])
                    )
                ],
            )
        )
        provider._client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=completions_create)
            )
        )

        provider.run_tool_turn(
            messages=[
                {"role": "system", "content": "stable tool prompt"},
                {"role": "user", "content": "look at this"},
            ],
            tools=[],
            session_id="session-123",
        )

        kwargs = completions_create.call_args.kwargs
        self.assertEqual(
            kwargs["extra_headers"]["x-session-affinity"], "session-123"
        )
        self.assertEqual(kwargs["extra_body"]["session_id"], "session-123")
        self.assertEqual(
            kwargs["extra_body"]["prompt_cache_key"], "session-123"
        )
        self.assertEqual(kwargs["extra_body"]["usage"], {"include": True})
        self.assertEqual(
            kwargs["messages"][0]["content"][0]["cache_control"],
            {"type": "ephemeral"},
        )
        self.assertEqual(
            kwargs["messages"][0]["content"][0]["text"],
            "stable tool prompt",
        )
        self.assertEqual(kwargs["messages"][1]["content"], "look at this")

    def test_non_openrouter_tool_turn_leaves_cache_options_out(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
            },
            validate=False,
        )
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider._settings = settings
        completions_create = unittest.mock.Mock(
            return_value=SimpleNamespace(
                usage=None,
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="done", tool_calls=[])
                    )
                ],
            )
        )
        provider._client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=completions_create)
            )
        )

        provider.run_tool_turn(
            messages=[{"role": "system", "content": "stable prompt"}],
            tools=[],
            session_id="session-123",
        )

        kwargs = completions_create.call_args.kwargs
        self.assertNotIn("extra_headers", kwargs)
        self.assertNotIn("extra_body", kwargs)
        self.assertEqual(kwargs["messages"][0]["content"], "stable prompt")

    def test_run_tool_turn_can_use_multimodal_provider_client(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "text-model",
                "tts_base_url": "https://tts.example.com/v1",
            },
            validate=False,
        )
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider._settings = settings
        text_create = unittest.mock.Mock()
        audio_create = unittest.mock.Mock(
            return_value=SimpleNamespace(
                usage=None,
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="audio answer", tool_calls=[]
                        )
                    )
                ],
            )
        )
        provider._client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=text_create)
            )
        )
        audio_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=audio_create)
            )
        )

        turn = provider.run_tool_turn(
            messages=[{"role": "user", "content": "audio request"}],
            tools=[],
            client=audio_client,
            model_name="audio-model",
            reasoning_kwargs={"reasoning_effort": "minimal"},
            reasoning_label="minimal",
        )

        self.assertEqual(turn.content, "audio answer")
        text_create.assert_not_called()
        self.assertEqual(audio_create.call_args.kwargs["model"], "audio-model")
        self.assertEqual(
            audio_create.call_args.kwargs["reasoning_effort"],
            "minimal",
        )


class ProviderAudioUploadTests(unittest.TestCase):
    def test_multimodal_live_uses_mp3_audio_format_when_available(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "tts_voice_id": "UgBBYS2sOqTuMpoF3BR0",
            },
            validate=False,
        )
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider._settings = settings
        completions_create = unittest.mock.Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="hello there")
                    )
                ]
            )
        )
        provider._client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=completions_create)
            )
        )

        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as wav_file,
            tempfile.NamedTemporaryFile(suffix=".mp3") as mp3_file,
        ):
            wav_file.write(b"wav-audio")
            wav_file.flush()
            mp3_file.write(b"mp3-audio")
            mp3_file.flush()

            with patch(
                "src.services.providers._prepare_audio_upload_path",
                return_value=(Path(mp3_file.name), lambda: None),
            ):
                reply = provider.generate_live_speech_reply_from_audio(
                    audio_path=wav_file.name,
                    transcript="open settings",
                )

        self.assertEqual(reply.text, "hello there")
        audio_part = completions_create.call_args.kwargs["messages"][1][
            "content"
        ][1]
        instruction_part = completions_create.call_args.kwargs["messages"][1][
            "content"
        ][0]
        self.assertIn(
            "Recognized transcript: open settings", instruction_part["text"]
        )
        self.assertIn("source of truth", instruction_part["text"])
        self.assertEqual(audio_part["input_audio"]["format"], "mp3")

    def test_multimodal_tool_messages_include_audio_and_speech_tool_prompt(
        self,
    ) -> None:
        settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "tts_voice_id": "UgBBYS2sOqTuMpoF3BR0",
            },
            validate=False,
        )
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider._settings = settings

        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as wav_file,
            tempfile.NamedTemporaryFile(suffix=".mp3") as mp3_file,
        ):
            wav_file.write(b"wav-audio")
            wav_file.flush()
            mp3_file.write(b"mp3-audio")
            mp3_file.flush()

            with patch(
                "src.services.providers._prepare_audio_upload_path",
                return_value=(Path(mp3_file.name), lambda: None),
            ):
                messages = provider.build_live_tool_messages_from_audio(
                    audio_path=wav_file.name,
                    transcript="search for weather",
                    conversation_history=[
                        {"role": "assistant", "content": "previous"}
                    ],
                    enabled_tool_names={"web_search", "end_live_session"},
                )

        self.assertIn("Tools are available", messages[0]["content"])
        self.assertIn("VOICE_ID", messages[0]["content"])
        self.assertEqual(
            messages[1], {"role": "assistant", "content": "previous"}
        )
        audio_part = messages[2]["content"][1]
        instruction_part = messages[2]["content"][0]
        self.assertIn(
            "Recognized transcript: search for weather",
            instruction_part["text"],
        )
        self.assertIn("source of truth", instruction_part["text"])
        self.assertEqual(audio_part["type"], "input_audio")
        self.assertEqual(audio_part["input_audio"]["format"], "mp3")


if __name__ == "__main__":
    unittest.main()
