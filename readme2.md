<div align="center">
  <img src="./docs/media/glance-mark-mono.svg" width="80" alt="Glance mark" />
  <h1>Glance</h1>
  <p><strong>Press a shortcut. Speak. Get the answer back out loud.</strong></p>
  <p>
    <img alt="Language" src="https://img.shields.io/badge/language-Python-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Desktop" src="https://img.shields.io/badge/desktop-macOS-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Agent" src="https://img.shields.io/badge/agent-live%20voice-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Coursework" src="https://img.shields.io/badge/report-OOP%20coursework-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
  </p>
  <img src="./docs/showcase.gif" alt="Glance app showcase" width="900" />
</div>

## About

Glance is my OOP coursework project: a macOS live agent app that can be invoked from anywhere with a keybind.

It has two core workflows:

- **Live** - speak to the assistant and hear a clear answer back.
- **OCR** - extract visible text from the screen and copy it to the clipboard.

The agent is provider-configurable. It uses OpenAI-compatible endpoints, so the reply model, transcription model, and speech model can be changed from the settings UI. The point is to keep the app open: not tied to one fixed vendor, and not tied to one language.

## Features

- Global shortcuts for Live, OCR, and opening the settings window.
- OpenAI-compatible provider fields for reply, transcription, and voice.
- Eleven v3 voice output.
- TEN VAD audio detection for natural speech turns.
- Tool permissions, so the model only gets tools the user allowed.
- Saved history with transcript, response, audio, screenshots, and tool records.
- Saved memories that the live agent can read and update.
- Electron + Next.js settings window, controlled by the Python runtime.

## Tools

| Tool | Description |
| --- | --- |
| Screenshot | Captures the current screen when visual context is needed. |
| OCR | Extracts requested text from the screen and copies it to the clipboard. |
| Web search | Finds current public information for answers that may change over time. |
| Web fetch | Reads one public web page and returns concise text for reasoning. |
| Add memory | Saves a task, idea, preference, plan, follow-up, or project note. |
| Read memory | Searches saved memories when the user asks what they saved or mentions an older note. |
| Change memory | Updates a saved memory when the user asks to edit or correct it. |
| End Live session | Stops listening when the user says they are done. |

## Running The App

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

bun install
GLANCE_PYTHON=.venv/bin/python bun run dev:desktop
```

Build the settings shell and run the Python app:

```bash
bun run build
.venv/bin/python main.py
```

CLI fallback:

```bash
.venv/bin/python main.py --cli
```

Glance needs macOS permissions for microphone, screen recording, and accessibility.

## Using The App

1. Open Glance.
2. Set provider base URLs, API keys, and models.
3. Choose audio devices and voice settings.
4. Enable the tools you want the agent to use.
5. Press `CMD+SHIFT+L` for Live.
6. Press `CMD+SHIFT+O` for OCR.
7. Press `CMD+SHIFT+G` to open the settings window.

## Project Structure

| Path | Purpose |
| --- | --- |
| `src/core/orchestrator.py` | Main runtime coordinator. |
| `src/factories/strategy_factory.py` | Chooses Live or OCR workflow. |
| `src/strategies/live_strategy.py` | Live voice pipeline and tool loop. |
| `src/strategies/ocr_strategy.py` | OCR pipeline. |
| `src/tools/runtime.py` | Tool definitions, permissions, and execution. |
| `src/services/audio_recording.py` | TEN VAD speech capture. |
| `src/services/providers.py` | OpenAI-compatible model calls. |
| `src/services/memory_manager.py` | Saved memories. |
| `src/storage/json_storage.py` | Settings/session persistence. |
| `src/ui/qt_app.py` | macOS menu bar app and hotkeys. |
| `components/` | Electron settings UI. |

## Coursework Analysis

### Abstraction

The project uses interfaces/abstract base classes for shared behavior:

- `BaseAgent.run(...)`
- `ModeStrategy.execute(...)`
- `AbstractRepository.load(...)`, `save(...)`, and `list_all(...)`
- `BaseInteraction.summary(...)`

This keeps the higher-level code clean. For example, the orchestrator does not need to know every detail of Live and OCR. It only needs a strategy with `execute(...)`.

### Encapsulation

Each class owns its own state and validation. `AppSettings` validates settings. `RuntimeToolRegistry` decides which tools are exposed. `HistoryManager` manages session records. `MemoryManager` handles memory search and updates.

### Inheritance

Concrete classes extend shared base classes:

- `LiveStrategy` and `OCRStrategy` inherit from `ModeStrategy`.
- `LLMAgent`, `OCRAgent`, `ScreenCaptureAgent`, `TranscriptionAgent`, and `TTSAgent` inherit from `BaseAgent`.
- `LiveInteraction` and `OCRInteraction` inherit from `BaseInteraction`.
- `SessionDirectoryRepository` inherits from `AbstractRepository`.

### Polymorphism

Polymorphism is used when the orchestrator runs a mode:

```python
strategy = self._strategy_factory.create(mode=mode, ...)
interaction = strategy.execute(execution_context)
```

The strategy can be Live or OCR. The call stays the same.

### Composition / Aggregation

`Orchestrator` is assembled from smaller services:

```python
Orchestrator(
    settings=settings,
    history_manager=history_manager,
    memory_manager=memory_manager,
    strategy_factory=ModeStrategyFactory(...),
    screen_capture_agent=ScreenCaptureAgent(),
    transcription_agent=TranscriptionAgent(...),
    llm_agent=LLMAgent(...),
    ocr_agent=OCRAgent(...),
    tts_agent=TTSAgent(...),
    clipboard_service=ClipboardService(),
)
```

This is easier to test and easier to change than one large class.

### Design Pattern

The main pattern is **Strategy**. Live and OCR are different algorithms behind the same interface.

The project also uses a small **Factory Method** in `ModeStrategyFactory`, because the app chooses the strategy at runtime.

## File Input And Output

The program reads and writes:

- Config: `~/.glance/config.json`
- Sessions: `~/.glance/sessions`
- Conversation exports: `conversation.md`
- Memories: `~/.glance/memories.json`
- Audio files: user recordings and generated replies
- Images: screenshots and OCR captures
- Tool result files: text results and artifacts

## Testing And Style

Python tests use `unittest`:

```bash
.venv/bin/python -m unittest discover -s tests
```

The Electron side uses Node tests:

```bash
node --test tests/electron_window_control.test.js tests/electron_window_chrome.test.js
```

The settings UI can be checked and built with:

```bash
bun run typecheck
bun run build
```

The Python code is split into modules by responsibility and follows normal PEP8 naming and layout.

## Results

- The app runs as a real macOS menu bar tool.
- The Live mode can handle speech input, model replies, tool calls, and voice output.
- OCR can extract visible text and copy it to the clipboard.
- Settings, sessions, memories, and artifacts persist to files.
- Unit tests cover the important runtime parts.

## Conclusions

Glance is a working OOP project, not just a demo script. It uses classes, interfaces, strategies, repositories, services, and models to keep the app understandable.

The next step would be packaging it properly for easier installation. After that, I would improve onboarding, add more tools, and make provider setup less manual.
