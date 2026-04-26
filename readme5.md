<div align="center">
  <img src="./docs/media/glance-mark-mono.svg" width="84" alt="Glance mark" />
  <h1>Glance</h1>
  <p><strong>My live desktop agent for fast voice help, OCR, and small useful tools.</strong></p>
  <p>
    <img alt="Status" src="https://img.shields.io/badge/status-coursework%20project-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Python" src="https://img.shields.io/badge/python-OOP%20runtime-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Electron" src="https://img.shields.io/badge/electron-settings%20UI-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Tools" src="https://img.shields.io/badge/tools-user%20controlled-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
  </p>
  <img src="./docs/showcase.gif" alt="Glance app showcase" width="900" />
</div>

## What Is Glance?

Glance is a macOS app that lets me quickly call a live AI agent without leaving what I am doing.

I press the Live shortcut, speak, and get the answer back out loud. If I need text from the screen, I press the OCR shortcut and Glance copies the extracted text to my clipboard.

The app supports configurable OpenAI-compatible endpoints. That means the reply model, transcription model, and voice model can be changed in settings instead of being hardcoded into the project.

## Why It Fits The Coursework

This is not a one-file script. Glance has enough moving parts to show proper OOP:

- data models for settings, sessions, interactions, memories, and tool records
- agents for model-related actions
- strategies for Live and OCR modes
- services for audio, storage, memory, clipboard, providers, hotkeys, and UI bridge
- repositories for file persistence
- tests for the important behavior

## Showcase

The GIF above shows the app UI. The actual app runs from the macOS menu bar. The settings UI is Electron/Next.js, but the main runtime is Python.

## Features

- **Live mode**: speak naturally and get a spoken answer.
- **OCR mode**: extract visible text and copy it.
- **Provider setup**: configure reply, transcription, and voice endpoints.
- **Tools**: let the agent use screen context, web context, and memories.
- **History**: save sessions and readable Markdown exports.
- **Memories**: remember and update notes for later.
- **Audio controls**: choose devices and tune speech strictness.
- **Theme/accent**: uses the app's dark UI and accent color.

## Agent Tools

| Tool | Plain explanation |
| --- | --- |
| Screenshot | Lets the model see the current screen when that helps answer the request. |
| OCR screen | Gets exact text from the screen, copies it to clipboard, and saves the result. |
| Web search | Looks up public current information. |
| Web fetch | Reads one public web page. |
| Add memory | Saves something the user explicitly wants remembered. |
| Read memory | Searches saved memories. |
| Change memory | Edits an existing memory. |
| End Live session | Stops the live session when the user says they are finished. |

## How To Run It

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

bun install
GLANCE_PYTHON=.venv/bin/python bun run dev:desktop
```

Build and run:

```bash
bun run build
.venv/bin/python main.py
```

CLI fallback:

```bash
.venv/bin/python main.py --cli
```

The app needs macOS Microphone, Screen Recording, and Accessibility permissions.

## How To Use It

1. Start Glance.
2. Open settings.
3. Add provider base URLs, API keys, and model names.
4. Pick audio input/output devices.
5. Enable or disable tools.
6. Press `CMD+SHIFT+L` for Live.
7. Press `CMD+SHIFT+O` for OCR.

## Main Files

| File/folder | What it does |
| --- | --- |
| `src/core/orchestrator.py` | Connects the whole runtime. |
| `src/factories/strategy_factory.py` | Creates the correct mode strategy. |
| `src/strategies/live_strategy.py` | Runs Live voice turns. |
| `src/strategies/ocr_strategy.py` | Runs OCR turns. |
| `src/tools/runtime.py` | Defines tools and executes them safely. |
| `src/storage/json_storage.py` | Saves settings, sessions, Markdown, and artifacts. |
| `src/services/providers.py` | Talks to OpenAI-compatible APIs. |
| `src/services/audio_recording.py` | Records speech with TEN VAD. |
| `src/ui/qt_app.py` | Runs the menu bar app and hotkeys. |
| `components/` | Contains the settings UI. |

## OOP Pillars

### Abstraction

The app uses abstract base classes to define behavior:

```python
class BaseAgent(ABC):
    @abstractmethod
    def run(self, **kwargs):
        "Execute the agent's main behavior."
```

This allows different agents to be used through the same idea: call `run(...)`.

### Encapsulation

Objects keep their logic inside themselves. For example, settings validation is inside `AppSettings`, memory logic is inside `MemoryManager`, and tool access rules are inside `RuntimeToolRegistry`.

### Inheritance

The app uses inheritance where shared contracts help:

- `LiveStrategy` and `OCRStrategy` inherit from `ModeStrategy`.
- Model agents inherit from `BaseAgent`.
- Interaction models inherit from `BaseInteraction`.
- `SessionDirectoryRepository` inherits from `AbstractRepository`.

### Polymorphism

The orchestrator does not care if the selected strategy is Live or OCR:

```python
interaction = strategy.execute(execution_context)
```

Both strategies can be used in the same way.

## Composition / Aggregation

The orchestrator is composed from services and agents. It does not record audio, call the model, copy text, save history, and manage tools by itself. It delegates those jobs to smaller classes.

That makes the app easier to understand. If OCR breaks, I know to look at the OCR strategy/service. If history breaks, I know to look at the history manager or repository.

## Design Pattern

Glance uses the **Strategy** pattern for modes.

Live and OCR are different workflows, so they are separate strategy classes. The factory chooses the strategy:

```python
if normalized_mode == "ocr":
    return OCRStrategy(...)
if normalized_mode == "live":
    return LiveStrategy(...)
```

This design keeps mode-specific code out of the orchestrator.

## Reading And Writing Files

Glance persists data to the user's home folder:

- `~/.glance/config.json`
- `~/.glance/sessions`
- `conversation.md`
- `~/.glance/memories.json`
- recordings, generated speech, screenshots, OCR images, and tool result files

This satisfies the file read/write requirement and also makes the app useful after restart.

## Tests

Run Python tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

Run Electron tests:

```bash
node --test tests/electron_window_control.test.js tests/electron_window_chrome.test.js
```

Check/build the UI:

```bash
bun run typecheck
bun run build
```

## Results

- Live mode works as a full speech-to-speech assistant flow.
- OCR mode extracts screen text and copies it to clipboard.
- Tool settings control what the model is allowed to use.
- Sessions and memories are saved to files.
- The app has tests for core Python behavior and Electron window behavior.

## Conclusions

Glance achieved the main goal: a working OOP desktop application that is useful in normal computer work. The design is split into classes for a reason, because the app has different workflows and services that need to cooperate.

Future improvements would be a packaged macOS build, easier provider onboarding, and more refined tool controls.
