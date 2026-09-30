# Brainless Agent

## Persistent runtime service

The existing browser-team and one-shot workflows remain available. For a
durable queue that stays alive while idle, use the persistent runtime:

```powershell
# Start the service; it remains in IDLE when the queue is empty.
python run.py runtime start

# Submit work from another terminal.
python run.py runtime submit "Describe the current project architecture" --priority 10

# Inspect service state, queue, workers, or health.
python run.py runtime status
python run.py runtime tasks
python run.py runtime agents
python run.py runtime health

# Request a graceful shutdown.
python run.py runtime stop
```

`python run.py --service` is an alias for `runtime start`. The existing
one-shot behavior is available as `python run.py --once` (or through the
existing `cli` and `browser-team` commands). The service persists tasks in
`data/runtime/service.sqlite3`, recovers tasks that were running during a
previous process interruption as recoverable waiting tasks, limits retries and
execution time, and records a heartbeat and structured task events. It does
not silently modify Windows startup settings; install it as a Windows service
only through an explicit operator-managed service wrapper.

## Coordinated coding workers

The browser leader remains the primary reasoning and authorization layer. Once
it produces a bounded implementation plan, the runtime can use the local
`vscode.*` tools to discover VS Code, Copilot, Codex, Python, and Git, open the
workspace, run allow-listed validation, and persist a coordination packet.
Packets identify the browser leader as authority and can be shared by the
browser team, VS Code Copilot, Codex, and VS Code agents. These workers never
grant themselves permissions or execute arbitrary shell strings; changes still
pass through the repository's normal permissions, validation, and verification
paths.

The VS Code bridge can also open validated workspace files, list installed
extensions, and install or uninstall validated extension identifiers. Extension
changes are high-risk operations and must be explicitly selected by the
browser-authorized plan. VS Code's extension host is not silently controlled as
an unrestricted process; extension-specific behavior requires the extension's
own supported command/API surface.

Use the [installed-browser team](BROWSER_TEAM.md) to discover all supported Windows
browser profiles and let their ChatGPT/Gemini sessions collaborate. Start with
`python run.py browser-team inventory`, then
`python run.py browser-team run "Your task" --setup`.

Brainless Agent is a Python computer-use runtime. It orchestrates a real, persistent Chrome session and uses chatbot **websites** as interchangeable reasoning engines. It does not call OpenAI, Gemini, Anthropic, or another model reasoning API. The optional AssemblyAI key is used only for speech transcription and never grants reasoning or execution authority.

## vNext autonomous computer-agent runtime

Alongside the existing browser-provider workflow, vNext adds a runtime-owned autonomous execution path:

```text
USER -> Root -> capability analysis -> AgentRegistry -> reuse | AgentFactory
     -> AgentSupervisor/ActionRuntime -> observe -> structured decision -> policy/permission
     -> resource lock -> controller action -> observe and verify -> audited result
```

`app/autonomy` is model independent: a decision provider can propose only a typed `ComputerAction`; it cannot access Python, the OS, controller backends, permissions, or tool registration. `ActionRuntime` validates identity, allow-listed tool, permission, global policy, arguments, locks shared resources, executes through a replaceable `ComputerController`, observes again, and verifies expected state. Failures are machine-readable (`PERMISSION_DENIED`, `CAPABILITY_UNAVAILABLE`, `VERIFICATION_FAILED`, and related codes), bounded by step and failure budgets, and logged in runtime audit records.

The production `PlaywrightComputerController` implements real browser observation/navigation and explicitly reports unsupported OS capabilities rather than faking success. OS/browser/filesystem/process adapters remain behind `ToolRegistry`; platform-specific controllers can be added without changing the agent hierarchy. The integration tests use an injected deterministic controller solely to make the full runtime flow reproducible; production actions are never hard-coded workflows.

Agents are configurations, not fixed classes. `CapabilityAnalyzer` derives conservative minimum requirements, `AgentRegistry` reuses an idle compatible agent, and `AgentFactory` validates an `AgentSpec`, parent permission boundary, and registered tool metadata before creation. Parent-owned grants remain the only way to add permissions. `ResourceLockManager` serializes mouse/keyboard/browser/screen resources. Existing `AgentManager` continues to supply hierarchy, lifecycle, pause/resume/retry/termination, parallel independent execution, and persisted event auditing.

### Autonomous runtime test coverage

`tests/test_autonomous_runtime.py` proves dynamic BrowserAgent creation, least-privilege navigation, observation/action verification, registry reuse, denied mouse control, authorized parent grant, and task requirement analysis. Browser, OS, and provider integrations still require the local platform and an owner-authenticated profile.

## Phase 1: working vertical slice

The current implementation is an end-to-end browser-driven MVP:

1. Opens a persistent, visible Chrome profile with Playwright.
2. Navigates to ChatGPT (or selects Gemini/Claude when named in a task).
3. Locates the webpage's semantic prompt element, writes and submits a rendered prompt.
4. Observes generation controls, extracts the rendered assistant response from the DOM, validates it is not empty, prints it, and stores it locally in SQLite.
5. Runs multiple named providers and asks the selected synthesis provider to compare their labelled responses.
6. Uses a logged runtime state machine, bounded response-extraction recovery, action/time budgets, and a cooperative emergency-stop latch.

