# Event permissions

Observation scopes are separate from controls: `mouse.observe`, `keyboard.observe`, `screen.observe`,
`clipboard.read`, `filesystem.read`, `process.observe`, `window.observe`, `browser.observe`,
`network.observe`, `device.observe`, `audio.observe`, `system.observe`, `session.observe`,
`notification.observe`, `security.observe`.
Controls use the corresponding `.control`, `.write`, `.delete`, `.capture`, or `power.control` permission.
Subscriptions do not grant permissions; action execution checks the caller's current permission set.

`PERMISSIONS` is the canonical capability catalog and `permission_for_event(category)` supplies the minimum
observation permission for detector/agent factories. A child can receive only a subset of its parent's
permissions. Directory and application allow-lists add a second boundary around filesystem and process
actions; they never broaden the permission grant. Child factories reject broader paths/applications and
inherit a restricted parent's boundary when no narrower boundary is supplied. Agent risk policies add an
independent ceiling; holding a permission does not override that ceiling.

## Voice permission prompts

The dashboard runtime asks before a registered tool's first use. With voice running,
the topmost overlay shows the exact tool and required capabilities. A finalized,
confident spoken **"yes, continue"** approves the displayed request and remembers
eligible permissions on this computer. **"Allow once"** permits only that action;
**"no"** denies it. Ambiguous or low-confidence speech does not approve anything.
Stop, voice shutdown, and request timeout leave the pending action unexecuted.
The authenticated dashboard can also approve or deny a pending action.

Remembered grants live in `data/permission-grants.json`, keyed by exact tool and
permission, and survive application restarts. They do not grant other tools access
or override a policy denial, the agent's capabilities, or the mission's boundaries.
High-risk, destructive, and sensitive operations such as sending email still need
approval for each action. To reset remembered permissions, stop the application
and remove `data/permission-grants.json` (or use `PermissionGrantStore.revoke`).
This is application consent; Windows elevation and website login still require
their normal user interaction.

With the microphone connected, say **"open browser"**. After approval and successful
opening, the overlay asks which site to open. Say **"Gmail"** or **"YouTube"**; after
navigation succeeds, it asks what to do on that site. On YouTube, **"search for cats"**
opens search results and **"play cats"** requests playback. New tools request their own
permissions when needed. Follow-up questions appear after runtime completion, and
failed browser operations are reported without claiming the page opened.

Voice browser tasks now ask which discovered installed profile (or managed browser)
to use. Profile selection is itself a governed tool, and follow-ups reuse the
selected window. Screen observation requests both `browser.read` and `screen.read`.
The overlay stays visible with task status between questions. See
[EXTERNAL_BROWSER.md](EXTERNAL_BROWSER.md) for supported external actions and OCR setup.
