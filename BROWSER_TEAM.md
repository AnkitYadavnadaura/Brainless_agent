# Installed-browser team

The Windows CLI can discover Chrome, Edge, Brave, Vivaldi, Opera, Opera GX and
Firefox, including their existing profiles and the app's existing managed Chrome
profile. It opens one visible window per eligible profile with ChatGPT and
Gemini tabs. Normal runs omit tabs previously confirmed as signed out; a profile
with both websites signed out is not opened. Discovery covers the registered executable locations and known
profile roots for those browser families; portable/custom roots and other browser
families are not currently enumerated.

The default **Chrome profile leader** uses the existing signed-in profile at
`Brainless_agent/data/browser-profile`. This is the same user-data directory
opened by the following command when run inside `Brainless_agent`:

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --user-data-dir="$PWD\data\browser-profile" --no-first-run
```

The leader selects Chrome's last-used profile (normally `Default`), opens one
owned team window in it, and uses native accessibility input. An already-open
manual window can stay open. The profile is not launched again as a peer, and
its participant IDs/checkpoints remain the same. The unrelated isolated
Chromium profile's sign-in cache does not exclude this Chrome leader.
Website replies remain the reasoning source; the Python coordinator validates
and executes browser repairs. To inspect just the leader, then use the full team:

```powershell
python run.py browser-team open --leader-only
python run.py browser-team run "Describe your task here" --recheck-signins
```

`--leader chrome-profile` is the default for CLI and GUI runs. `--leader chromium`
explicitly selects the previous isolated `data/chromium-leader` profile using
Playwright's [persistent browser context](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context).
That alternative needs its own website sign-ins and Playwright's Chromium install.
`--leader none` uses only peers. `--leader-only` cannot combine with `--profile`.
The `open` command leaves the native leader window open; task/doctor exit closes
only the leader window owned by that command, preserving its login and manual
windows. Other native windows retain their close-on-exit behavior.

The ready profile-leader ChatGPT member leads by default, with its Gemini tab and
then healthy peers as fallbacks. The current leader is reported in status and
receives final synthesis first. During a task, a healthy website member may
propose `recheck`, `switch_native`, `reload_tab`, or `hold` for up to two failed members. The
coordinator records that diagnosis as its own durable round, validates the
allowlisted choice, invokes the affected client's repair, and independently
checks readiness before rejoining it. If the advising leader fails, one healthy
replacement may advise instead. `doctor` and preflight never send diagnosis
prompts. Authentication, denied permissions, quota limits and pending submissions
cannot be cleared by peer advice; pending replies use exact-receipt recovery.
Reloading uses the saved provider conversation URL and refuses a pending or
generating response. It never resubmits the task or executes suggested code.

Run these commands from either the outer workspace or `Brainless_agent`:

```powershell
python run.py
python run.py browser-team inventory
python run.py browser-team run "Describe your task here" --session my-task --wait-ready 120
python run.py browser-team status --session my-task
```

`python run.py` and `python run.py cli` now enter browser-team mode. Enter the
task when prompted; then the app discovers and opens all supported profiles.
The Tk GUI (`python run_gui.py`) also defaults to **Use all installed browser
profiles: ChatGPT + Gemini**. Its log reports profile launches and readiness;
it waits up to two minutes for login and supports Emergency Stop. Turn that
option off for the legacy GUI provider workflow. Team mode does not currently
support the legacy Pause button or its task-history table.

The old managed single-browser CLI is explicitly available as
`python run.py single-browser`. The dashboard remains available through
`python run_dashboard.py` (or `python run.py dashboard` from the outer directory).
An unknown command now reports usage instead of silently launching Chromium.

`inventory --json` returns executable locations, profile directories, stable IDs,
counts and warnings without opening browsers. `open` only opens the windows and
websites for inspection. It sends no prompts. Each new CLI process creates its
own windows; it does not adopt windows left by an earlier process.

`--input-mode auto` uses Windows accessibility focus/Invoke patterns and
verified keyboard paste when the provider's visible controls are recognized.
Mouse clicks remain a fallback for controls without an Invoke pattern. Loading or
accessibility errors no longer silently fall back to console pasting. Use
`--input-mode native` or `--input-mode console` to explicitly test either path.
Native mode does not need console paste permission. Unknown or localized
accessibility layouts can still require adapter updates.

`--setup` waits after opening the windows for manual login or console setup.
Console mode requires docked developer tools in English; close them before
continuing. `--wait-ready 120` automatically rechecks readiness while you finish
login when no tab is ready. Startup proceeds once at least one tab is ready;
unsigned-in, challenged, unavailable and uncertain tabs are reported as skipped.
A visible login control means a tab is unsigned even if it exposes a composer.
Sign-in means the website session, not the browser's account name. Unknown profiles
must be inspected once; no passwords or cookies are read to determine eligibility.
After signing in manually, pass `--recheck-signins` to reconsider cached exclusions.
`open`, `doctor` and `run --setup` also bypass those exclusions. A signed-in Gemini
tab can participate even when ChatGPT in the same profile is excluded, and vice versa.
Login, MFA and CAPTCHA remain human steps. `--profile PROFILE_ID` selects one
profile from the inventory; repeat the option to select several. The default
remains all discovered profiles.

## Collaboration and task execution

The default `--work-mode parts` asks the leader to analyse software requirements
and divide a request into 1..16 parts with acceptance criteria and an acyclic
dependency graph. The runtime assigns independent parts to separate ready tabs,
passes dependency results to later parts, rotates reviewers and integrates all
results into the original requested output schema. Failed independent work does
not discard successful results. Only a certified unsubmitted part can be
reassigned; uncertain submissions and usage limits cannot trigger account switching.

An explicit supported software name is preserved. Without one, a 3D request is
routed to Blender; general tasks go through the existing capability workflow.
Other named software is not silently replaced by Blender. Software selection
does not install or prove availability of a capability; existing health checks
still govern execution. Large city/village plans can separate layout, terrain,
roads, buildings, vegetation, materials and lighting, within existing operation
and hardware limits. A GTA6-like reference expresses a desired style, not a
guarantee of game-production geometry, assets or photorealism.

`--work-mode review` retains independent whole-request proposals and peer review.
The default is two rounds (work and review) followed by synthesis. `--rounds 1..3`, `--parallelism 1..16` and
`--timeout 30..900` control bounded work. Desktop input is serialized even when
multiple website responses generate concurrently.

### Shared team board and tagged messages

Each session has an atomic JSON board at `data/browser-team/boards/<session-hash>.json`;
the exact path is printed when work starts. It includes assignments, dependencies,
part answers, review states, tagged messages and the current executor checkpoint.
SQLite retains historical requests and mail. The JSON file is a readable view;
use the message command to post reliably while the team is running:

```powershell
python run.py browser-team board --session my-task
python run.py browser-team message --session my-task --to "PARTICIPANT_ID_FROM_BOARD" "Check that roads meet at district borders"
python run.py browser-team message --session my-task --to "*" "Use metres and keep the central square clear"
```

Use exact participant IDs from readiness/board output. For `--execute`, modeling
work switches to the printed **3D project ID** as its session; use that ID for
board/mail commands. Website parts can return up to four tagged messages per
turn. Every work, review, synthesis and repair turn reads its inbox. Mail arriving
while a website is generating is delivered on its next turn; unread mail survives
later requests in the same session. Threads are bounded, not always-on chat bots.
The board shows the latest 500 messages; older messages remain in SQLite.

Part results and peer claims are proposals. Existing schema, geometry, file/hash
and checkpoint validators still verify execution. Full part results must fit the
synthesis context; oversized integrations pause instead of silently dropping
parts. Blender scene writes remain serialized so concurrent website planning
cannot overwrite another part's scene checkpoint.

Peers receive bounded task checkpoints and one another's suggestions. They can
correct reasoning and propose solutions to failures. A definitely unsubmitted
failure gets one retry in the same profile using peer context; the client reopens
that same saved chat. Failed synthesis can move to another already participating
peer. Model text is never executed as console JavaScript or shell commands.
This is bounded collaboration, not a guarantee that every task or site failure
can be solved automatically.

By default `run` returns a team answer. To use the team as the reasoning provider
for the existing capability and 3D workflows:

```powershell
python run.py browser-team run "Build a detailed village in Blender" --execute --session village --setup
```

The existing task router, tool permissions, validators and checkpoints still own
execution. `--execute` selects the project's existing 3D and playback workflows.
Blender must be installed for 3D tasks. The team supplies planning
and review responses through the existing provider interface, including repair
requests after invalid plans or failed operations. `--execute` and `--desktop`
are CLI features; the GUI team mode returns a collaborative answer.

For other Windows UI tasks, use the new bounded desktop workflow:

```powershell
python run.py browser-team run "Open Notepad and write a short project checklist" --desktop --max-actions 12 --max-minutes 10
```

The loop observes real UI Automation controls, asks the team for one structured
action, validates the observed target, executes through the existing permission
and mission gates, then observes and checks the result. It supports launching
Calculator/Notepad/Paint/Explorer/Settings, focusing observed windows, and
clicking, pasting or pressing a small set of navigation keys on observed controls.
Browser reasoning can change the foreground window; the desktop target is pinned
and revalidated before input. Shell/console typing and model-authored process
commands are rejected. Mutating UI actions show a concrete terminal approval
request; unattended runs block at that gate. This is a broader UI executor, not
unrestricted execution or a guarantee that every application exposes usable UI.
Desktop reports live under `data/browser-team/desktop`.

## Input and recovery

The native adapter uses the exact observed composer runtime ID for accessibility
focus, independently verifies focus, verifies pasted text, and invokes only the
observed send button. An ambiguous invocation remains pending. This avoids
depending on Chromium hit tests that can return a containing Group instead of
the editable descendant. UI Automation helper processes use DPI-aware coordinates
as described by [Microsoft's screen scaling guidance](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-screenscaling).
ChatGPT's one-time `/c/WEB:<uuid>` to canonical conversation transition is
recognized only after submission; later changes to another conversation remain
blocked. Native response extraction recognizes current ChatGPT response-action
groups and Gemini's hidden author label plus feedback-control structure. Loaded
offscreen replies are counted, including replies Chromium flattens into Text
nodes, and their text is read in document order. Where available, the answer's
Copy response control extracts the selected answer. Structured prompts request
a JSON code block because unfenced Markdown can consume backslash escapes even
when copied. The coordinator removes a complete valid JSON presentation fence;
structured planning and peer-repair parsers reject surrounding commentary.
References to CAPTCHA inside coordination prose are not treated as a sign-in
challenge; recognized challenge controls still pause the affected tab.

Native readiness checks queue before their timeout starts, avoiding false failures
while another profile owns the desktop input lane. At run startup, a participant
with one unresolved saved round gets one bounded read-only recovery attempt. The
saved session, conversation URL and round must match; no prompt is resent and an
old paused task is not automatically executed. Successful recovery releases the
tab for a new task. Missing conversation URLs or ambiguous receipts remain skipped.
Address-bar focus and the pasted URL are verified before navigation; recovery
rejects any reply from another conversation.

For a small diagnostic that opens and closes its own Edge profile window:

```powershell
cd Brainless_agent
python -m scripts.diagnose_native_input
python -m scripts.diagnose_native_input --submit-smoke
```

The first command inspects/focuses composers without typing. The second sends
one fresh nonce prompt per ready provider and checks the exact reply. Neither
replays the user's saved task or deletes an uncertain receipt.

Edge titles with a profile label and the invisible brand separator are now
recognized while retaining the unique launch marker and new-window checks.
When Windows refuses foreground activation, the runtime tries bounded
accessibility focus and then a single click on an uncovered, owned title bar
verified by Windows [WM_NCHITTEST](https://learn.microsoft.com/en-us/windows/win32/inputdev/wm-nchittest).
Temporary window stacking changes are restored, and foreground identity is
checked before every subsequent key. If activation still fails, no text is sent.
Unknown console execution is quarantined per identified tab, so its sibling
provider can continue. Operations without an identified tab conservatively
retain a window-wide block. A quarantine is never cleared to force a resend.

Fleet startup retries confirmed process-start failures and partial tab setup up
to two times, with a short delay between attempts. It closes a partial owned
window before retrying. If a launch times out, it checks for that launch's unique
marker without starting another process. A later `BrowserFleet.start()` call can
adopt a late window, recheck existing window identities, and replace windows that
closed or changed ownership. Healthy windows stay in place. An unreadable window
identity pauses that profile until a later check succeeds.

Startup and shutdown save a timestamped fleet snapshot, failure details, and the
last 100 recovery events to `data/browser-team/diagnostics/last-fleet.json`.
`python run.py browser-team status` includes this historical snapshot even if no
task reached the team database. `last-team.json` additionally records the elected
leader and member health. `doctor` and `smoke` report failure or partial
coverage when a selected profile could not launch. These reports help diagnose
the next run; they do not authorize adopting windows from a previous process.

Native input focuses only windows identified by a unique launch marker. Keyboard
shortcuts open provider tabs. Native input uses fresh accessible composer and
Send controls, hit-tests their observed bounds, checks focus before paste, and
verifies the composer text before sending. Responses are extracted only from
explicitly identified assistant groups. The console path uses fixed DOM programs
to read response elements, fill the composer and invoke Send. Neither path uses
model-invented coordinates. A failed or uncertain send never triggers a second
send through the other input path.
The console returns nonce-tagged results through the clipboard, whose previous
text is restored unless you copied something else meanwhile.

The implementation uses the documented DevTools
[`copy()` console utility](https://developer.chrome.com/docs/devtools/console/utilities).
Firefox uses an explicit profile path and `-no-remote` to prevent forwarding into
a different running profile, following Mozilla's
[command-line options](https://firefox-source-docs.mozilla.org/browser/CommandLineParameters.html).
An already locked Firefox profile may need its current instance closed manually.
No remote-debugging port, cookie copying or credential-store access is used.

Submission intent is saved before sending. A timed-out request gets one bounded
read-only recovery attempt using its exact saved request/round identity. A
confirmed existing answer is reused; otherwise the participant remains
quarantined across restarts. Login readiness can rejoin a definitely unsubmitted
member after you sign in. Usage limits are rechecked without sending after a
five-minute cooldown; `doctor --recheck-limits` can explicitly inspect a reset
limit once sooner. Permission denials remain blocked. The status command reports
request/round outcomes and persisted member problems without printing complete
prompts or answers.

Console setup interventions pause without repeated loading retries, while
pending submission receipts remain quarantined across restarts. Malformed
transport replies are reported as typed provider errors. General response
recovery keeps its remaining read attempts if a reload fails, but stops on
login intervention, emergency stop, or exhausted time/action budgets. Recovery
uses these built-in operations; it does not rewrite source code or guarantee
repair of arbitrary errors. Login, CAPTCHA and ambiguous submissions can still
require owner input.

```powershell
python run.py browser-team recover --session my-task --setup
```

Recovery opens the profile windows and only reads the saved outstanding
conversation. It can clear quarantine when the response is confirmed and exactly
one unresolved round matches that participant and session. It never treats an
old recovered response as the answer to a new task. Missing conversation URLs,
ambiguous matches, login and console failures remain unresolved and need manual
inspection. Do not delete checkpoints to force a replay.

Native peer windows remain open by default. Add `--close-on-exit` to close only windows this
run created. Failed close attempts remain tracked, and partial launches retry
only after their window has actually closed. Ctrl+C stops coordination; a native
input operation already in progress finishes its bounded critical section first.

Local team state lives in ignored `data/browser-team/team.sqlite3` and
`native-sessions.sqlite3`. These contain task answers, checkpoints, response
receipts and chat URLs, so treat them as local task data.

## Verification

Run actual diagnostics separately from the unit tests:

```powershell
python run.py browser-team doctor --input-mode native --close-on-exit
python run.py browser-team smoke --wait-ready 120 --close-on-exit
```

`doctor` checks provider readiness without submitting a task. `smoke` sends a
harmless arithmetic/nonce challenge through independent proposals, peer review
and synthesis. A pass requires valid replies from every selected participant,
both ChatGPT and Gemini, and a matching final answer. A partial run is explicitly
reported as partial. Reports under `data/browser-team/diagnostics` identify the
driver used; injected test transports are not presented as native live evidence.

```powershell
python -m pytest tests/test_browser_inventory.py tests/test_browser_fleet.py tests/test_native_console.py tests/test_native_website.py tests/test_collaborative_provider.py tests/test_browser_team_cli.py tests/test_team_diagnostics.py tests/test_desktop_team_workflow.py tests/test_accessibility_scripts.py -q
```

Tests use temporary metadata and fake desktop/website transports; they cover
profile isolation, launch/close failures, input serialization, submission
certainty, peer exchange, recovery, persistence and CLI routing. Actual website
selectors, sign-in state and native focus behavior still require a live test on
the installed browser versions.
