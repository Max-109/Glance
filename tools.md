# Tools Spec

## Purpose

This file captures the current understanding of the planned `Tools` feature for Glance.

It is a planning and architecture brief, not an implementation file.

The goal is to avoid repeating the current `Capture` problem, where UI exists but the runtime behavior behind it is either missing or misleading.

## Product Goal

Add a real `Tools` system to Glance Live mode.

`Tools` should let the AI improve its answers by using explicitly enabled capabilities such as:

- `take_screenshot`
- `web_search`
- `web_fetch`
- `python_code`
- `computer_use` eventually

The feature must be:

- real, not prompt theater
- settings-driven
- runtime-enforced
- persisted in session folders
- safe enough to evolve without becoming a disaster

## Hard Truths Found In The Repo

### 1. Live mode is currently audio-first and mostly one-shot

The real live path today is basically:

1. capture mic audio
2. send audio or transcript to model
3. get answer
4. generate TTS
5. play TTS

Relevant files:

- `src/services/live_session.py`
- `src/strategies/live_strategy.py`
- `src/services/audio_recording.py`
- `src/services/providers.py`

### 2. The current `Capture` tab is mostly fake

The app exposes settings like:

- `screenshot_interval`
- `batch_window_duration`
- `screen_change_threshold`

Relevant files:

- `components/settings-tabs/capture-tab.tsx`
- `src/models/settings.py`
- `src/ui/settings_viewmodel.py`

But those values are not meaningfully wired into the live execution path that is actually in use.

Conclusion:

- replacing `Capture` with `Tools` is valid
- the next tab must not repeat this mistake

### 3. The repo already has a seam for extra live artifacts

`LiveInteraction` already supports `frame_paths`.

Relevant files:

- `src/models/interactions.py`
- `src/storage/json_storage.py`

That means the data model already hints at storing more than just audio and final speech.

### 4. Session folders already exist and should be reused

Glance already stores session data under `~/.glance/sessions`.

Relevant files:

- `src/services/app_paths.py`
- `src/storage/json_storage.py`

Each session already has:

- `session.json`
- `conversation.md`
- turn artifacts such as audio and images

This is the correct place for tool outputs, screenshots, code, stdout, stderr, and fetch results.

### 5. The current prompting shape is wrong for tools

The provider layer currently expects the model to return the final spoken reply directly, sometimes with a `VOICE_ID:` header.

Relevant file:

- `src/services/providers.py`

That is acceptable for one-shot voice answers.

It is the wrong shape for tool calling.

Tools require an iterative loop:

1. user input
2. assistant decides whether to call tools
3. tools run
4. assistant sees tool outputs
5. assistant gives final answer
6. final answer is shaped for speech
7. TTS runs

### 6. Runtime ownership is already correct

The Python runtime already owns:

- live session control
- audio capture
- persistence
- orchestration

The Electron + Next UI is a settings shell.

Relevant files:

- `src/ui/qt_app.py`
- `src/ui/electron_bridge.py`
- `electron/preload.js`

Conclusion:

- tool execution belongs in Python runtime code
- dangerous execution should not be moved into the settings shell bridge

### 7. Quick and OCR exist in code, but not as real product flows

There are strategy implementations for Quick and OCR, but the tray runtime still reports them as unavailable.

Relevant file:

- `src/ui/qt_app.py`

Conclusion:

- the only real product path today is Live mode
- tool architecture should be designed around Live first

## Core Principle

The `Tools` tab must not work like this:

- enable some toggles
- append a big paragraph to a prompt
- hope the model behaves

That is fake capability.

The correct rule is:

1. settings decide which tools are enabled
2. runtime builds the actual enabled tool list from settings
3. provider receives only the enabled tools
4. prompt adds behavior guidance on top of the hard gate
5. every tool call is persisted

If step 2 and 3 do not exist, the feature is not real.

## Recommended Feature Scope

### V1 should include

- a real `Tools` tab
- persisted tool settings in `AppSettings`
- runtime tool registry
- tool-capable live loop
- tool artifact persistence in session folders
- readable tool visibility in `conversation.md`

### V1 tool set should be limited to

- `take_screenshot`
- `web_search`
- `web_fetch`

### V1 should not ship these as real production tools yet

- `python_code` without sandboxing
- host desktop `computer_use`

## What Should Be Built

## Settings Model

The app should gain real persisted tool settings.

Recommended initial fields in `AppSettings`:

```python
tools_enabled: bool = False
tool_take_screenshot_enabled: bool = True
tool_web_search_enabled: bool = True
tool_web_fetch_enabled: bool = True
tool_python_code_enabled: bool = False
tool_computer_use_enabled: bool = False
max_tool_calls_per_turn: int = 3
```

