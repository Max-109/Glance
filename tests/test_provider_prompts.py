import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.models.settings import AppSettings
from src.services.providers import (
    DEFAULT_TEXT_REPLY_PROMPT,
    DEFAULT_TRANSCRIPTION_PROMPT,
    DEFAULT_TTS_PREPARATION_PROMPT,
    DEFAULT_VOICE_REPLY_PROMPT,
    LiveSpeechReply,
    NagaTranscriptionProvider,
    OpenAICompatibleProvider,
    _format_usage,
    _format_usage_summary,
    _preview_text,
)


class ProviderPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "system_prompt_override": "Be extra attentive to follow-up questions.",
            },
            validate=False,
        )
        self.provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        self.provider._settings = self.settings

    def test_system_prompt_keeps_base_identity_and_appends_override(self) -> None:
        prompt = self.provider._build_system_prompt(match_user_language=False)

        self.assertIn("You are Glance, a live desktop voice assistant.", prompt)
        self.assertIn(
            "Additional instructions: Be extra attentive to follow-up questions.",
            prompt,
        )

    def test_system_prompt_starts_with_runtime_context(self) -> None:
        moment = datetime(
            2026,
            4,
            25,
            12,
            34,
            tzinfo=timezone(timedelta(hours=3), "EEST"),
        )

        with patch(
            "src.services.providers._current_local_datetime",
            return_value=moment,
        ), patch(
            "src.services.providers._detect_user_country",
            return_value="Lithuania",
        ):
            prompt = self.provider._build_system_prompt(match_user_language=False)

        self.assertTrue(
            prompt.startswith(
                "Current day and time: Saturday, April 25, 2026, 12:34 EEST (UTC+03:00).\n"
                "User country: Lithuania.\n"
                "Use the current day, date, time, year, timezone, and user country above as the source of truth.\n\n"
            )
        )

    def test_text_prompt_override_replaces_default_base(self) -> None:
        self.provider._settings.text_prompt_override = "You are a terse text assistant."

        prompt = self.provider._build_system_prompt(match_user_language=False)

        self.assertIn("You are a terse text assistant.", prompt)
        self.assertNotIn(DEFAULT_TEXT_REPLY_PROMPT, prompt)

    def test_system_prompt_matches_user_language_and_supports_immediate_switch(self) -> None:
        prompt = self.provider._build_system_prompt(match_user_language=False)

        self.assertIn("Reply in the same language as the user's request", prompt)
        self.assertNotIn("Reply in en", prompt)
        self.assertIn(
            "If they ask for another language, answer in that language immediately in the same reply.",
            prompt,
        )
        self.assertIn(
            "Do not claim you are limited to English or cannot speak a requested language",
            prompt,
        )

    def test_tts_preparation_prompt_is_strict_cleanup_not_rewrite(self) -> None:
        prompt = self.provider._build_tts_preparation_prompt()

        self.assertIn("strict cleanup step, not a new answer", prompt)
        self.assertIn("Keep the same facts, meaning, speaker, perspective, and intent", prompt)
        self.assertIn("Do not add facts, jokes, personal stories", prompt)
        self.assertIn("Use simple, direct wording", prompt)
        self.assertIn("Preserve or add emotional delivery on most replies", prompt)
        self.assertIn("roughly 85 percent of the time", prompt)
        self.assertIn("[reassuring]", prompt)
        self.assertIn("Never use angle-bracket tags like <laugh>", prompt)

    def test_transcription_prompt_allows_high_confidence_context_inference(
        self,
    ) -> None:
        provider = NagaTranscriptionProvider.__new__(NagaTranscriptionProvider)
        provider._settings = self.settings
        prompt = provider._build_transcription_prompt()

        self.assertIn("use the surrounding context to infer", prompt)
        self.assertIn("high confidence", prompt)
        self.assertIn("stay conservative rather than inventing content", prompt)

    def test_transcription_prompt_override_replaces_default_base(self) -> None:
        provider = NagaTranscriptionProvider.__new__(NagaTranscriptionProvider)
        provider._settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "transcription_prompt_override": "Return a clean transcript and nothing else.",
            },
            validate=False,
        )

        prompt = provider._build_transcription_prompt()

        self.assertIn("Return a clean transcript and nothing else.", prompt)
        self.assertNotIn(DEFAULT_TRANSCRIPTION_PROMPT, prompt)

    def test_live_speech_prompt_merges_reply_and_delivery_rules(self) -> None:
        prompt = self.provider._build_live_speech_system_prompt()

        self.assertIn("final spoken text", prompt)
        self.assertIn("Do not change speaker identity or perspective", prompt)
        self.assertIn("simple terms first", prompt)
        self.assertIn("Do not invent personal stories", prompt)
        self.assertIn("Use emotional delivery on most replies", prompt)
        self.assertIn("roughly 85 percent of the time", prompt)
        self.assertIn("[curious]", prompt)
        self.assertIn("Never use angle-bracket tags like <laugh>", prompt)
        self.assertIn("never use emoji", prompt)
        self.assertIn(
            "Short casual turns should usually be one short sentence", prompt
        )
        self.assertIn("Ask at most one follow-up question", prompt)

    def test_voice_prompt_override_replaces_default_base(self) -> None:
        self.provider._settings.voice_prompt_override = "Speak with dry, understated clarity."

        prompt = self.provider._build_live_speech_system_prompt()

        self.assertIn("Speak with dry, understated clarity.", prompt)
        self.assertNotIn(DEFAULT_VOICE_REPLY_PROMPT, prompt)

    def test_voice_polish_prompt_override_replaces_default_base(self) -> None:
        self.provider._settings.voice_polish_prompt_override = (
            "Polish the text gently, but keep the rhythm understated."
        )

        prompt = self.provider._build_tts_preparation_prompt()

        self.assertIn(
            "Polish the text gently, but keep the rhythm understated.",
            prompt,
        )
        self.assertNotIn(DEFAULT_TTS_PREPARATION_PROMPT, prompt)

    def test_live_speech_prompt_lists_auto_voice_contract(self) -> None:
        prompt = self.provider._build_live_speech_system_prompt()

        self.assertIn("VOICE_ID: <id>", prompt)
        self.assertIn("Allowed voice: BIvP0GN1cAtSRTxNHnWS - Ellen", prompt)
        self.assertIn(
            "prefer Mark unless another voice is clearly a better fit", prompt
        )
        self.assertIn("Choose the voice before composing the final reply", prompt)

    def test_live_tool_prompts_answer_directly_after_tools(self) -> None:
        text_prompt = self.provider.build_live_tool_messages(
            transcript="what is the weather in Vilnius",
            conversation_history=[],
        )[0]["content"]
        audio_prompt = self.provider._build_live_tool_speech_system_prompt()

        for prompt in (text_prompt, audio_prompt):
            with self.subTest(prompt=prompt[:40]):
                self.assertIn("Do not narrate the tool work", prompt)
                self.assertIn("answer with the result directly", prompt)
                self.assertIn("tool", prompt)

    def test_parse_live_speech_reply_uses_fixed_voice_when_not_auto(self) -> None:
        self.provider._settings.tts_voice_id = "UgBBYS2sOqTuMpoF3BR0"

        reply = self.provider._parse_live_speech_reply("[happy] Hello there!")

        self.assertEqual(
            reply,
            LiveSpeechReply(
                voice_id="UgBBYS2sOqTuMpoF3BR0",
                text="[happy] Hello there!",
            ),
        )

    def test_parse_live_speech_reply_extracts_auto_voice_header(self) -> None:
        self.provider._settings.tts_voice_id = "auto"

        reply = self.provider._parse_live_speech_reply(
            "VOICE_ID: BIvP0GN1cAtSRTxNHnWS\n\n[happy] Hello there!"
        )

        self.assertEqual(
            reply,
            LiveSpeechReply(
                voice_id="BIvP0GN1cAtSRTxNHnWS",
                text="[happy] Hello there!",
            ),
        )

    def test_preview_text_normalizes_whitespace_and_truncates(self) -> None:
        preview = _preview_text("Hello\n\nthere   general   kenobi" * 40, limit=40)

        self.assertNotIn("\n", preview)
        self.assertLessEqual(len(preview), 40)
        self.assertTrue(preview.endswith("..."))

    def test_format_usage_handles_dict_usage(self) -> None:
        usage = _format_usage(
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                }
            }
        )

        self.assertEqual(
            usage,
            "prompt_tokens=10,completion_tokens=20,total_tokens=30",
        )

    def test_format_usage_flattens_nested_cache_details(self) -> None:
        usage = _format_usage(
            {
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 25,
                    "total_tokens": 145,
                    "prompt_tokens_details": {"cached_tokens": 96},
                }
            }
        )

        self.assertEqual(
            usage,
            "prompt_tokens=120,completion_tokens=25,total_tokens=145,prompt_tokens_details.cached_tokens=96",
        )

    def test_format_usage_includes_cache_write_details(self) -> None:
        response = {
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 25,
                "total_tokens": 145,
                "prompt_tokens_details": {
                    "cached_tokens": 96,
                    "cache_write_tokens": 24,
                },
            }
        }

        usage = _format_usage(response)
        summary = _format_usage_summary(response)

        self.assertIn("prompt_tokens_details.cache_write_tokens=24", usage)
        self.assertIn("cached=96", summary)
        self.assertIn("cache_write=24", summary)

    def test_live_reply_request_includes_prior_conversation_history(self) -> None:
        self.provider._settings.tts_voice_id = "UgBBYS2sOqTuMpoF3BR0"
        messages_create = Mock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="[curious] Got it.")
                    )
                ],
                usage={"prompt_tokens": 10},
            )
        )
        self.provider._client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=messages_create))
        )

        reply = self.provider.generate_live_speech_reply(
            transcript="What was I just asking?",
            conversation_history=[
                {"role": "user", "content": "Remember this detail."},
                {"role": "assistant", "content": "I will remember it."},
            ],
        )

        self.assertEqual(reply.text, "[curious] Got it.")
        request_messages = messages_create.call_args.kwargs["messages"]
        self.assertEqual(request_messages[1]["content"], "Remember this detail.")
        self.assertEqual(request_messages[2]["content"], "I will remember it.")
        self.assertEqual(
            request_messages[3], {"role": "user", "content": "What was I just asking?"}
        )


if __name__ == "__main__":
    unittest.main()
