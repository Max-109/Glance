<div align="center">
  <img src="./docs/media/glance-mark-mono.svg" width="84" alt="Glance mark" />
  <h1>Glance</h1>
  <p><strong>Press a shortcut. Speak. Get the answer back out loud.</strong></p>
  <p>
    <img alt="Coursework" src="https://img.shields.io/badge/coursework-OOP%202026-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Backend" src="https://img.shields.io/badge/backend-Python-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Frontend" src="https://img.shields.io/badge/frontend-Electron%20%2B%20Next.js%20%2B%20Bun-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Voice" src="https://img.shields.io/badge/voice-Eleven%20v3-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
  </p>
  <img src="./docs/media/showcase.gif" alt="Glance app showcase" width="900" />
</div>

## About

Glance is my OOP coursework project: a macOS live agent app that stays out of the way until I need it.

I press a customizable shortcut, speak, and Glance runs a Live turn. If I only need text from the screen, I use OCR and Glance copies the extracted text to the clipboard.

## Features

- Customizable shortcuts.
- Configurable OpenAI-compatible endpoints for reply, transcription, and voice.
- Eleven v3 voice output, currently the best multilingual TTS model, with excellent voice quality and support for different emotions. (Supported by Glance.)
- Advanced TEN VAD audio detection for natural speech turns.
- Various tools available for the live agent to use.
- Saved history with transcript, response, audio, screenshots, and tool records.
- Saved memories that the live agent can read and update.

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

## Using The App

1. Open Glance.
2. Configure reply, transcription, and voice providers in settings.
3. Set the Live, OCR, and Open Glance shortcuts.
4. Choose audio devices and voice settings.
5. Enable only the tools you want the live agent to use.
6. Press the Live shortcut and speak.
7. Press the OCR shortcut when you want visible text copied from the screen.

Settings are saved in `~/.glance/config.json`. Sessions are saved under `~/.glance/sessions`. Memories are saved in `~/.glance/memories.json`.

## Running The App

```bash
# Create and enter the Python virtual environment.
python3 -m venv .venv
source .venv/bin/activate

# Install Python and frontend dependencies.
python -m pip install -r requirements.txt

bun install
bun run build

# Open the Python backend and Electron frontend.
python3 main.py
```

Glance needs macOS permissions for microphone, screen recording, and accessibility.

## Implementation

Glance is made of Python as the backend and Electron + Next.js + Bun as the frontend, styled with Tailwind CSS v4.

| Area | Role |
| --- | --- |
| `main.py` | Starts the desktop app or CLI mode. |
| `src/ui/qt_app.py` | Owns the macOS menu bar behavior, tray mark, hotkeys, OCR, and Electron startup. |
| `src/ui/electron_window.py` | Launches and controls the Electron settings window. |
| `src/core/orchestrator.py` | Connects settings, agents, strategies, history, memories, providers, and clipboard services. |
| `src/strategies/live_strategy.py` | Runs the Live pipeline, tool loop, transcription path, multimodal path, and speech output. |
| `src/strategies/ocr_strategy.py` | Runs screenshot capture and OCR extraction. |
| `src/tools/runtime.py` | Defines and executes Live tools. |
| `src/storage/json_storage.py` | Reads and writes settings, sessions, artifacts, and conversation Markdown. |
| `components/` | Builds the Electron settings UI. |

## OOP Requirements

### Abstraction

Glance uses abstract base classes to define what objects must do, while hiding how they do it.

```python
class BaseAgent(ABC):
    @abstractmethod
    def run(self, **kwargs):
        "Execute the agent's main behavior."
```

`BaseAgent`, `ModeStrategy`, `BaseInteraction`, and `AbstractRepository` are the clearest examples. The rest of the app can depend on these contracts instead of concrete details.

### Encapsulation

State is kept inside focused classes. `AppSettings.validate()` owns settings validation, `TenVadAudioRecorder` owns audio capture details, and `RuntimeToolRegistry` owns tool availability rules.

```python
if name == "web_fetch":
    return self._settings.tool_web_fetch_policy
```

The caller does not need to know how every setting is stored. It asks the registry what is available.

### Inheritance

Several classes extend shared base types:

- `LiveStrategy` and `OCRStrategy` inherit from `ModeStrategy`.
- `LLMAgent`, `OCRAgent`, `ScreenCaptureAgent`, `TranscriptionAgent`, and `TTSAgent` inherit from `BaseAgent`.
- `LiveInteraction`, `OCRInteraction`, and `QuickInteraction` inherit from `BaseInteraction`.
- `SessionDirectoryRepository` inherits from `AbstractRepository[SessionRecord]`.

### Polymorphism

The orchestrator can run different modes through the same `execute(...)` call:

```python
strategy = self._strategy_factory.create(mode=mode, ...)
interaction = strategy.execute(execution_context)
```

That works because both Live and OCR strategies follow the same interface.

### Composition And Aggregation

`Orchestrator` is built from smaller objects: settings, history, memories, strategy factory, screen capture, transcription, LLM, OCR, TTS, and clipboard services.

## Design Pattern

Glance uses **Strategy** and **Factory Method**.

`LiveStrategy` and `OCRStrategy` are separate workflows. `ModeStrategyFactory` chooses the right one at runtime:

```python
if normalized_mode == "ocr":
    return OCRStrategy(...)
if normalized_mode == "live":
    return LiveStrategy(...)
```

This fits better than a Singleton because the app needs replaceable services for tests and runtime configuration.

## File Reading And Writing

Glance reads and writes real files:

- `~/.glance/config.json` for settings.
- `~/.glance/sessions/.../session.json` for saved sessions.
- `~/.glance/sessions/.../conversation.md` for readable conversation export.
- `~/.glance/memories.json` for saved memories.
- Audio, speech, screenshot, OCR, and tool result artifacts.

## Testing

```bash
.venv/bin/python -m unittest discover -s tests
node --test tests/electron_window_control.test.js tests/electron_window_chrome.test.js
bun run typecheck
bun run build
```

The tests cover settings validation, storage, history, live strategy behavior, tool execution, providers, OCR capture, hotkeys, Electron window control, and runtime status sync.

## Results

- Glance can run a full Live turn: listen, transcribe or use multimodal audio, call the model, use allowed tools, speak the answer, and save the session.
- OCR works as a quick workflow for extracting visible text and copying it to the clipboard.
- The tool system is permission-based, so disabled tools are not shown to the model.

## Conclusions

It was fun to work on this project. Glance started as a coursework idea, but it became a real desktop app I can actually use.
