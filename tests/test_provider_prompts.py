import unittest

from src.models.settings import AppSettings
from src.services.providers import (
    LiveSpeechReply,
    OpenAICompatibleProvider,
    NagaTranscriptionProvider,
    _format_usage,
    _preview_text,
)


class ProviderPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings.from_mapping(
            {
                "llm_base_url": "https://api.example.com/v1",
                "llm_model_name": "model-a",
                "tts_base_url": "https://tts.example.com/v1",
                "fallback_language": "en",
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

    def test_system_prompt_supports_immediate_language_switch(self) -> None:
        prompt = self.provider._build_system_prompt(match_user_language=True)

        self.assertIn(
            "If they ask for another language, answer in that language immediately in the same reply.",
            prompt,
        )

    def test_tts_preparation_prompt_encourages_contextual_vocal_tags(self) -> None:
        prompt = self.provider._build_tts_preparation_prompt()

        self.assertIn("Actively apply Eleven v3 best practices", prompt)
        self.assertIn(
            "voice-related tags, non-verbal vocal sounds, accent tags, and sound effect tags",
            prompt,
        )
        self.assertIn("include at least one suitable Eleven-style tag", prompt)
        self.assertIn("Never use angle-bracket tags like <laugh>", prompt)
        self.assertIn("never use emoji", prompt)
        self.assertIn("Reply only with the final speech text", prompt)

    def test_transcription_prompt_allows_high_confidence_context_inference(
        self,
    ) -> None:
        prompt = NagaTranscriptionProvider._build_transcription_prompt()

        self.assertIn("use the surrounding context to infer", prompt)
        self.assertIn("high confidence", prompt)
        self.assertIn("stay conservative rather than inventing content", prompt)

    def test_live_speech_prompt_merges_reply_and_delivery_rules(self) -> None:
        prompt = self.provider._build_live_speech_system_prompt()

        self.assertIn("final spoken text", prompt)
        self.assertIn("Do not change speaker identity or perspective", prompt)
        self.assertIn("Actively follow Eleven v3 best practices", prompt)
        self.assertIn(
            "Use only square-bracket Eleven-style tags",
            prompt,
        )
        self.assertIn("Never use angle-bracket tags like <laugh>", prompt)
        self.assertIn("never use emoji", prompt)
        self.assertIn("place the main tag at the start of the reply", prompt)
        self.assertIn(
            "Small conversational turns should usually be one short sentence", prompt
        )
        self.assertIn("ask at most one follow-up question", prompt)

    def test_live_speech_prompt_lists_auto_voice_contract(self) -> None:
        prompt = self.provider._build_live_speech_system_prompt()

        self.assertIn("VOICE_ID: <id>", prompt)
        self.assertIn("Allowed voice: BIvP0GN1cAtSRTxNHnWS - Ellen", prompt)
        self.assertIn(
            "prefer Mark unless another voice is clearly a better fit", prompt
        )
        self.assertIn("Choose the voice before composing the final reply", prompt)

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


if __name__ == "__main__":
    unittest.main()
