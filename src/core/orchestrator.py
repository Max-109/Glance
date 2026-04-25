from __future__ import annotations

from src.agents.audio_capture_agent import AudioCaptureAgent
from src.agents.llm_agent import LLMAgent
from src.agents.ocr_agent import OCRAgent
from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.agents.screen_diff_agent import ScreenDiffAgent
from src.agents.tts_agent import TTSAgent
from src.agents.transcription_agent import TranscriptionAgent
from src.factories.strategy_factory import ModeStrategyFactory
from src.models.interactions import BaseInteraction, SessionRecord
from src.models.settings import AppSettings
from src.services.app_paths import AppPaths, build_app_paths
from src.services.clipboard import ClipboardService
from src.services.history_manager import HistoryManager
from src.services.providers import (
    NagaSpeechProvider,
    NagaTranscriptionProvider,
    OpenAICompatibleProvider,
)
from src.services.settings_manager import SettingsManager
from src.storage.json_storage import (
    JsonSettingsStore,
    SessionDirectoryRepository,
)


class Orchestrator:
    def __init__(
        self,
        *,
        settings: AppSettings,
        history_manager: HistoryManager,
        strategy_factory: ModeStrategyFactory,
        screen_capture_agent: ScreenCaptureAgent,
        screen_diff_agent: ScreenDiffAgent,
        audio_capture_agent: AudioCaptureAgent,
        transcription_agent: TranscriptionAgent,
        llm_agent: LLMAgent,
        ocr_agent: OCRAgent,
        tts_agent: TTSAgent,
        clipboard_service: ClipboardService,
    ) -> None:
        self._settings = settings
        self._history_manager = history_manager
        self._strategy_factory = strategy_factory
        self._screen_capture_agent = screen_capture_agent
        self._screen_diff_agent = screen_diff_agent
        self._audio_capture_agent = audio_capture_agent
        self._transcription_agent = transcription_agent
        self._llm_agent = llm_agent
        self._ocr_agent = ocr_agent
        self._tts_agent = tts_agent
        self._clipboard_service = clipboard_service

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def open_session(self, mode: str) -> SessionRecord:
        return self._history_manager.start_session(mode)

    def run_mode(
        self,
        mode: str,
        *,
        session: SessionRecord | None = None,
        **context,
    ) -> BaseInteraction:
        strategy = self._strategy_factory.create(
            mode=mode,
            screen_capture_agent=self._screen_capture_agent,
            screen_diff_agent=self._screen_diff_agent,
            audio_capture_agent=self._audio_capture_agent,
            transcription_agent=self._transcription_agent,
            llm_agent=self._llm_agent,
            ocr_agent=self._ocr_agent,
            tts_agent=self._tts_agent,
            clipboard_service=self._clipboard_service,
            settings=self._settings,
        )
        active_session = session or self._history_manager.start_session(mode)
        execution_context = dict(context)
        execution_context["session"] = active_session
        interaction = strategy.execute(execution_context)
        self._history_manager.save_interaction(active_session, interaction)
        return interaction

    def list_history(self) -> list:
        return self._history_manager.list_sessions()


def build_orchestrator() -> Orchestrator:
    paths = build_app_paths()
    settings_manager = SettingsManager(
        store=JsonSettingsStore(paths.config_file)
    )
    settings = settings_manager.load()
    history_repository = SessionDirectoryRepository(paths.sessions_dir)
    history_manager = HistoryManager(
        history_repository,
        settings.history_length,
        retention_enabled=settings.history_retention_enabled,
    )
    llm_provider = OpenAICompatibleProvider(settings)
    transcription_provider = NagaTranscriptionProvider(settings)
    tts_provider = NagaSpeechProvider(settings)
    return build_orchestrator_with_dependencies(
        settings=settings,
        paths=paths,
        history_manager=history_manager,
        llm_provider=llm_provider,
        transcription_provider=transcription_provider,
        tts_provider=tts_provider,
    )


def build_orchestrator_with_dependencies(
    *,
    settings: AppSettings,
    paths: AppPaths,
    history_manager: HistoryManager,
    llm_provider,
    transcription_provider,
    tts_provider,
) -> Orchestrator:
    return Orchestrator(
        settings=settings,
        history_manager=history_manager,
        strategy_factory=ModeStrategyFactory(),
        screen_capture_agent=ScreenCaptureAgent(),
        screen_diff_agent=ScreenDiffAgent(),
        audio_capture_agent=AudioCaptureAgent(),
        transcription_agent=TranscriptionAgent(transcription_provider),
        llm_agent=LLMAgent(llm_provider, transcription_provider),
        ocr_agent=OCRAgent(llm_provider),
        tts_agent=TTSAgent(tts_provider),
        clipboard_service=ClipboardService(),
    )