Each rendered prompt receives a dedicated tab for each selected provider, so ChatGPT and Gemini prompts never
overwrite one another. Claude uses the same flow as an optional best-effort provider: if it fails after another
provider has succeeded, the run continues with the successful results. The application saves only a SHA-256 prompt
identifier and the provider-owned conversation URL in `data/conversation-urls.json`; prompt text is not written to
that index. On the next run, an exact saved conversation URL is restored. Browser windows and tabs stay open for the
life of `run.py` and are closed only as part of application shutdown.

Before an autonomous task is assigned, the dashboard runtime uses a two-prompt agent-planning workflow. Prompt 1
receives the task, required authority, and a metadata-only inventory of existing agents, then proposes reuse or
creation as strict JSON. The runtime independently checks that proposal against the authoritative registry. Only when
no eligible agent exists does Prompt 2 receive the required permissions and registered function descriptions. Its
strict JSON definition is validated against the runtime requirements. The runtime writes and executes a fixed,
data-only Python definition artifact, creates the child through `AgentManager`, assigns exactly the validated tools and
permissions, and then uses the existing audited action/verification loop. Provider-supplied Python is never executed;
it cannot bypass parent authority, tool registration, policy, approval, or verification.

The provider interface and adapters are implemented now so the runtime has no provider-specific branches. Gemini and Claude selectors are included, but their current UIs evolve frequently; verify the configured DOM selectors after logging in. The desktop GUI and bounded DOM/clipboard/OCR response-extraction fallbacks are available now. A system-wide emergency hotkey and visual-anchor discovery remain future work.

### Autonomous capability lifecycle

Missing capabilities can now be handled through the sandbox-first lifecycle in
`app/autonomy/capability_lifecycle.py`. A runtime-owned builder stages a versioned
candidate in an isolated workspace, runs a runtime-owned health check, and only
then makes the typed handler available to `ToolRegistry`. Promotion records an
active version; health failures can mark a candidate unusable and rollback restores
the previous registered handler. Website reasoning may suggest metadata and sources,
but it cannot provide executable Python, install arbitrary packages, or bypass the
registry. Builders and health checks must therefore be explicitly registered by
the deployment, and high-risk capabilities remain subject to the existing policy
and approval gates.

`WebsiteCapabilityDiscovery` connects the authenticated browser provider to this
lifecycle. The provider may research and return metadata, but the runtime rejects
unknown builders, changed tool identities, and non-catalog sources. The
`RuntimeUpgradeManager` provides a separate hash-verified, health-checked,
version-pointer upgrade channel with rollback; it activates a version for the
next process start rather than replacing code inside a running process.

`UniversalTaskRouter` is the automatic entry point for tasks: it checks the
capability broker, asks the configured website provider to acquire a missing
capability, and retries the original task only after the new capability is
validated and promoted. If discovery is unavailable or rejected, the task fails
closed instead of pretending it completed.

The default composition root also registers a trusted `video.edit` builder backed
by a locally installed FFmpeg executable. The adapter uses argument arrays (never
shell strings), confines media paths to its capability sandbox, verifies the
output file, and refuses to start when FFmpeg is unavailable. It is an example of
how additional capabilities become fully automatic: add a runtime-owned builder
and health check, then website research can select only that approved builder.

Visible Windows desktop actions are also project-owned runtime tools in
`app/computer/desktop.py`: `desktop.launch`, `desktop.type`, and
`desktop.calculator`. They are allow-listed, permission-gated, and invoked
through `ToolRegistry`; they are not ad-hoc scripts outside the application.

The declarative catalog in `app/autonomy/automation_catalog.py` contains 100
automation definitions across desktop, browser/internet research, files,
video/FFmpeg, Blender, and Unreal Engine. Each entry declares its objective,
required tool, external dependency, and is available to the website reasoning
planner as structured metadata. Entries requiring Blender, Unreal, or FFmpeg
remain dependency-gated until that software is installed and a corresponding
trusted adapter is registered; the runtime never reports those tasks as
completed without verified output.

Trusted Blender and Unreal adapters are registered by the application composition
root. Blender operations use a fixed allow-list and invoke the installed Blender
binary with a runtime-generated operation script; Unreal operations use the
installed Unreal Editor with a fixed allow-list and an editor Python bridge.
Both adapters reject paths outside their capability sandbox and report a missing
executable instead of claiming success. Multi-step work is represented as
consecutive catalog operations, so a website reasoning plan can compose
`create_scene -> add_cube -> add_light -> render` or
`open_project -> create_level -> add_camera -> save -> verify`.

The Blender adapter supports general website-planned automation, not only cars.
ChatGPT may choose from a fixed runtime-owned operation vocabulary covering
scene reset, cube/sphere/cylinder/cone/torus/plane primitives, camera and area
lights, transforms, beveling, smooth shading, materials, rendering, exporting,
and the trusted car helpers. The runtime validates every operation and JSON
argument, rejects code/shell commands and unsafe paths, then executes the
validated plan in visible Blender. The older car workflow remains available as
one example of this general mechanism; render/export outputs are checked before
success is returned.

The catalog can also be executed sequentially through the project itself:

```powershell
python run.py catalog list
python run.py catalog execute --arguments catalog-arguments.json
```

