<div align="center">
  <img src="./docs/media/glance-mark-mono.svg" width="84" alt="Glance mark" />
  <h1>Glance</h1>
  <p><strong>Press a shortcut. Speak. Get the answer back out loud.</strong></p>
  <p>
    <img alt="Backend" src="https://img.shields.io/badge/backend-Python-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Frontend" src="https://img.shields.io/badge/frontend-Electron%20%2B%20Next.js%20%2B%20Bun-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
    <img alt="Voice" src="https://img.shields.io/badge/voice-Eleven%20v3-%23eaabab?style=for-the-badge&labelColor=3f3f46" />
  </p>
  <img src="./docs/media/showcase.gif" alt="Glance app showcase" width="900" />
</div>

## What is Glance?

Glance is a macOS live agent app that stays out of the way until you need it.

In Live mode, press a shortcut, speak, and Glance records your request, gets a response from the configured model, speaks the answer out loud, and saves the session. In OCR mode, press a shortcut when you need visible text from the screen, and Glance extracts that text and copies it to the clipboard.

## Features

- Customizable shortcuts for Live mode, OCR, and opening Glance.
- Configurable OpenAI-compatible endpoints for reply, transcription, and voice.
- Multimodal audio support when your chosen model can understand audio directly.
- Eleven v3 voice output with multilingual TTS and emotion support.
- TEN VAD audio detection for natural speech turns.
- Optional tools for the live agent, including screenshot, OCR, web search, web fetch, and memory tools.
- Saved sessions with transcript, response, audio, screenshots, and tool records.
- Saved memories that the live agent can read and update.

## Requirements

- macOS.
- Python 3.10+.
- Git or Xcode Command Line Tools, because `requirements.txt` installs TEN VAD from GitHub.
- Bun 1.3.x.
- Node.js 20+.
- Microphone, Screen Recording, and Accessibility permissions in macOS settings.

## Run locally

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

bun install
bun run build

python3 main.py
```

## How to use it

1. Open Glance.
2. Configure reply, transcription, and voice providers in settings.
3. Set the Live, OCR, and Open Glance shortcuts.
4. Choose audio devices and voice settings.
5. Enable only the tools you want the live agent to use.
6. Press the Live shortcut and speak.
7. Press the OCR shortcut when you want visible text copied from the screen.

Settings are saved in `~/.glance/config.json`. Sessions are saved under `~/.glance/sessions`. Memories are saved in `~/.glance/memories.json`.

## How it works

<p align="center">
  <img src="./docs/media/glance-how-it-works.svg" alt="How Glance works" width="900" />
</p>

Glance uses Python for the backend and Electron, Next.js, and Tailwind CSS for the frontend.

| File | What it does |
| --- | --- |
| `main.py` | Opens the desktop app, or CLI mode when `--cli` is used. |
| `src/ui/qt_app.py` | macOS menu bar app, shortcuts, OCR overlay, Live control, and Electron startup. |
| `src/ui/electron_window.py` | Opens the Electron settings window and sends runtime updates to it. |
| `src/core/orchestrator.py` | Connects settings, history, memories, providers, strategies, and clipboard. |
| `src/strategies/live_strategy.py` | Records speech, gets the reply, uses tools when enabled, and plays voice output. |
| `src/strategies/ocr_strategy.py` | Captures the screen, extracts text, and copies it to the clipboard. |
| `src/tools/runtime.py` | Handles tool definitions and tool execution for Live mode. |
| `src/storage/json_storage.py` | Stores settings, sessions, artifacts, and conversation Markdown on disk. |
| `components/` | Electron settings UI built with Next.js and Tailwind CSS v4. |

## Tools

| Tool | Description |
| --- | --- |
| Screenshot | Captures the screen for better context. |
| OCR | Extracts requested text from the screen and copies it to the clipboard. |
| Web search | Searches the web for latest information. |
| Web fetch | Fetches data from a specific URL. |
| Add memory | Saves a task, idea, preference, plan, or project note. |
| Read memory | Searches saved memories. |
| Change memory | Updates a saved memory when you ask to edit or correct it. |

## Development

Run tests and checks:

```bash
.venv/bin/python -m unittest discover -s tests
node --test tests/electron_window_control.test.js tests/electron_window_chrome.test.js
bun run typecheck
bun run build
```

Run Python style checks:

```bash
.venv/bin/python -m pycodestyle main.py src tests
```

## License

See [LICENSE](./LICENSE).