Notes:

- safe tools can default to enabled behind the master switch
- dangerous tools should default to disabled
- `max_tool_calls_per_turn` should be a real runtime limit, not decoration

## Runtime Tool System

The runtime should gain a real tool subsystem, not ad hoc branches.

Suggested concepts:

- `ToolDefinition`
- `ToolRegistry`
- `ToolExecutor`
- `ToolResult`
- `ToolCallRecord`
- `ToolPolicy`

Recommended package area:

- `src/tools/`
- or `src/services/tools/`

Each tool definition should include:

- name
- description
- JSON args schema
- timeout
- dangerous flag
- executor
- artifact persistence rules

## Live Runtime Behavior

### If tools are disabled

If `tools_enabled` is off:

- do not expose tools to the model
- do not mention tools in the prompt
- keep the existing live answer flow

### If tools are enabled

If `tools_enabled` is on:

- build enabled tool list from settings
- if the resulting list is empty, behave like tools are off
- otherwise use the tool-capable live loop

### Important recommended rule

When tools are enabled, Live mode should become transcription-first.

Reason:

- the current direct audio one-shot path is optimized for immediate final spoken output
- tool use needs intermediate reasoning and intermediate outputs
- forcing tool use through the one-shot speech path will be brittle and messy

Recommended rule:

- tools off: current live behavior can remain
- tools on: transcribe first, then run tool loop, then create final speech output

## Recommended Tool Loop

Suggested runtime flow:

1. capture audio turn
2. transcribe audio to text
3. build conversation history
4. build enabled tool definitions from settings
5. call provider with messages plus enabled tools
6. if assistant asks for tool calls:
7. validate tool name and arguments
8. execute tool
9. persist artifacts and structured tool results
10. append tool result back into the conversation
11. loop until assistant returns final answer or tool limit is reached
12. shape final answer for speech
13. run TTS
14. persist final turn

Pseudo-shape:

```python
transcript = transcription_agent.run(audio_path=recording_path)
messages = build_live_messages(transcript, conversation_history)
tools = registry.enabled_tools_from_settings(settings)

if not tools:
    final_reply = llm.generate_live_speech_reply(
        transcript=transcript,
        conversation_history=conversation_history,
    )
else:
    final_text = run_tool_loop(
        messages=messages,
        tools=tools,
        registry=registry,
        session=session,
        settings=settings,
    )
    final_reply = llm.prepare_speech_text(text=final_text)
```

## Prompt Strategy

## Core rule

Do not put giant tool manuals into the prompt.

The prompt should be short.

Tool behavior should live primarily in code and in the tool definitions.

### The prompt should do only this

- tell the assistant that tools may be used
- tell it to use the minimum number of tools needed
- forbid inventing tool results
- instruct it to answer directly when no tool is needed
- keep the final answer natural and speech-friendly

Recommended tool fragment when tools are enabled:

```text
You may use the available tools when needed to answer accurately.
Use the minimum number of tools needed.
Do not invent tool results.
If a tool fails, either try a sensible fallback or briefly say what failed.
Prefer a direct answer when no tool is needed.
Keep the final answer natural and suitable for speech.
```

### Tool-specific usage guidance belongs in the tool definitions

Examples:

#### `take_screenshot`

- use when the user asks what is visible right now
- use for current-screen understanding
- do not spam repeated captures without need

#### `web_search`

- use for discovery of candidate sources or current information
- use before `web_fetch` when the exact URL is not known

#### `web_fetch`

- use to read a specific URL after search or when the user names the URL directly
- return readable extracted content, not random raw junk

## Session Persistence

## Reuse the existing session folder model

Do not invent another logging system.

Tool data should be stored in the existing session folder structure.

Suggested artifact examples:

- `turn-001-tool-01-screenshot.png`
- `turn-001-tool-02-web-search.json`
- `turn-001-tool-03-web-fetch.md`
- `turn-001-tool-04-python-code.py`
- `turn-001-tool-04-stdout.txt`
- `turn-001-tool-04-stderr.txt`

## Recommended interaction model change

Extend `LiveInteraction` to include tool call records.

Suggested concept:

- `tool_calls: list[ToolCallRecord]`

Each record should contain:

- tool name
- arguments
- status
- started_at
- finished_at
- summary
- artifact paths
- stdout path if relevant
- stderr path if relevant

## `conversation.md` should visibly show tool use

The tool system should not be invisible.

Human-readable session output should include:

