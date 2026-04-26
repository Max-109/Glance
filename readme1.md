<div align="center">
  <img src="./docs/media/glance-mark-mono.svg" width="84" alt="Glance mark" />
  <h1>Glance</h1>
  <p><strong>A small macOS live agent you can call from anywhere.</strong></p>
  <p>
    <img alt="Coursework" src="https://img.shields.io/badge/coursework-OOP%202026-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Runtime" src="https://img.shields.io/badge/runtime-Python%20%2B%20PySide6-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="UI" src="https://img.shields.io/badge/UI-Electron%20%2B%20Next.js-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Voice" src="https://img.shields.io/badge/voice-Eleven%20v3-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
  </p>
  <img src="./docs/showcase.gif" alt="Glance app showcase" width="900" />
</div>

## Introduction

Glance is a desktop assistant that stays out of the way until I need it. I press a keybind, speak, and the app runs a live agent turn. It can also run OCR when I just need text from the screen copied quickly.

The main idea is simple: I should be able to ask for help without changing windows, copying text by hand, or opening a separate chat page. Glance listens, sends the request to a configurable OpenAI-compatible endpoint, and speaks the answer back in the same language I used unless I ask for something else.

## What It Does

- **Live agent** - starts from `CMD+SHIFT+L`, records speech, asks the configured model, and plays the answer back.
- **OCR** - starts from `CMD+SHIFT+O`, captures the current screen or selected image area, extracts requested text, and copies it to the clipboard.
- **OpenAI-compatible providers** - reply, transcription, and voice endpoints can be configured separately.
- **Multilingual replies** - the user can speak naturally in different languages, and the reply follows the conversation.
- **History** - sessions are saved with transcript, answer, audio, screenshots, tool records, and Markdown.
- **Menu bar app** - Glance lives as a macOS menu bar app, with Electron used for the settings window.

## Live Agent Tools

These are the tools exposed to the live model when tools are enabled in settings:

| Tool | What it does |
| --- | --- |
| `take_screenshot` | Captures the user's current screen when visual context is needed to answer the live request. |
| `ocr_screen` | Captures the current primary screen, extracts the exact requested text, copies the result to the clipboard, and saves the tool result. |
| `web_search` | Searches the web for current public information when the answer depends on recent facts, pricing, schedules, or details likely to change. |
| `web_fetch` | Reads a specific public `http` or `https` page and returns concise page text for reasoning. |
| `add_memory` | Saves a memory when the user asks Glance to remember a task, idea, preference, plan, follow-up, or project note. |
| `read_memory` | Searches saved memories when the user asks what they saved, asks to be reminded, or refers to previous notes. |
| `change_memory` | Updates an existing saved memory when the user asks to edit, rename, correct, or add details to it. |
| `end_live_session` | Ends the current Live session when the user clearly says they are done or asks Glance to stop listening. |

## How To Run

Glance is built for macOS because it uses menu bar APIs, microphone access, screen capture, global hotkeys, and Electron.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

bun install
GLANCE_PYTHON=.venv/bin/python bun run dev:desktop
```

For a production-style local run:

```bash
bun run build
.venv/bin/python main.py
```

For the CLI fallback:

```bash
.venv/bin/python main.py --cli
```

macOS may ask for Microphone, Screen Recording, and Accessibility permissions. Glance needs them for Live audio, OCR/screen tools, and global shortcuts.

## How To Use

1. Open Glance.
2. Configure reply, transcription, and voice providers in the settings window.
3. Set the Live, OCR, and Open Glance keybinds.
4. Enable only the tools you want the live agent to use.
5. Press the Live keybind and speak.
6. Press the OCR keybind when you want visible text copied from the screen.

Settings are saved in `~/.glance/config.json`. Sessions are saved under `~/.glance/sessions`. Memories are saved in `~/.glance/memories.json`.

## Implementation

The app has two main parts:

| Area | Role |
| --- | --- |
| `main.py` | Starts the desktop app or CLI mode. |
| `src/ui/qt_app.py` | Owns the PySide6 app, macOS menu bar behavior, tray mark, hotkeys, OCR, and Electron startup. |
| `src/ui/electron_window.py` | Launches and controls the Electron settings window. |
| `src/core/orchestrator.py` | Connects settings, agents, strategies, history, memories, providers, and clipboard services. |
| `src/strategies/live_strategy.py` | Runs the Live pipeline, tool loop, transcription path, multimodal path, and speech output. |
| `src/strategies/ocr_strategy.py` | Runs screenshot capture and OCR extraction. |
| `src/tools/runtime.py` | Defines and executes Live tools. |
| `src/storage/json_storage.py` | Reads/writes settings, sessions, artifacts, and conversation Markdown. |
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

State is kept inside focused classes. For example, `AppSettings.validate()` owns settings validation, `TenVadAudioRecorder` owns audio capture details, and `RuntimeToolRegistry` owns tool availability rules.

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

`Orchestrator` is built from many smaller objects: settings, history, memories, strategy factory, screen capture, transcription, LLM, OCR, TTS, and clipboard services. This is composition because the runtime behavior is created by connecting these parts instead of putting everything into one huge class.

## Design Pattern

Glance uses **Strategy** and **Factory Method**.

`LiveStrategy` and `OCRStrategy` are separate workflows. `ModeStrategyFactory` chooses the right one at runtime:

```python
if normalized_mode == "ocr":
    return OCRStrategy(...)
if normalized_mode == "live":
    return LiveStrategy(...)
```

This fits better than a Singleton because the app needs replaceable services for tests and for runtime configuration. A single global object would make that harder.

## File Reading And Writing

Glance reads and writes real files:

- `~/.glance/config.json` for settings.
- `~/.glance/sessions/.../session.json` for saved sessions.
- `~/.glance/sessions/.../conversation.md` for readable conversation export.
- `~/.glance/memories.json` for saved memories.
- `.wav`, `.mp3`, `.png`, and `.txt` artifacts for audio, speech, screenshots, and tool results.

`SessionDirectoryRepository` is responsible for session folders and artifacts. `JsonSettingsStore` is responsible for settings persistence.

## Testing

The project uses Python `unittest` and Node's built-in test runner.

```bash
.venv/bin/python -m unittest discover -s tests
node --test tests/electron_window_control.test.js tests/electron_window_chrome.test.js
bun run typecheck
bun run build
```

The tests cover settings validation, storage, history, live strategy behavior, tool execution, providers, OCR capture, hotkeys, Electron window control, and runtime status sync.

## Results

- Glance can run a full Live turn: listen, detect speech, transcribe or use multimodal audio, call the reply model, run allowed tools, speak the answer, and save the session.
- OCR works as a fast separate workflow for extracting visible text and copying it to the clipboard.
- The tool system is permission based. Disabled tools are not shown to the model.
- The hardest part was keeping the Python runtime and Electron settings UI synchronized while still making Python the source of truth.
- The result is a working desktop agent with persistent settings, history, memories, tests, and a clear structure for adding more tools later.

## Conclusions

Glance achieved the coursework goal by turning an OOP design into a real desktop app. The useful part is not only that it talks to AI models, but that it wraps the model in local services: hotkeys, audio, OCR, tools, memory, storage, and a settings UI.

Future improvements would be app packaging, easier first-run setup, richer tool permissions, and more polished onboarding for provider configuration.