The arguments file is a JSON object keyed by automation ID. Every item is
submitted individually through `AgentManager` and the runner prints
`completed`, `failed`, `blocked`, or `needs_input`. Unregistered tools,
missing external applications, missing inputs, and failed verification are
reported explicitly; the runner never invokes a handler directly or turns an
unavailable automation into a success.

## Architecture

```text
CLI -> AgentRuntime -> State/Prompt/SQLite Memory -> Provider Registry
    -> Provider Adapter -> BrowserManager -> persistent Chrome -> chatbot website
```

### Hierarchical agents and tools

The runtime also provides a local, typed `AgentManager` for work that benefits from delegation. A root agent creates child agents with an explicit task, narrowly scoped context, permissions, and tool allow-list. Child permissions must be a subset of their parent's permissions; a tool is only invoked after the registry verifies both the allow-list and every required capability. Global policy can auto-approve, require human approval, or deny sensitive capabilities.

```text
USER -> ROOT AGENT -> AGENT MANAGER
                         |- Research child -> browser.read tool
                         |- Coding child   -> explicitly granted tools
                         `- Testing child  -> explicitly granted tools
```

Agent events record task, status, result, error, tool, and permission-denied outcomes. Independent children can run concurrently, and a parent can inspect the tree, collect results, retry bounded failures, pause, resume, or terminate direct children. The provider websites remain the reasoning layer; agent orchestration and tool permissions remain in Python.

Agents can also be assembled from validated declarative building blocks in Python, created from the authenticated **Agents** dashboard page, or submitted to a running dashboard with `python run.py agent create`. See [the complete agent-building guide](AGENT_BUILDING.md) for the schema, examples, CLI flags, dashboard workflow, and least-privilege checklist.

The runtime observes after navigation and before sending input. Provider adapters use DOM/accessibility locators instead of fixed screen coordinates. If a login, CAPTCHA, 2FA, or another security challenge is detected, the run stops and tells the user to complete it manually. The project never captures passwords, exports cookies, or attempts to bypass a security mechanism.

### Generic browser automation

Generic site automation is a separate layer from `NativeWebsiteClient`: the
native client remains restricted to ChatGPT/Gemini, while `BrowserClient`
provides owned tabs, structured observations, HTTPS-only navigation, and
validated data-only actions. `BrowserPlanner` converts a goal and one
observation into a single structured action; `BrowserAgent` then observes,
executes that validated action, and observes again. Page observations are
untrusted data; the planner is instructed to ignore embedded page commands and
cannot supply executable JavaScript. External form
submissions require both an explicit confirmation callback and the
`browser.external_action` permission.

The Playwright `BrowserManager` exposes `browser_client()` after `start()`.
`BrowserFleet.browser_client()` is available when its Playwright Chromium leader
is enabled; it creates separate tabs and never repurposes the provider tabs.
Native installed-profile windows remain provider-only until a generic DOM
transport is added. `BrowserSessionStore` persists only HTTPS tab metadata and
can restore recorded tabs; it does not replace the provider-only
`NativeSessionStore`.

Initial domain wrappers are in `app/skills/`: `GenericWebSkill` for navigation,
page extraction, and bounded same-origin crawling; `YouTubeSkill` for observed
search/recommendation/player controls; and `GmailSkill` for visible-page
reading and confirmed compose/send.
The crawler follows only visible HTTPS links on the starting origin, skips
obvious state-changing routes, and enforces limits of 50 pages, depth 5, 20,000
characters per page, and 250,000 characters total. `BrowserPlanner` can return
a crawl request and `BrowserAgent` executes it through this skill; the returned
page text remains untrusted data and is never executed as instructions.
The Gmail wrapper does not bypass sign-in or human verification, and its send
operation requires explicit user confirmation plus the external-action
permission. These wrappers are building blocks; the existing voice mission
runtime and its profile-aware Gmail flow remain unchanged.

## Web Command Center

Run the authenticated, read-mostly operations dashboard with a local token:

```bash
BRAINLESS_DASHBOARD_TOKEN="replace-with-at-least-16-characters" python run_dashboard.py
```

Open `http://127.0.0.1:8765` and enter the same token. The responsive, keyboard-accessible dark operations dashboard renders authoritative mission, task, agent, action, resource, event, world-model, inventory, approval, and component-health projections. Its desktop sidebar collapses into a mobile navigation drawer, dense runtime tables remain horizontally navigable on tablets, and status colors always include readable text labels. Press `/` to focus structured global search. It uses authenticated JSON endpoints (`/api/system`, `/api/health`, `/api/events`, `/api/search`), an SSE replay stream (`/api/stream`), and an authenticated command endpoint (`/api/commands`). It never imports or invokes computer tools. Commands are allow-listed by `RuntimeCommandGateway`, authorized with constant-time token comparison, applied to runtime-owned mission/takeover services, and emitted back as correlated events.

The dashboard event bus retains a bounded 2,000-event in-memory replay window with monotonically increasing sequence IDs and backpressure, backed by retained SQLite event history. Mission, task, agent, action, and trigger history comes from existing durable stores; unsupported health integrations are shown as `unknown` or `not_configured`, never synthesized. On reconnect, the client fetches a fresh authoritative snapshot before requesting events after its last sequence. When a reasoning provider is configured, the standalone command center composes a least-privilege runtime task graph and executes it with `TaskEngineMissionRunner` through `AutonomousTaskEngine`; without a provider, mission execution is accurately reported as `not_configured`.