- transcript
- tool call summaries
- references to artifacts
- final assistant reply

That matters because the point of the feature is improved capability with observable behavior.

## Tool-by-Tool Recommendations

## 1. `take_screenshot`

Status:

- should ship in v1

Reason:

- directly useful
- replaces the fake value currently carried by the `Capture` tab
- low conceptual risk

Behavior:

- on-demand only in v1
- no passive continuous capture

Suggested args schema:

```json
{
  "type": "object",
  "properties": {
    "reason": { "type": "string" }
  },
  "additionalProperties": false
}
```

## 2. `web_search`

Status:

- should ship in v1

Reason:

- useful for current information and source discovery
- read-only
- low implementation risk

Suggested args schema:

```json
{
  "type": "object",
  "properties": {
    "query": { "type": "string" },
    "max_results": { "type": "integer", "minimum": 1, "maximum": 10 }
  },
  "required": ["query"],
  "additionalProperties": false
}
```

## 3. `web_fetch`

Status:

- should ship in v1

Reason:

- necessary companion to `web_search`
- needed to read actual content instead of just snippets

Suggested args schema:

```json
{
  "type": "object",
  "properties": {
    "url": { "type": "string" }
  },
  "required": ["url"],
  "additionalProperties": false
}
```

## 4. `python_code`

Status:

- do not ship without sandboxing

Reason:

- host Python execution would be reckless
- it gives the model filesystem, environment, and network access unless isolated

If eventually added, requirements include:

- sandbox isolation
- CPU and memory limits
- timeout
- stdout and stderr capture
- source file persistence

Suggested args schema:

```json
{
  "type": "object",
  "properties": {
    "code": { "type": "string" }
  },
  "required": ["code"],
  "additionalProperties": false
}
```

## 5. `computer_use`

Status:

- do not ship as host desktop control in v1

Reason:

- highest-risk tool
- not needed to validate the architecture
- easy prompt-injection bait
- introduces permission and safety complexity immediately

If shown in UI before implementation, it should be:

- clearly marked `coming soon`
- or clearly marked `dangerous`
- disabled by default
- not wired to fake behavior

## Library Recommendations

## Web search

Recommended:

- `ddgs`

Reason:

- maintained current package
- the older `duckduckgo-search` package has been renamed
- lightweight and suitable for v1

## Web fetch

Recommended v1 approach:

- simple extraction path first
- readable markdown or text output
- avoid overbuilding the fetch path initially

### About `crawl4ai`

`crawl4ai` is promising but heavy.

Reasons not to make it the default foundation for v1:

- browser setup overhead
- installation complexity
- slower cold-path execution
- unnecessary complexity for simple fetch cases

Best role for it later:

- optional fallback for JS-heavy or complex pages
- not the default backend for the first working implementation

## Python sandbox candidate

Candidate worth spiking:

- `microsandbox`

Why it looks promising:

- local microVM model
- Python SDK exists in docs
- host-side secret substitution model is strong
- aligns well with local-first runtime expectations

Why it should still be treated as a spike first:

- some features in docs are marked `coming soon`
- it needs real validation for macOS setup pain and runtime ergonomics

Hard rule:

- never run host Python directly for `python_code`

## Security And Safety Notes

## Strong rule

Do not trust the prompt for safety.

Safety must be enforced in code.

### Required hard gates

- disabled tools must not be exposed to the model
- tool names must be validated against the registry
- arguments must be schema-validated
- execution must use timeouts
- failures must be logged and persisted
- dangerous tools must default off

## Electron bridge note

The local Electron bridge is appropriate for settings and UI state.

It should not become the main execution boundary for dangerous tool logic.

Reason:

- it is a settings bridge
- it is not the right place for code execution or desktop automation control

Keep dangerous execution in the Python runtime/orchestrator layer.

## UI / UX Requirements For The Future `Tools` Tab

The `Tools` tab should not just replace `Capture` mechanically.

It should look intentional, premium, and significantly better than a boring list of switches.

### Non-negotiable UI direction

- preserve the current Glance visual language
- do not introduce a random new design system
- use the established shell, spacing, panel structure, icon language, and status treatment
- make the tab feel like a first-class product surface, not a developer debug page

Relevant style reference:

- `UI.md`

### What good UI here means

The tab should feel:

- clear
- premium
- slightly high-agency
- easy to scan
- safe for dangerous capabilities
- pleasant enough that it does not feel like a downgrade from the current shell

### What the tab should not be

- not a raw checklist of toggles with no hierarchy
- not a dense admin panel
- not generic AI-settings slop
- not five equal rows of identical controls and helper text
- not fake futurism

