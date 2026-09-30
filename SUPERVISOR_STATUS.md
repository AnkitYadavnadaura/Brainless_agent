# Supervisor and Universal Agent Status

**Generated:** 2025-01-20
**Tests Passing:** 772 passed, 6 skipped

## Current System State

### ✅ Completed Features
1. **Planner-First Routing** - All interactive tasks now route through ChatGPT browser leader for reasoning before any local tool execution
2. **Always-On Supervisor** - Persistent SQLite-backed task queue with:
   - Task enqueuing with `python run.py supervisor enqueue "task"`
   - Task execution with `python run.py supervisor run`
   - Status monitoring with `python run.py supervisor status`
   - Exponential backoff retry logic
   - Graceful SIGINT/SIGTERM shutdown

3. **VS Code Integration** - Full VS Code/extension/file/workspace bridge:
   - Workspace discovery and file I/O
   - Extension lifecycle (list, install, uninstall)
   - Copilot/Codex coordination (discovery, but CLIs not on PATH)
   - Validated command execution (no shell injection)

4. **Self-Skilling Capability** - `CapabilityGapCoordinator` enables:
   - Browser-authorized skill development plans
   - Permission-gated worker delegation (VS Code, Codex, Copilot)
   - Skill validation before promotion
   - Runtime registration of new capabilities

5. **Uncertain State Detection** - System deliberately:
   - Refuses to replay uncertain browser submissions
   - Moves tasks to `awaiting_recovery` state instead of blind retries
   - Prevents duplicate side effects and hidden execution

### 🔴 Current Blocker: Browser Session State

The browser team has many **uncertain and blocked sessions** from previous runs:
- Multiple ChatGPT/Gemini tabs with `status: "uncertain"`
- Several tabs with `status: "blocked"` (require login)
- One suspended task in `task-928587c60b8d8468e822` with ChatGPT in uncertain state

**Impact:** New tasks enqueued to the supervisor reach the browser-team but:
1. Browser team waits for provider tabs to be ready
2. Provider tabs require manual login/recovery
3. Supervisor task hangs in `running/starting` phase indefinitely
4. No automatic recovery is attempted (by design)

### 📊 Test Infrastructure

Full regression suite validates:
- Supervisor queue persistence and state transitions
- Planner-first routing enforcement  
- VS Code worker availability and delegation
- Capability gap detection and skill promotion
- Uncertain state detection (refuses replays)
- Browser fleet discovery and profile selection

## Immediate Actions Required

### Step 1: Check Browser Health

```bash
python run.py supervisor health
```

**Current Status (2025-01-20):**
- Healthy: ❌ NO
- Ready providers: 1 of 18 (5.6%)
- Blocked providers: 4 (login required)
- Uncertain providers: 12 (recovery needed)

**Issues Detected:**
- Most providers blocked by login requirement
- Several providers with uncertain submissions (pending, no conversation URL)
- Some browser windows closed or lost context

### Step 2: Recover Browser Sessions

Choose ONE approach:

#### Option A: Quick Test (Use the 1 Ready Provider)
If you want to test immediately with the one ready provider:
```bash
python run.py supervisor enqueue "List Python files in the project directory"
python run.py supervisor run
```
This should complete because one ChatGPT provider is ready. However, to handle unknown tasks reliably, more providers should be recovered.

#### Option B: Manual Recovery (Recommended for Full Capability)
```bash
# 1. View browser team status
python run.py browser-team status

# 2. Identify sessions that need recovery
# Sessions shown with "blocked" or "uncertain" status

# 3. For each uncertain session, attempt recovery:
python run.py browser-team recover --session <session-id> --setup --timeout 180

# This will:
# - Open browser windows with that session
# - Wait for you to manually re-authenticate (sign in to ChatGPT/Gemini)
# - Read the responses from any pending work
# - Close the window if appropriate
```

#### Option C: Hard Reset (Nuclear Option - Last Resort)
```bash
# WARNING: This clears all saved provider state and conversations.
# Use only if recovery attempts fail repeatedly.

# 1. Close all Chrome/Chromium windows manually (important!)
# 2. Delete the team session database:
del data/browser-team/team.sqlite3

# 3. Rediscover profiles:
python run.py browser-team inventory

# 4. Open fresh profiles and establish new login:
python run.py browser-team open --setup

# This gives you a clean slate but loses all saved conversation history.
```

### Step 2: Verify Supervisor Flow End-to-End

Once browser team is healthy (all members "ready"):

```bash
# 1. Check health status
python run.py supervisor health
# Expected: "healthy": true, "message": "Browser team is ready"

# 2. Enqueue a simple test task
python run.py supervisor enqueue "List the three largest .py files in the project"

# 3. Check status (should be "queued")
python run.ell supervisor status

# 4. Run supervisor (will submit task to browser leader)
# NOTE: Supervisor now has 10-minute timeout per task attempt
python run.py supervisor run

# 5. Monitor in separate terminal:
# - Watch browser open ChatGPT
# - Watch ChatGPT receive the task
# - Watch browser team coordinate response
# - Watch supervisor mark task "completed" after response extracted

# 6. Verify result in status:
python run.py supervisor status
# Expected: status should change from running → completed (or awaiting_recovery if uncertain)
```

### Step 3: Test Unknown Task Handling

After supervisor flow validates:

```bash
# Enqueue an unknown task (something not explicitly configured)
python run.py supervisor enqueue "Generate a report of Python package dependencies and their versions"

# Run supervisor
python run.py supervisor run

# Expected behavior:
# 1. Task enters running state
# 2. Browser leader receives task (ChatGPT)
# 3. ChatGPT analyzes and suggests approach
# 4. Browser team may detect need for capability gap:
#    - CLI tool to list packages? (pip, poetry, etc.)
#    - File analysis? (parse pyproject.toml, requirements.txt)
#    - Output formatting? (CSV, JSON, markdown)
# 5. If capability gap exists, system:
#    - Checks if VS Code worker can help
#    - Proposes a skill development plan
#    - Optionally runs VS Code to gather data
# 6. Result extracted and stored
# 7. Task marked completed
```