Runtime agent and action records are incrementally bridged into correlated dashboard events. The Analytics page uses real terminal mission/task, action audit, retry, intervention, agent failure, and approval records. A rate displays `N/A` when no valid denominator exists rather than inventing a score. Mission execution runs in supervised mode: medium/high-risk actions create metadata-only durable approval requests, wait without acquiring resources, and resume only after an authenticated dashboard decision passes through `ApprovalSystem`. Action arguments and sensitive text are never written to the approval store.

The dashboard builds an authoritative task-to-mission index from persisted mission graphs and uses it to correlate agents, action audits, and events that carry only a task ID. Selecting a mission opens a drill-down with its objective, policy, acceptance criteria, constraints, task graph, assigned agents, and correlated event timeline. Correlation is a read-only projection: it never rewrites event, agent, action, or mission records.

`AutonomyGovernor` is the final deterministic mission gate before mode policy, permissions, resources, and tool execution. `RuntimeMissionComposer` registers mission-scoped task IDs and least-privilege contracts containing allowed tools, allowed permissions, forbidden actions, confidence thresholds, and action/failure budgets. High-risk contracted actions require independent approval; exhausted budgets and out-of-contract authority are denied. Mission drill-downs expose the contract and real budget consumption. The reasoning provider cannot register contracts or make governor decisions.

`ActionRuntime` also treats an action ID as single-use for the lifetime of a runtime process. A duplicate delivery returns the original result without acquiring resources or repeating side effects. Restart recovery remains checkpoint-driven: it re-observes and verifies environmental state rather than blindly replaying an action.

Temporary capabilities use `CapabilityLeaseRegistry`. A parent may lease only authority it already possesses, to a direct child, for that child's current task, for at most 24 hours. Tool execution accepts an active matching lease in place of a permanent permission; revocation, expiry, task reassignment, or process restart fails closed. The dashboard shows active lease metadata and expiry times but cannot issue leases.

### Dashboard security and deployment

The server binds to loopback by default. Put it behind an authenticated TLS reverse proxy for remote access and rotate `BRAINLESS_DASHBOARD_TOKEN` operationally. Read endpoints and SSE require the token; mutation requests are schema-limited, size-bounded, authenticated, and routed through the runtime command gateway. Responses add restrictive framing, content-type, referrer, browser-permission, and content-security headers. Sensitive argument and state keys are recursively redacted. The dashboard cannot grant permissions, execute tools, write WorldState, or contact a reasoning provider.

Architecture: `Browser UI -> authenticated dashboard API -> runtime projections/command gateway -> mission/operator policy -> existing validated ActionRuntime`. Runtime events flow back via `AutonomousEventBus -> bounded replay -> SSE -> browser`.

### Voice control with AssemblyAI Streaming v3

Installed-browser profile selection, persistent overlay status, and current-page
OCR follow-ups are available through the governed voice runtime. See the
[external browser guide](EXTERNAL_BROWSER.md) for the voice flow and OCR setup.

Install dependencies, set `ASSEMBLYAI_API_KEY`, and select a bounded activation mode in `.env` or the process environment. Voice is disabled when the key is absent. The default `push_to_talk` mode does not open a microphone automatically; `voice_active` and `voice_session` start a microphone session with the Command Center. Audio is 16 kHz mono PCM16 and is streamed through the AssemblyAI Python SDK's v3 streaming client using `universal-3-5-pro` by default.

```bash
export ASSEMBLYAI_API_KEY="your-key"
export VOICE_MODE="voice_session"
BRAINLESS_DASHBOARD_TOKEN="replace-with-at-least-16-characters" python run_dashboard.py
```

The voice flow is `Microphone -> finalized speech parts -> complete-request confirmation -> clarification/planning -> governed mission runtime`. Describe the task across pauses. After 1.5 seconds of silence following a finalized part, the overlay asks whether you want to add anything. Say **yes** and continue, or **no** / **that's all** to analyze the collected request once. Partial speech and silence never execute a task. Low-confidence parts must be repeated. Unsubmitted speech stays in memory and is cleared by **Stop voice** or **start over**.

Answers to specific questions, browser profile choices, and permission prompts continue their current flow directly. A **no** in a permission prompt denies that action; it is separate from completing a task description. Explicit stop, pause, takeover, resume, and status controls use a bounded local control path; contextual **continue** answers the current clarification or permission question. A new ordinary task begins a fresh collection without replaying previously submitted speech.

The browser LLM receives a task-scoped catalog of registered functions and exact argument schemas. The runtime validates and executes the proposed sequence through normal permission, approval, and verification checks. Reasoning providers can fail over in configured order. Malformed plans receive one correction attempt; if planning still fails, the assistant asks for clarification. Provider output, webpage text, and OCR never grant permissions or execute functions directly. The executable inventory comes from `ToolRegistry`, not the Python-method index in `FUNCTION_INVENTORY.md`.

Browser tasks ask for an installed profile or the managed browser. Follow-ups read the current page and reuse its tab. Gmail requests reuse a selected installed profile or ask for one once. The governed `gmail.open` action opens that profile's Gmail website before the agent collects remaining recipient or content details. Opening permission is distinct from the high-risk `gmail.send_email` approval. The selected profile and current email details survive a recoverable opening failure. Send success requires Gmail's confirmation; check Sent before retrying an uncertain send.

