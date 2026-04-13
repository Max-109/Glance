import unittest

from src.models.settings import AppSettings
from src.services.providers import (
    OpenAICompatibleProvider,
    NagaTranscriptionProvider,
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

        self.assertIn("Actively add Eleven v3 vocal tags", prompt)
        self.assertIn("In most replies", prompt)
        self.assertIn("not randomly or excessively", prompt)

    def test_transcription_prompt_allows_high_confidence_context_inference(
        self,
    ) -> None:
        prompt = NagaTranscriptionProvider._build_transcription_prompt()

        self.assertIn("use the surrounding context to infer", prompt)
        self.assertIn("high confidence", prompt)
        self.assertIn("stay conservative rather than inventing content", prompt)

    def test_preview_text_normalizes_whitespace_and_truncates(self) -> None:
        preview = _preview_text("Hello\n\nthere   general   kenobi" * 40, limit=40)

        self.assertNotIn("\n", preview)
        self.assertLessEqual(len(preview), 40)
        self.assertTrue(preview.endswith("..."))


if __name__ == "__main__":
    unittest.main()
