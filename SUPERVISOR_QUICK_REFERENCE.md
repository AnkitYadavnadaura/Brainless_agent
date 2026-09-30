# Supervisor Quick Reference

**Status:** 772 tests passing, Supervisor with timeout protection active

## TL;DR - Common Commands

```bash
# Check if ready to run tasks
python run.py supervisor health

# Enqueue a task
python run.py supervisor enqueue "Your task here"

# List all queued, running, or completed tasks
python run.py supervisor status

# Process all queued tasks (runs forever, Ctrl+C to stop)
python run.py supervisor run

# Help
python run.py supervisor --help
```

## Decision Tree

### "I want to test the supervisor now"

```
├─ Check health first?
│  └─ python run.py supervisor health
│
├─ Health is healthy (green)?
│  └─ YES → Proceed to queuing task
│  └─ NO → Skip to recovery section below
│
├─ Queue a simple task
│  └─ python run.py supervisor enqueue "List Python files"
│
├─ Watch it run
│  └─ python run.py supervisor run
│     (Ctrl+C after task completes)
│
├─ Check result
│  └─ python run.py supervisor status
│     (Should show status: "completed")
└─ DONE
```

### "Health check shows NOT healthy - what do I do?"

```
├─ How many providers are ready?
│  ├─ 0 ready → Recovery REQUIRED
│  ├─ 1-2 ready → Can test, but recover for full capability
│  └─ 3+ ready → Acceptable, recovery recommended
│
├─ What's blocking?
│  ├─ Many "blocked" → Providers need login
│  │  └─ Option A: Recover one session: python run.py browser-team recover --session <id> --setup
│  │  └─ Option B: Manual login in browser windows
│  │
│  └─ Many "uncertain" → Previous tasks interrupted
│     └─ Let system retry once: python run.py supervisor run
│     └─ Then check again: python run.py supervisor health
│
└─ If recovery doesn't help → See hard reset below
```

### "I want to recover providers manually"

```
1. View status
   python run.py browser-team status

2. Find a session with uncertain members
   Look for lines like:
     "session": "task-928587c60b8d8468e822"
     "status": "uncertain"

3. Start recovery
   python run.py browser-team recover --session task-928587c60b8d8468e822 --setup

4. In the browser window that opens:
   - If you see login screen → Sign in to ChatGPT/Gemini
   - If you see a conversation → It will read the response
   - Press Enter or close window when done

5. Verify improvement
   python run.py supervisor health
   # Watch "ready" count increase

6. Repeat for other sessions if needed
```

### "Health check keeps showing NOT healthy despite recovery attempts"

```
This means providers are stuck or inaccessible. Try hard reset:

1. Close all browser windows manually (IMPORTANT)
   - Close all Chrome profiles
   - Make sure no Playwright browsers remain

2. Reset state
   python run.py browser-team doctor
   # Check what's happening

   If problems persist:
   del data/browser-team/team.sqlite3

3. Rediscover profiles
   python run.py browser-team inventory

4. Open fresh browsers
   python run.py browser-team open --setup
   # Wait for login screens to appear
   # Sign in to ChatGPT and Gemini
   # Press Enter when done

5. Verify health
   python run.py supervisor health
   # Should show healthy: true now
```

## Task State Reference

### Running a Task

```
Step 1: Enqueue
$ python run.py supervisor enqueue "Do something"
Queued task 013ac86f-dcde-4113-ae08-07144bb60e9e

Step 2: Check status (before running)
$ python run.py supervisor status
[
  {
    "id": "013ac86f-...",
    "status": "queued",     ← Ready to run
    "attempts": 0,
    ...
  }
]

Step 3: Run supervisor
$ python run.py supervisor run
[Supervisor waits for tasks]
[Browser opens ChatGPT]
[Task submitted]
[Response extracted]
[^C to stop supervisor]

Step 4: Check result (after running)
$ python run.py supervisor status
[
  {
    "id": "013ac86f-...",
    "status": "completed",  ← Success!
    "checkpoint": {"phase": "verified", "attempt": 1},
    ...
  }
]
```

### When Task Gets Stuck (Timeout)