Press **Start listening** to connect the microphone and **Stop voice** to disconnect. Releasing the mouse does not end the conversation. The configured session limit still applies; the `push_to_talk` configuration remains a manually started session with an idle timeout, extended while awaiting a clarification. Hands-free modes listen until their session limit or Stop. The overlay stays visible with the current question or status. The dashboard shows collected-part count, pending completion, active mission, and command history.

`VOICE_COLLECT_TASKS=true` enables collection by default; `VOICE_TASK_PAUSE_SECONDS=1.5` sets the pause interval. Use `VOICE_COLLECT_TASKS=false` for legacy immediate finalized-turn routing. Requests are bounded to 2,000 characters. Raw audio persistence is unsupported. Transcript storage defaults off; configured retention and credential redaction apply to stored command metadata. ASR turn IDs are scoped to each connection, and shutdown cancels pending collection and reasoning.

The authenticated Voice page accepts an AssemblyAI key for the current process through **Configure AssemblyAI**. The write-only configuration plane keeps the key out of snapshots, events, and voice history. Alternatively set `ASSEMBLYAI_API_KEY` for startup configuration. `not_configured` means no key was supplied; microphone errors require checking the OS input device and installed SDK audio dependencies. See [EXTERNAL_BROWSER.md](EXTERNAL_BROWSER.md) for the full browser and email flow, and [PERMISSIONS.md](PERMISSIONS.md) for spoken consent and remembered grants.

### Multimodal perception architecture

The runtime now has an on-demand `MultimodalPerceptionEngine` above the existing computer controller observation boundary:

```text
Voice / authenticated dashboard / agent request
                    |
             PerceptionRequest + capability scope
                    |
 Controller / accessibility / DOM / visual providers
                    |
        immutable PerceptionObservation records
                    |
             PerceptionFusionEngine
                    |
             EnvironmentSnapshot
                    |
       WorldStateManager + structural events
                    |
       semantic grounding -> proposed action
                    |
 governor -> policy -> permission -> tool -> execution
                    |
             observation -> verification
```

`PerceptionSource` is provider-independent. The production launcher currently installs `ComputerControllerSource`, which adapts the real active controller's read-only `observe()` method; accessibility, DOM, OCR, or visual-understanding adapters can be registered when their platform integration is available. Missing sources and screenshots are reported as unavailable rather than fabricated. Agent requests are checked against permissions held by the authoritative `AgentManager`, and fields outside the requested capability scope are removed before fusion. The engine serializes observations to avoid stale-state races, continues in a visible `degraded` state when one of several sources fails, records observed application/window/browser/UI identifiers in the existing `WorldStateManager`, measures actual perception latency, and emits structural `environment_observed`, drift, `perception_source_failed`, and `human_required` events. Capture is active and on demand rather than an unconditional screenshot loop.

`ScreenGroundingEngine` resolves text, roles, ordinals, and spatial relationships against `UIElement` records. Accessibility and DOM evidence outrank application, OCR, visual, and controller-text evidence. A coordinate is derived only from the selected semantic element's current bounds; an unresolved or equally ranked ambiguous target fails closed. Existing `TargetResolver.resolve()` remains backward compatible, while `resolve_environment()` uses normalized multimodal state.

Observed webpage, DOM, OCR, voice-context, and screenshot content is always labelled **untrusted observation data**. `MultimodalCommand` rejects screen-originated executable intent, and `ContextBuilder` sends only bounded relevant elements and history. Perception providers have no execution method, tool registry, permission mutation, or agent factory. Shared redaction removes credential-bearing keys and values from dashboard projections, events, and durable voice metadata. CAPTCHA, MFA, security-key, biometric, identity, and payment-confirmation indicators emit `human_required` and enter user-takeover mode; no bypass is attempted.

The dashboard **Perception** page provides an authenticated **Observe now** control, real source/latency/confidence counts, active application/window/browser state, structured UI elements, and the `OBSERVE → UNDERSTAND → TARGET → ACTION → OBSERVE → VERIFY` trace. The browser receives projections only and cannot capture a screen or invoke a controller directly. Filesystem paths backing screenshots are never projected; image retrieval is separately authenticated, restricted to the runtime's `screenshots` and `data` roots, size bounded, and marked `no-store`.

Voice approval fails closed by default because speech transcription does not establish speaker identity. Spoken approval can be enabled only by injecting an independent `approval_authorizer`; otherwise the runtime directs the user to the authenticated approval center. Voice configuration also rejects non-finite confidence values and unbounded session settings. Microphone and AssemblyAI teardown failures still produce a clean stopped state, and a paused or disconnected push-to-talk session can reconnect without leaving a zombie listener.

### Automation readiness guarantees

Explicitly paused missions are inert: background events cannot re-observe or restart them until an authenticated dashboard or authorized voice-resume transition changes them back to `waiting`. The operator dispatches consumed runtime events to the persisted trigger engine, so event and mission triggers share the same authoritative event path instead of relying on a second polling implementation. A voice resume both releases takeover and emits mission wakeups for paused user-blocked work.

