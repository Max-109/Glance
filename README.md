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

## Coursework Report

### 1. Introduction

#### What Is The Application?

Glance is my OOP coursework project: a macOS live agent app that stays out of the way until I need it.

The application has two main workflows. In Live mode, I press a customizable shortcut, speak, and Glance records the request, gets a response from the configured model, speaks the answer out loud, and saves the session. In OCR mode, I press a shortcut when I need visible text from the screen, and Glance extracts that text and copies it to the clipboard.

Main features:

- Customizable shortcuts.
- Configurable OpenAI-compatible endpoints for reply, transcription, and voice. A multimodal model can also understand audio and write the reply in one step.
- [Eleven v3](https://elevenlabs.io/docs/overview/models#eleven-v3) voice output, currently the best multilingual TTS model, with excellent voice quality and support for different emotions.
- Advanced TEN VAD audio detection for natural speech turns.
- Tools available for the live agent to use.
- Saved history with transcript, response, audio, screenshots, and tool records.
- Saved memories that the live agent can read and update.

#### How To Run The Program

Prerequisites:

- macOS.
- Python 3.10+.
- Git or Xcode Command Line Tools, because `requirements.txt` installs TEN VAD from GitHub.
- Bun 1.3.x.
- Node.js 20+.
- Microphone, Screen Recording, and Accessibility permissions in macOS settings.

Run the application:

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

#### How To Use The Program

1. Open Glance.
2. Configure reply, transcription, and voice providers in settings.
3. Set the Live, OCR, and Open Glance shortcuts.
4. Choose audio devices and voice settings.
5. Enable only the tools you want the live agent to use.
6. Press the Live shortcut and speak.
7. Press the OCR shortcut when you want visible text copied from the screen.

Settings are saved in `~/.glance/config.json`. Sessions are saved under `~/.glance/sessions`. Memories are saved in `~/.glance/memories.json`.

### 2. Body / Analysis

#### Application Structure

<p align="center">
  <img src="./docs/media/glance-how-it-works.svg" alt="How Glance works" width="900" />
</p>

Glance uses Python as the backend and Electron + Next.js + Tailwind CSS as the frontend.

| File | What it does |
| --- | --- |
| `main.py` | Opens the desktop app, or CLI mode when `--cli` is used. |
| `src/ui/qt_app.py` | macOS menu bar app, shortcuts, OCR overlay, Live control, and Electron startup. |
| `src/ui/electron_window.py` | Opens the Electron settings window and sends runtime updates to it. |
| `src/core/orchestrator.py` | Connects settings, history, memories, providers, strategies, and clipboard. |
| `src/strategies/live_strategy.py` | Records speech, gets the reply, uses tools when enabled, and plays voice output. |
| `src/strategies/ocr_strategy.py` | Captures the screen, extracts text, and copies it to the clipboard. |
| `src/tools/runtime.py` | Tool definitions and tool execution for Live mode. |
| `src/storage/json_storage.py` | Stores settings, sessions, artifacts, and conversation Markdown on disk. |
| `components/` | Electron settings UI built with Next.js and Tailwind CSS v4. |

#### Functional Requirements Coverage

The main runtime path starts in `main.py`, passes through the UI and orchestration layer, and then runs either the Live or OCR strategy.

| Requirement | How Glance implements it |
| --- | --- |
| GitHub usage | The program and Markdown report are kept in one GitHub repository. |
| Python program | The main backend is written in Python and starts from `main.py`. |
| 4 OOP pillars | Abstraction, encapsulation, inheritance, and polymorphism are used in the backend classes. |
| Composition / aggregation | `Orchestrator` is composed from smaller services such as settings, history, memory, providers, strategies, and clipboard. |
| Design pattern | `ModeStrategyFactory` creates the correct workflow strategy at runtime. |
| Reading and writing files | Settings, sessions, conversation exports, memories, audio, screenshots, OCR results, and tool results are saved to disk. |
| Testing | Python unit tests cover the main backend behavior, and Node tests cover Electron window control. |
| Code style | Python coursework code is checked with `pycodestyle` against `main.py`, `src`, and `tests`. |

#### Tools

| Tool | Description |
| --- | --- |
| Screenshot | Captures the screen for better context. |
| OCR | Extracts requested text from the screen and copies it to the clipboard. |
| Web search | Searches the web for latest information. |
| Web fetch | Fetches data from a specific URL. |
| Add memory | Saves a task, idea, preference, plan, or project note. |
| Read memory | Searches saved memories. |
| Change memory | Updates a saved memory when the user asks to edit or correct it. |

#### OOP Requirements

##### Abstraction

The best example of abstraction in Glance is `ModeStrategy`, an abstract class used with the Strategy pattern. The program has two main modes: `live` and `OCR`.

In `live` mode, the user speaks, the program receives an audio file, transcribes it, sends the text to the LLM, and returns the answer as audio. In `OCR` mode, the program receives a screenshot or selected screen area, analyzes it, and extracts the needed text.

```python
class ModeStrategy(ABC):
    @abstractmethod
    def execute(self, context: dict) -> BaseInteraction:
        "Run one mode workflow and return the resulting interaction."
```

These modes receive different data and have different internal logic, but both are started through the same `execute(context)` method. The `Orchestrator` uses `ModeStrategyFactory` to get the correct strategy for the selected mode, such as `LiveStrategy` or `OCRStrategy`, and then runs it.

##### Encapsulation

The best example of encapsulation in Glance is `RuntimeToolRegistry`. This class keeps the logic for deciding which live agent tools are allowed and which ones are blocked.

The user can enable or disable tools globally, and can also allow or deny individual tools such as screenshots, OCR, web search, web fetch, and memories. Instead of making the whole program check those settings directly, the logic stays inside one class.

```python
def get(self, name: str) -> ToolDefinition | None:
    definition = self._definitions.get(name)
    if definition is None:
        return None
    if not self._settings.tools_enabled:
        return None
    if self._policy_for_tool(name) == "allow":
        return definition
    return None

def _policy_for_tool(self, name: str) -> str:
    if name == "web_fetch":
        return self._settings.tool_web_fetch_policy
    return "deny"
```

Other parts of the app only ask `RuntimeToolRegistry` for a tool by name. They do not need to know where every setting is stored or how each policy is checked.

##### Inheritance

Shared base classes are used where the app has several versions of the same kind of object:

- `LiveStrategy` and `OCRStrategy` inherit from `ModeStrategy`.
- `LLMAgent`, `OCRAgent`, `ScreenCaptureAgent`, `TranscriptionAgent`, and `TTSAgent` inherit from `BaseAgent`.
- `LiveInteraction`, `OCRInteraction`, and `QuickInteraction` inherit from `BaseInteraction`.
- `SessionDirectoryRepository` inherits from `AbstractRepository[SessionRecord]`.

##### Polymorphism

The orchestrator can call `execute(...)` without needing separate code for every mode:

```python
strategy = self._strategy_factory.create(mode=mode, ...)
interaction = strategy.execute(execution_context)
```

That works because Live and OCR strategies follow the same interface.

##### Composition And Aggregation

`Orchestrator` is made from smaller services: settings, history, memories, strategy factory, screen capture, transcription, LLM, OCR, TTS, and clipboard.

#### Design Pattern

Glance uses **Strategy** and **Factory Method**.

`LiveStrategy` and `OCRStrategy` are separate workflows. `ModeStrategyFactory` picks the right one at runtime:

```python
if normalized_mode == "ocr":
    return OCRStrategy(...)
if normalized_mode == "live":
    return LiveStrategy(...)
```

This fits better than a Singleton because the app needs replaceable services for tests and runtime settings.

#### File Reading And Writing

Glance stores app data in real files:

- `~/.glance/config.json` for settings.
- `~/.glance/sessions/.../session.json` for saved sessions.
- `~/.glance/sessions/.../conversation.md` for readable conversation export.
- `~/.glance/memories.json` for saved memories.
- Audio, speech, screenshot, OCR, and tool result artifacts.

#### Testing

```bash
.venv/bin/python -m unittest discover -s tests
node --test tests/electron_window_control.test.js tests/electron_window_chrome.test.js
bun run typecheck
bun run build
```

The tests check settings validation, storage, history, Live behavior, tools, providers, OCR capture, hotkeys, Electron window control, and runtime status sync.

For Python style, I use:

```bash
.venv/bin/python -m pycodestyle main.py src tests
```

### 3. Results And Summary

#### Results

- Glance can run a full Live turn: listen, transcribe or use multimodal audio, call the model, use allowed tools, speak the answer, and save the session.
- OCR works as a quick workflow for extracting visible text and copying it to the clipboard.
- The tool system is permission-based, so disabled tools are not shown to the model.
- The application stores useful output, including session metadata, conversation Markdown, screenshots, audio, OCR output, and tool results.
- The main implementation challenge was connecting desktop app behavior, audio processing, model providers, tools, and persistent storage into one stable workflow.

#### Conclusions

This coursework resulted in a working desktop assistant that demonstrates OOP principles in a practical application. The program uses abstract contracts, inherited strategy and agent classes, encapsulated service state, polymorphic workflow execution, composition, file storage, and automated tests.

In the future, I would like to make Glance cross-platform. The Python backend and Electron frontend already make that realistic, but the current macOS-specific permissions, hotkeys, menu bar behavior, and screen capture integrations would need platform-specific handling.