```
Status progression:
queued → running (10 minute timer starts)
  ↓
[10 minutes pass without completion]
  ↓
awaiting_recovery (moved out of retry loop)

What to do:
1. Check browser windows - are they hanging?
2. Check provider status
   python run.py supervisor health

3. If providers are all blocked/uncertain:
   python run.py browser-team recover --session <id> --setup
   # This will read the actual saved state

4. After recovery:
   python run.py supervisor status
   # Task may automatically progress or may need retry

5. If still stuck, see "hard reset" section above
```

## Troubleshooting Matrix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `supervisor health` shows "NOT healthy" | Browser providers need login | `browser-team recover --setup` |
| Task in `awaiting_recovery` state | Timeout or uncertain submission | Run `browser-team recover` then check `supervisor status` |
| Task in `failed` state | Exhausted retries | Check error message in status, possibly hard reset |
| Supervisor hangs when running `python run.py supervisor run` | (Fixed in this version - now has 10min timeout) | Previously would hang forever; now moves to `awaiting_recovery` after 10min |
| Browser windows stay open | By design | They stay open until Ctrl+C or app closes |
| Multiple browser windows open | Multiple profiles discovered | You can work in any of them; supervisor coordinates |
| Can't sign in to browser window | Browser profile data lost | Delete browser data or use hard reset |

## Health Check Levels

```bash
$ python run.py supervisor health

GREEN (Healthy):
{
  "healthy": true,
  "ready": 18,
  "blocked": 0,
  "uncertain": 0,
  "message": "Browser team is ready"
}
→ You can run tasks confidently

YELLOW (Degraded):
{
  "healthy": false,
  "ready": 3,           # Still have some ready
  "blocked": 2,         # But some need login
  "uncertain": 13,      # And some need recovery
  "message": "Browser team NOT ready: 3 ready, 2 blocked, 13 uncertain"
}
→ Can still run tasks (will use ready providers)
→ Should schedule recovery session soon

RED (Not Healthy):
{
  "healthy": false,
  "ready": 0,           # No ready providers!
  "blocked": 8,
  "uncertain": 10,
  "message": "Browser team NOT ready: 0 ready, 8 blocked, 10 uncertain"
}
→ Cannot run new tasks reliably
→ MUST recover before proceeding
```

## Performance Notes

- **First run:** May take 1-2 minutes (browser startup + tab opening)
- **Subsequent runs:** ~30-120 seconds per task (depends on complexity)
- **Timeout:** 10 minutes per task attempt (includes all provider coordination)
- **Backoff:** If task fails: 1s → 2s → 4s delay before retry (max 3 attempts)
- **Supervisor:** Processes queue continuously until Ctrl+C or no tasks remain

## Advanced: Manual Queue Management

```bash
# View JSON of all tasks
python run.py supervisor status | python -m json.tool

# Find a specific task's details
python run.py supervisor status | jq '.[] | select(.id | startswith("013ac86f"))'

# Monitor continuously (requires separate window)
while true; do
  python run.py supervisor status | jq '.[0] | {status, attempts, error}'
  sleep 5
done
```

## Architecture Reminder

```
Your input
    ↓
Supervisor (queues task)
    ↓
Browser Team (starts providers)
    ↓
ChatGPT/Gemini provider (executes in browser)
    ↓
Result extracted and verified
    ↓
Supervisor marks complete or awaiting_recovery
    ↓
(Loop for next task)
```

## Getting Help

```bash
# General supervisor help
python run.py supervisor --help

# Browser team operations
python run.py browser-team --help

# Check browser inventory
python run.py browser-team inventory

# Read current board state
python run.py browser-team status

# Detailed diagnostics
python run.py browser-team doctor
```

## Important: What This System Is NOT

- ❌ It's not calling a cloud API (it uses browser automation)
- ❌ It's not sending tasks to OpenAI/Google (it uses installed browser profiles)
- ❌ It doesn't work without a browser (it needs Chrome/Chromium with ChatGPT/Gemini logged in)
- ❌ It's not instant (LLMs take time; 30-120 seconds per task is typical)

## What It Is

- ✅ A local browser automation system using ChatGPT/Gemini as reasoning engines
- ✅ A persistent task queue that survives restarts
- ✅ A coordinator that detects and prevents duplicate work
- ✅ A progression system (queued → running → completed/awaiting_recovery/failed)

