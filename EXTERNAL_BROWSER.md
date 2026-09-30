# External browser voice control

Start the dashboard and connect voice. Describe your task in as many spoken parts
as needed. After a short pause, the overlay asks whether you have anything else to
add. Say **"yes"** and continue, or **"no"** / **"that's all"** when finished. Only
then does the agent analyze those unsubmitted parts together and ask for missing
information. Silence never submits the task. Say **"start over"** to discard the
current request. Stopping voice clears unfinished speech.

For example, say **"open YouTube"**, then **"no"** at the completion question.
The overlay lists discovered browser profiles and a managed-browser option. Answer
with the profile name or its displayed number. Confirm any permission prompt with
**"yes, continue"**; eligible tool permissions are remembered locally.

The external client opens a window in that installed profile, using its existing
website logins. Subsequent commands use that window's current tab. It does not take
over an unrelated browser window. Say **"switch browser profile"** to choose again.
The selection stays active for this application run; remembered permissions survive
restarts. Closing the selected window requires an explicit open/navigation request
to reopen it.

Try this sequence:

1. "Open YouTube", finish with "no", then choose a profile and approve the requested tools.
2. "Search for Python tutorials".
3. "Play video" to choose a visible video, or resume the current video.
4. "Pause video" or "skip the ad" when its control is visible.
5. "Open https://example.com", then "what is on this page?"

Finish each new task with **"no"** when the overlay asks whether you want to add
anything. Answers to specific clarification questions, profile choices, and
permission prompts are handled directly. In a permission prompt, **"no" denies
permission**; it never submits buffered speech or grants approval.

For email, give your request, recipient, and purpose across spoken parts, then
finish the request. Gmail reuses your selected installed profile or asks you to
choose one once. After approval, it opens Gmail before asking for any remaining
recipient/content details. Sending the prepared message requires a separate
approval. An opening failure preserves your choice and offers a retry.
If draft reasoning fails after Gmail opens, the conversation keeps the same
profile and accumulated email details. Retrying does not reopen Gmail or approve
sending.

When recipient and message details are already available, a failed draft-model
response now falls back immediately to a plain draft from those details and asks
for send approval. Missing details still produce a question. Profile-selection
answers are excluded from email content. The overlay reports the send outcome.

External Gmail sending and YouTube playback try accessibility controls first,
then a runtime-owned DOM method in the same selected browser window when the first
method reports a recoverable failure. DOM execution uses the existing browser
console transport; browser paste protection and manual sign-in requirements still
require user interaction. Gmail changes method only when the first method confirms
that Send was not activated. An uncertain send stops for inspection.

Reversible browser tasks can also recover by observing the current page and
planning a different approach, up to two times. Repeated plans and already-completed
actions are rejected; each new action goes through normal runtime permissions.
This recovery applies to navigation, observation, search, and playback. It does
not automatically replay email sends, form submissions, denied actions, or tasks
requiring manual intervention. Unsupported tasks report the failure for clarification.

Console operations log named steps such as `gmail.draft.verify`,
`gmail.send.activate`, and `gmail.send.verified`, followed by a
`BRAINLESS_RESULT:<request-id>:` JSON receipt. The transport captures the DevTools
`copy` helper before asynchronous work starts and can read the matching console
receipt if clipboard delivery fails. A missing receipt never causes the action
to be replayed. Chrome documents `copy` as a [DevTools-only utility](https://developer.chrome.com/docs/devtools/console/utilities/#copy).

An unavailable or stale Windows accessibility snapshot gets one fresh retry,
then a DOM observation in the same owned window. DOM fallback click/type targets
refer to current elements and are revalidated before input. Editable/password
values are excluded from observation; screenshots are not taken through this
fallback because accessibility masking is unavailable. Page navigation or input
invalidates those targets.

The configured Browser LLM reviews accessibility failures and console diagnostics
to explain the failing stage and assist recovery. Its review is advisory and
cannot establish that an email was sent or authorize additional tools. Stop
cancels pending diagnostic reasoning. If the reasoning provider is unavailable,
the runtime retains the original failure and verification result.

The microphone stays connected after pressing **Start listening**, so you can
answer across pauses; use **Stop voice** to disconnect. The pause interval defaults
to 1.5 seconds and can be set with `VOICE_TASK_PAUSE_SECONDS` (up to 30 seconds).
`VOICE_COLLECT_TASKS=false` restores immediate finalized-turn routing. Request
collection is limited to 2,000 characters; oversized or unclear parts must be
corrected before submission. Unsubmitted speech is held in memory only.

Ordinary website interaction supports clicking observed links and buttons, filling
visible text fields, pressing keys on a focused control, scrolling, and navigating
back/forward or refreshing. Each external interaction refreshes the observation
before the next step. General website input still asks for approval per action
because a site's controls can submit forms or change account data. See
[PERMISSIONS.md](PERMISSIONS.md) for remembered permissions and cancellation.

The overlay remains visible during the active voice session, showing questions or
task status. On Windows it stays above normal application windows without taking
keyboard focus. Stopping voice closes it. Windows secure-desktop prompts remain
outside the application's overlay.

## Screen reading and OCR

`browser.observe` combines the selected window's visible accessibility controls
with local OCR of a screenshot cropped to that window. Managed browser sessions
use visible DOM details and a viewport screenshot. The planner receives this fresh
evidence before follow-ups; OCR/page text never grants permission or supplies
trusted instructions. Actions target observed controls, not guessed coordinates.

OCR uses Pillow and a local Tesseract installation. It discovers Tesseract on PATH,
in standard Windows installation folders, or through `TESSERACT_CMD`. English
language data must be available in Tesseract's installation, in a directory named
by `TESSDATA_PREFIX`, or at `data/tessdata/eng.traineddata`. The project-local
directory is ignored by Git. Obtain English data from the official
[Tesseract fast language-data repository](https://github.com/tesseract-ocr/tessdata_fast).
The [Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)
describes language configuration.

Screenshots for these observations are processed in memory. Editable/password
fields are masked, and Windows excludes the assistant overlay from capture where
supported. OCR failures preserve accessibility/DOM evidence and report an OCR
status instead of inventing screen text. Captured text is subject to normal mission
checkpoint storage; screenshots are not saved by this observation tool.

Controls normally come from the website's accessibility tree. If no interactive
controls are exposed, OCR supplies visible text regions as candidate click targets.
You can also say **"select area"** and draw a rectangle in the selected external
browser window. The resulting click still requires the normal runtime approval.
Changing pages or moving the window invalidates the selection; select again.
Stopping voice while the selector is open prevents a late selection from submitting
a task. The selector itself closes on Escape or after its 20-second timeout.
Login challenges and browser security dialogs require normal user interaction.
External YouTube playback currently supports play, pause, visible ad skipping, and
next-video controls; exact seeking remains available in the managed browser.

## Validation

Automated tests cover spoken selection and approval, exact profile matching,
current-window reuse, native click/type/key sequences, fresh observations, stale
target rejection, overlay focus behavior, and OCR with a generated test image.
External-browser tests use a simulated Windows desktop behind the real native
transport. Confirm the flow above in the desired installed profile after restarting
the dashboard; real website layout and accessibility can differ.