## Architecture Review

### Task Flow (Supervisor → Browser Team → Leader → Result)

```
┌─────────────┐
│  Supervisor │  - SQLite queue persistence
│  (always-on)│  - Exponential backoff retries
└──────┬──────┘  - Detects uncertain browser states
       │         - Prevents blind replays
       ↓
┌──────────────────────────────┐
│   Browser Team (Chromium)    │  - Fleet of profiles (ChatGPT, Gemini)
│ - Fleet discovery            │  - Parallel provider coordination
│ - Profile selection          │  - Session persistence
│ - Participant readiness      │  - Round-based work synthesis
└──────┬───────────────────────┘
       │
       ↓
┌────────────────────────────┐
│  Chrome Provider (Browser) │  - ChatGPT or Gemini tab
│  - Prompt submission        │  - Response extraction from DOM
│  - DOM observation          │  - Conversion to structured output
│  - Bounded action loop      │  - Timeout/retry recovery
└──────┬─────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│  Extracted Result → Supervisor   │  - Verified before marking "completed"
│  - Browser session persisted     │  - Uncertain outcomes → "awaiting_recovery"
│  - Result recorded in team.db    │  - Success confirmed via status query
└──────────────────────────────────┘
```

### Skill Development Path (For Unknown Tasks)

```
┌─────────────────────────────────────┐
│  Browser Leader detects gap         │
│  (e.g., "need to list Python files")│
└────────────┬────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  CapabilityGapCoordinator evaluates │
│  - Available skills registry        │
│  - Proposed workers (VS Code, CLI) │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  Browser authorizes skill plan      │
│  - No embedded code                 │
│  - Structured workflow steps        │
│  - Expected outcomes defined        │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  Worker executes (e.g., VS Code)    │
│  - Reads workspace config           │
│  - Executes validated commands      │
│  - Returns structured result        │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  Runtime validates result           │
│  - Output matches expected format   │
│  - No side effects beyond scope     │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  Skill promoted and registered      │
│  - Stored in learning system        │
│  - Reusable for future tasks        │
└──────────────────────────────────────┘
```

## Key Design Decisions

### 1. No Blind Retries on Uncertain Submissions
- **Why:** Prevents duplicate side effects (e.g., creating two tasks instead of one)
- **How:** Detects uncertain state and moves task to `awaiting_recovery`
- **Recovery:** Manual `browser-team recover` with manual re-authentication if needed

### 2. Browser Leader as Authority
- **Why:** Ensures all tasks are classified and planned before execution
- **How:** All interactive tasks forced through `--leader-only --execute` flags
- **Benefit:** System understands the task intent before touching any tools

### 3. Permission-Gated Worker Delegation
- **Why:** VS Code, Codex, Copilot have real file system and OS access
- **How:** Plans must be JSON with `"authority": "browser-leader"`, no embedded code/shell
- **Enforcement:** Runtime validates plan structure, rejects code/commands, uses allow-listed CLIs

### 4. Persistent SQLite Queues
- **Why:** Tasks survive application restart, crashes, network interruption
- **How:** Supervisor persists state before each browser-team call
- **Atomicity:** Database writes lock properly; partial failures detected

## Known Limitations

1. **Browser Tab Context Loss**
   - If browser crashes or tabs close unexpectedly, provider context is lost
   - Recovery requires manual re-authentication
   - Mitigation: Planned health checks to detect and alert on provider disconnection

2. **Long-Running Tasks**
   - Supervisor waits for browser-team to return; tasks > 15 minutes may timeout
   - Mitigation: Break large tasks into checkpointed sub-tasks

3. **Codex/Copilot CLI Availability**
   - Currently report as "unavailable" (not installed on this machine)
   - Mitigation: Environment variable configuration or extension-based approach planned

4. **VS Code Extension Management**
   - Installing/uninstalling extensions can be destructive to user's dev environment
   - Mitigation: Only allow in authorized skill plans; require explicit user approval

## Recommended Next Steps

### Short Term (Complete the E2E Flow)
1. ✅ Recover browser sessions (manual login/reset)
2. ✅ Run simple known task through supervisor → leader → completion
3. ✅ Verify task marked "completed" and result accessible
4. ✅ Run unknown task and observe capability gap detection
5. ✅ Verify optional skill development (if gap detected)

### Medium Term (Enhance Robustness)
1. Add health check job to detect browser provider disconnections
2. Implement automatic recovery attempt thresholds before requiring manual intervention
3. Create web-based supervisor dashboard for task monitoring
4. Add scheduled periodic task execution (cron-like)
5. Implement task prioritization and SLA enforcement

### Long Term (Full Autonomy)
1. Migrate more tools to permission-gated model (currently: browser, youtube, blender, unreal)
2. Implement self-discovery of installed OS tools via `which`, `apt-cache`, etc.
3. Add automatic skill learning from successful outcomes
4. Enable cross-worker coordination (e.g., VS Code + browser + CLI for complex tasks)
5. Implement persistent memory across supervisor runs (task history, learned skills, etc.)

## Related Documentation
- [BROWSER_TEAM.md](BROWSER_TEAM.md) - Browser fleet coordination
- [PERMISSIONS.md](PERMISSIONS.md) - Permission system details
- [MODEL_WORKFLOW.md](MODEL_WORKFLOW.md) - Agent reasoning workflow
- [README.md](README.md) - System architecture overview