### Recommended visual structure

The `Tools` tab should likely be grouped into panels such as:

#### 1. Overview panel

- master `Enable Tools` toggle
- short explanation of what tools do
- visible status summary, such as:
  - `off`
  - `3 enabled`
  - `safe tools only`

#### 2. Safe tools panel

- `Take Screenshot`
- `Web Search`
- `Web Fetch`

These should feel fast, useful, and low-friction.

#### 3. Advanced tools panel

- `Python Code`
- maybe future `Browser Use`

This section should visually communicate higher complexity.

#### 4. Dangerous or unavailable tools panel

- `Computer Use`

This section should be clearly separated and visually more cautious.

### Recommended interaction behavior

- master toggle should instantly make the whole tab state legible
- per-tool toggles should have meaningful helper text
- unavailable tools should look intentionally unavailable, not broken
- dangerous tools should be visually isolated and harder to enable casually
- if the master toggle is on but no tools are enabled, show a clear empty state

### Recommended premium details

- good icon choice per tool, not decorative clutter
- status pills for `enabled`, `disabled`, `coming soon`, `dangerous`
- subtle hierarchy between safe and risky capabilities
- helper copy that is concise and useful
- compact but elegant spacing
- avoid repetitive toggle rows that all look identical

### Recommended UX copy direction

Good copy is:

- concrete
- direct
- short
- product-like

Bad copy is:

- vague
- inflated
- startup-gimmicky
- overexplained

Example direction:

- `Take Screenshot`: Capture the current screen when Glance needs visual context.
- `Web Search`: Find current sources before answering.
- `Web Fetch`: Read a page after search finds the right source.
- `Python Code`: Run isolated code for calculations or transformation.
- `Computer Use`: Control the desktop directly. Keep off until explicit safeguards exist.

### UX principle for risk presentation

The tab should make safe tools feel approachable.

It should make risky tools feel deliberate.

The UI must communicate:

- what is safe to try now
- what is advanced
- what should stay off

### Final UI rule

The `Tools` tab should look awesome and really good from a UI/UX perspective, but it must still be honest.

Beauty is welcome.

Fake capability is not.

## What Should Not Be Done

Do not do any of the following:

- do not create a nice `Tools` tab with no hard runtime behavior behind it
- do not append a giant paragraph to the prompt and call that implementation
- do not expose disabled tools to the provider anyway
- do not use fake toggles for tools that do nothing
- do not run host Python directly
- do not ship host desktop `computer_use` in v1
- do not mix tool reasoning logic directly into the final TTS-facing prompt
- do not let the UI outrun the runtime again

## File-by-File Implementation Map For Later

This section is for later implementation work, not for this spec-writing step.

### UI routing and tab replacement

- `lib/glance-bridge.ts`
- `components/settings-tab.tsx`
- replace `CaptureTab` with `ToolsTab`

### UI implementation

- create `components/settings-tabs/tools-tab.tsx`
- update `components/settings-page.tsx` default state

### Settings and validation

- `src/models/settings.py`
- `src/ui/settings_viewmodel.py`

### Runtime tools subsystem

- add new tool registry area under `src/tools/` or similar

### Live strategy changes

- `src/strategies/live_strategy.py`
- `src/services/providers.py`

### Persistence changes

- `src/models/interactions.py`
- `src/storage/json_storage.py`

## Recommended phased plan

### Phase 1

- replace `Capture` with `Tools`
- add persisted settings
- add real `Tools` tab UI

### Phase 2

- add registry and tool definitions
- implement `take_screenshot`
- implement `web_search`
- implement `web_fetch`

### Phase 3

- refactor live mode into tool-capable path
- force transcription-first behavior when tools are enabled
- keep final speech shaping separate

### Phase 4

- extend session persistence and `conversation.md`

### Phase 5

- spike `microsandbox` for `python_code`

### Phase 6

- only after the above is stable, revisit whether `python_code` should be exposed
- keep `computer_use` out until real safety design exists

## Final Recommendation

The best version of this feature is:

- replace `Capture` with `Tools`
- make tool settings real runtime gates
- start with safe tools only
- use a real tool registry and tool loop
- force tool-enabled live mode into transcription-first flow
- keep final speech shaping separate from tool reasoning
- persist every tool call and artifact in the existing session folder model
- make the `Tools` tab visually premium and clearly structured without becoming fake UI theater

The worst version is:

- a pretty `Tools` tab
- big prompt text
- no hard runtime gating
- no persistence
- fake toggles
- dangerous tools before the safe architecture works