Event details are redacted before entering either the in-memory history or SQLite event store. Action arguments, outputs, errors, mission failure checkpoints, voice records, and dashboard projections use the same credential-aware redaction boundary, preventing observed password/token material from being fed back to a reasoning provider through action results. This redaction complements—rather than replaces—tool permissions, policy, approvals, mission contracts, and verification.

## Installation

For a complete Hinglish setup guide—including virtual environments, dashboard/voice configuration, persistent Google Chrome login, automation checklist, and troubleshooting—see [`run_project.md`](run_project.md).

Requires Python 3.11+ and an installed Google Chrome/Chrome-compatible browser.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
playwright install chromium
```

`channel: chrome` in `app/config/providers.yaml` asks Playwright for the installed Chrome channel. If Chrome is not installed, install it or change the channel to a supported locally installed browser.

## First-run Chrome setup

Run the application once, let the visible Chrome window open, and manually sign in to the service(s) you own. The profile is retained at `data/browser-profile`; it is local-only and gitignored. Do not point it at a profile that is currently open in another Chrome process. Do not put credentials in this repository.

## Run

```bash
python run.py                 # browser team across installed profiles; prompts for a task
python run.py cli             # same browser-team entry point
python run.py single-browser  # legacy managed single-browser CLI
python run_dashboard.py       # authenticated Command Center
```

The CLI normally submits a task to the selected chatbot website and prints its advisory response.
Email requests use a guided browser workflow: the chatbot must return bounded JSON steps, missing
values are requested in a native popup (with terminal fallback), Chrome is reused when already open,
and semantic controls are used to operate the authenticated Gmail website. The final Send click
requires explicit confirmation. Successful workflows persist only structural labels and host names;
recipients, message bodies, answers, credentials, selectors, and coordinates are not learned.

Dashboard voice email tasks use a focused browser-LLM-assisted flow instead of the general
multi-provider task planner. The active browser LLM selects or clarifies a discovered installed
browser/profile, then the runtime launches an owned window in that profile and opens Gmail using
Windows accessibility controls (not the browser-team's ChatGPT/Gemini tabs). The same active LLM
asks only for essential missing details, generates the subject and message body from the user's
stated intent, and does not ask the user to dictate them. Each email turn uses one active browser
LLM, without cycling through ChatGPT/Gemini/Claude for routine clarifications. Sending still
requires the runtime's high-risk approval and a positive Gmail confirmation. If the send click may
have happened but Gmail confirmation is missing, check the account's Sent folder before retrying.
Profile discovery reads browser/profile metadata only; it does not inspect saved credentials or history.

The autonomous task engine has a continuous, evidence-driven learning loop. Every run through
`run_with_learning` records its verified outcome, reuses an existing candidate instead of creating
duplicates, recalculates success and verification metrics, and promotes a repeatable candidate to
`tested` only after the configured minimum number of successful runs. Human approval is still
required before activation; later outcome regressions deprecate an approved skill. Learned steps
remain advisory and are revalidated against current tools, permissions, contracts, and environment
before every reuse.

When no `BRAINLESS_DASHBOARD_TOKEN` is configured, `run.py` generates a cryptographically random per-run token and prints it to the local terminal. The Perception page can accept an explicit owner-labelled desktop rectangle (for example, “Search box” or “Continue button”); the selection becomes non-executable perception evidence and still passes through normal target resolution, policy, permission, execution, observation, and verification boundaries.

The Perception page also shows real desktop-window inventory with active, normal, minimized, maximized, and fullscreen states when native enumeration is available. Window-state collection currently uses PyGetWindow's supported Windows backend; other platforms remain explicitly unavailable rather than reporting guessed state.

### Capability-first personal agent

Before accepting a specialized objective, the runtime capability broker checks its registered tools and reusable agents. For example, a video-editing request requires a real `video.edit` capability; generic mouse/process access is not misrepresented as a video editor. If no compatible local agent or tool exists, the requested mission is safely paused and a separate browser-research mission is created to compare free/open-source local options. Discovery is constrained to research: it cannot install software, create an account, purchase a service, upload private media, or execute an external agent. A discovered option becomes usable only after a real adapter is registered and the normal permission, governor, approval, and verification checks pass.

### Desktop UI

Run `python run_gui.py` to launch the Tk desktop UI. It provides a task editor, provider checkboxes, strategy and prompt-profile selectors, Start, cooperative Pause/Resume, Emergency Stop, current status, an in-window result/error log, and a refreshable local task-history table. The browser closes after each GUI run while the persistent profile remains for the next run. Pause takes effect at the next action boundary. Emergency Stop cancels the in-flight browser operation and records the failure state; it does not bypass, dismiss, or otherwise alter provider security pages.

When a provider shows login, CAPTCHA, 2FA, or another security challenge, Brainless pauses without attempting a bypass. Complete the challenge yourself, then press **Continue after login** in the GUI or Enter in the CLI; the runtime verifies the page again before it sends a prompt.

At the prompt, enter a task such as:

```text
Research resilient browser automation patterns.
```

Mentioning more than one configured provider (for example, `compare chatgpt and gemini`) activates deterministic multi-provider task parsing. In the desktop UI, selecting more than one provider also creates a multi-provider workflow when Strategy is **automatic**. The runtime collects labelled answers and sends them to its selected synthesis provider (ChatGPT when selected, otherwise the first selected provider) for a final result.

## Configuration and prompts

Provider URLs, persistent profile location, browser behavior, and bounded runtime limits are in `app/config/providers.yaml`. Prompt templates live in `prompts/<profile>/default.txt`; an optional `prompts/<profile>/<provider>.txt` overrides the default for one provider. Templates support `{task}`, `{previous_results}`, `{provider}`, `{context}`, and `{requirements}`. The runtime retrieves bounded, keyword-matched local context before the first provider prompt. The parser deterministically selects `research`, `coding`, or `analysis` today.

## Adding a provider

Create an adapter subclass of `ChatbotProvider`, give it webpage input/response/stop selectors, and add it to `ProviderRegistry.from_settings`. The agent runtime does not need to change. Test it against the provider's normal browser UI while logged into your own account.

## Local memory

Each completed or failed provider interaction is recorded in `data/memory.db` with task ID, timestamp, provider, prompt, response/status, duration, workflow, errors, and a screenshot path when capture succeeds. Existing databases are migrated in place to add screenshot metadata. `SQLiteMemory.search()` provides local keyword retrieval for later prompt context; no task content is sent to an API by this program.

## Safety and troubleshooting

* You retain control of the visible browser. Stop the process with `Ctrl+C`; the persistent browser context closes cleanly.
* Complete login, CAPTCHA, and 2FA manually. The runtime will not bypass them.
* If an input is not found, inspect the provider website after login and update the adapter selector list. Website DOMs can change.
* Browser actions are bounded by config timeouts and recovery retries; failures are recorded in SQLite.

## Roadmap

Normal response extraction is DOM-first. If its bounded recovery fails, the runtime tries the provider's visible response Copy control plus the local clipboard, then uses local OCR on a recorded screenshot. Every candidate is validated before it can be persisted. OCR requires the optional local Tesseract executable in addition to the Python dependencies.

Next phases add authenticated browser integration tests, provider-specific selector maintenance, visual-anchor discovery, a global emergency hotkey, and task-history controls in the desktop UI.

## Tests

```bash
pytest
```

These tests cover configuration, prompt rendering, local SQLite memory, state transitions, bounded recovery, provider registry behavior, and deterministic task parsing. Browser UI automation remains a manual integration test because it requires the owner's logged-in Chrome session.

### Verified autonomy building blocks

The autonomous runtime now maintains a versioned `WorldStateManager`. Controller observations become evidence-backed facts marked **observed**, **inferred**, **assumed**, or **stale**; tool return values do not update the world model. `ActionContract` optionally supplies runtime-checked preconditions, expected observed effects, retry idempotency, risk metadata, and rollback information. `TargetResolver` is provider-based and uses observed text only as a confidence-scored fallback, never blindly preferring coordinates.

`TaskGraph` and `TaskScheduler` provide validated dependencies, conflict-aware runnable selection, retries, cancellation states, and safe replanning primitives. `ResourceLockManager` uses globally ordered locks, bounded waits, inspectable ownership, and failure cleanup. `CheckpointStore` writes atomically and intentionally requires a fresh environment observation before a resumed action can be executed. `RecoveryEngine` classifies permission, verification, and validation failures and refuses blind retry of non-idempotent actions.

### Task-graph execution and recovery

`AutonomousTaskEngine.run_graph()` executes a validated, mutable dependency graph through the existing agent factory/registry and `ActionRuntime`. It only schedules dependency-ready, non-conflicting work, keeps partial/blocked results explicit, and evaluates supplied `GoalCriterion` acceptance criteria after the graph finishes. The backward-compatible `run()` path is retained for current callers.

Planning context is deliberately scoped: `TaskContextManager` supplies only observed facts and declared permissions to child work; external webpage/document content remains labelled untrusted data and cannot change policy, permissions, identity, or tool grants. `PlanValidator` rejects cyclic graphs, unavailable capabilities/permissions/tools, missing action contracts, and ungated high-risk tasks before execution.

Contracts can set an execution timeout and retry idempotency. A safe retry is always preceded by a fresh controller observation; non-idempotent verification failures select re-observation rather than repeating the action. Checkpoint resumption likewise calls an observer before returning pending work and never replays actions by itself.

`ActionRuntime` writes structured action/observation/verification journal records when given the existing SQLite journal store. `AutonomousTaskEngine` can receive a `CheckpointStore`; it snapshots graph status, retries, agent permissions/statuses, WorldState values, resource ownership, and pending nodes at plan creation and after each task transition. Restart code must call `CheckpointStore.resume(observer)`, which returns a newly observed environment alongside pending work rather than replaying an action.

### Controlled experience and skills

`app.learning` is a durable, advisory layer separate from execution. `ExperienceMemory` stores only structured runtime or human-approved execution outcomes and rejects externally sourced content; retrieval ranks goal/task/environment overlap and treats results as planning suggestions. `SkillRegistry` keeps versioned workflow definitions candidate-first: a skill cannot be registered as verified/trusted, and `SkillEvaluator` can reject a regressing candidate without changing the previous verified version. `WorkflowSynthesizer` turns discovered skills into a `TaskGraph`; the existing plan validator and action runtime remain responsible for permissions, contracts, resources, approval, execution, and verification.

`LearningCoordinator` is the integration point for the experience-to-workflow loop: it persistently records verified runtime outcomes, produces candidate skills only from reusable structured workflows, then retrieves experience and verified skills for a later related goal. `SkillSandbox` statically validates candidate workflow permissions, capabilities, tools, contracts, and high-risk approval requirements with the existing `PlanValidator`; it cannot execute a skill or activate it.


### Connected village construction checkpoints

New runs divide construction into world, block ground, east/west and north/south
gully roads, drainage, and individual objects. Each house or villa has separate
foundation, south/north/west/east wall, roof, and entrance checkpoints, followed by
refinement. Doors, stairs, gates, scenery, lighting, and rendering also receive
execution checkpoints.

The workspace stores `checkpoint.json`, numbered `.blend` scenes, and geometry
reports under `connected-villages/<objective hash>/`. Run the same objective again
to resume. Completed scenes are hash-verified; missing or changed output is rebuilt
from the last verified scene. Older checkpoints retain the original sequence for
started districts and use component stages for unstarted districts.

Planning retries invalid responses and uses validated defaults when necessary.
Invalid area plans fall back to a sparse two-home layout. Execution retries up to
three times from the preceding scene, discarding only uncommitted output. Render
retries halve samples and resolution within configured minimum bounds; actual
settings are recorded in the checkpoint. Progress reports recovery and reduced
quality. Persistent failures retain the pending job and error for the next run.
Explicit review pauses, permission failures, cancellation, and incompatible
checkpoint contracts are not overridden. Recovery cannot guarantee completion
when Blender, storage, or the planning service remains unavailable.


### Village projects and repeated user updates

The village CLI now keeps a stable project ID and a SQLite database at
`data/village-workspace/village-projects.sqlite3`. It records queued requests,
revision plans, errors, completion states, events, and checkpoint snapshots.
The original scenes remain available when a revision is created. A process lock
allows one worker per project while another terminal can submit requests.

New projects prioritize final rendering: 256 Cycles samples and at least 2560px
width, adaptive sampling and denoising, procedural material variation, bevels,
and physically based lighting. Existing lower-budget projects receive a separate
final-quality pass. These controls improve procedural output; detailed assets and
visual art direction are still needed for a cinematic result. GTA6 visual parity
is not a verified completion criterion.

After a run the CLI accepts another natural-language update. You can also use the
project ID printed at startup from another terminal, in the `Brainless_agent`
directory:

```powershell
python run.py village update PROJECT_ID "Set the sunlight angle to 35 degrees"
python run.py village update PROJECT_ID "Increase wall weathering and roof detail in area-0-0"
python run.py village status PROJECT_ID
python run.py village resume PROJECT_ID
```

Queued updates run after the current revision finishes. Supported updates include
render settings, sun elevation, replacement district object layouts, and object
refinement. The planner checks each proposed change against existing district IDs,
footprint contracts, and numeric bounds. A revision copies the verified checkpoint
prefix and rebuilds from the earliest affected stage: lighting changes reuse
geometry, and object refinements preserve preceding components. Requests requiring
unsupported controls or unavailable assets remain `needs_input` with an explanation.

SQLite restores missing or changed checkpoint metadata. Damaged Blender artifacts
are rebuilt from the preceding verified scene. Execution retries are bounded, and
persistent errors remain `failed` with resumable state. A recovery render below the
requested budget is `needs_attention`, not a successful final-quality render;
submit a render retry when resources allow. Validation checks geometry and output
integrity, not a rendered image's aesthetic quality. User pauses, permission checks,
and cancellation remain effective.


### One-session live 3D modelling

See [MODEL_WORKFLOW.md](MODEL_WORKFLOW.md) for the general 3D workflow. Products,
robots, interiors, buildings and cities use a named-object operation planner;
villages keep the district hierarchy. Both use one continuing ChatGPT tab and one
visible Blender worker across checkpoints and revisions. The viewport animates
primitive transforms and reveals district components in sequence. This is visible
scripted modelling, with bounded operations, not mouse impersonation.

Use `python run.py 3d update PROJECT_ID "request"`, `3d status PROJECT_ID`, and
`3d resume PROJECT_ID` for any supported 3D project. Updates also work interactively
after a revision completes. The `village` management commands remain aliases. The
live worker can reconnect after a CLI restart and reload a verified scene after a
Blender interruption. Heavy builds and final rendering can temporarily block UI
refresh; uninterrupted real-time performance is not guaranteed.


### Chat rollover and related-task recognition

Long modelling sessions now replace the active project chat at a completed-turn
boundary after 20 prompts / 100k characters, or after detected composer lag. The
next chat receives a compact checkpoint summary; unrelated tabs stay open. A
pending response is recovered before any new submission, preventing duplicate
prompts after timeouts. General-model reviews cover up to eight upcoming actions
while every operation still gets its own scene checkpoint.

Follow-ups are classified against the current project, including across CLI
restarts. `/update TEXT` explicitly edits the current scene; `/new TEXT` creates a
separate project. Live viewport navigation tracks the edited object's evaluated
bounds continuously, including existing-object bevel and material edits, without
moving the render camera. Bevel `amount` is accepted as a bounded `width` alias.
Domes, pointed arch frames and a validated approximate Taj Mahal starter improve
architectural planning. See [MODEL_WORKFLOW.md](MODEL_WORKFLOW.md) for details.
#   B r a i n l e s s _ a g e n t  
 