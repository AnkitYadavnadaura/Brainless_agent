"""Grounded Windows UI actions for a browser team's bounded desktop workflow.

The accessibility script is runtime-owned. Model output can select observed IDs,
never supply scripts, process commands, or unobserved screen coordinates.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import time
from typing import Any

from app.agents.tools import RiskLevel, ToolSpec
from app.autonomy.models import ComputerState
from app.computer.desktop import WindowsApplicationLauncher
from app.safety.redaction import redact


_SNAPSHOT_SCRIPT = r"""$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]__HWND__)
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$queue = [System.Collections.Generic.Queue[object]]::new()
$queue.Enqueue($root)
$items = @()
$visited = 0
while ($queue.Count -gt 0 -and $visited -lt 250) {
    $node = $queue.Dequeue()
    $visited++
    try {
        $current = $node.Current
        if ($current.IsPassword -or $current.IsOffscreen) { continue }
        $rect = $current.BoundingRectangle
        $name = $current.Name
        if ($name.Length -gt 500) { $name = $name.Substring(0, 500) }
        $value = ''
        $pattern = $null
        if ($node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$pattern)) {
            $value = $pattern.Current.Value
        } elseif ($node.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$pattern)) {
            $value = $pattern.DocumentRange.GetText(2000)
        }
        if ($value.Length -gt 2000) { $value = $value.Substring(0, 2000) }
        if ($rect.Width -gt 0 -and $rect.Height -gt 0) {
            $items += @{ runtime_id = ($node.GetRuntimeId() -join '.'); name = $name;
                role = $current.ControlType.ProgrammaticName; text = $value;
                enabled = $current.IsEnabled; focused = $current.HasKeyboardFocus;
                bounds = @([int]$rect.Left, [int]$rect.Top, [int]$rect.Width, [int]$rect.Height) }
        }
        $child = $walker.GetFirstChild($node)
        $children = 0
        while ($null -ne $child -and $children -lt 250 -and $queue.Count -lt 500) {
            $queue.Enqueue($child)
            $child = $walker.GetNextSibling($child)
            $children++
        }
    } catch { continue }
}
ConvertTo-Json -InputObject @($items) -Depth 5 -Compress
"""

TOOL_SCHEMAS = {
    "team.desktop.launch": ("application",),
    "team.desktop.focus": ("window_id",),
    "team.desktop.click": ("target_id",),
    "team.desktop.type": ("target_id", "text"),
    "team.desktop.key": ("target_id", "key"),
}
LAUNCH_APPS = frozenset({"calculator", "notepad", "paint", "explorer", "settings"})
ALLOWED_KEYS = frozenset({"tab", "shift+tab", "escape", "enter", "up", "down", "left", "right", "home", "end"})
_UNSAFE_CONTEXT = ("powershell", "command prompt", "windows terminal", "developer tools", "devtools", "console prompt", "javascript", "python console")


class WindowsDesktopTeamController:
    """Pin an observed window across browser reasoning; validate again before input."""

    def __init__(self, backend=None, *, snapshot_reader=None, launcher=None):
        self._backend = backend
        self._snapshot_reader = snapshot_reader or self._read_accessibility
        self._launcher = launcher or WindowsApplicationLauncher()
        self._window: int | None = None
        self._identity = None
        self._targets: dict[str, dict[str, Any]] = {}
        self._windows: dict[str, tuple[int, Any]] = {}
        self._bound = None

    @property
    def backend(self):
        if self._backend is None:
            from app.browser.native_console import WindowsDesktopBackend
            self._backend = WindowsDesktopBackend()
        return self._backend

    @staticmethod
    def _read_accessibility(hwnd: int):
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             _SNAPSHOT_SCRIPT.replace("__HWND__", str(int(hwnd)))],
            capture_output=True, encoding="utf-8", shell=False, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode:
            raise RuntimeError("Windows accessibility observation is unavailable")
        items = json.loads(result.stdout)
        return items if isinstance(items, list) else [items]

    async def _serialized(self, function, *arguments):
        from app.browser.native_console import _DESKTOP_LOCK
        def work():
            with _DESKTOP_LOCK:
                return function(*arguments)
        running = asyncio.create_task(asyncio.to_thread(work))
        try:
            return await asyncio.shield(running)
        except asyncio.CancelledError:
            # A timed-out UI mutation must finish before another desktop user acts.
            try:
                await running
            except Exception:
                pass
            raise

    async def observe(self) -> ComputerState:
        return await self._serialized(self._observe)

    def _observe(self):
        windows = self.backend.windows()
        self._windows = {str(hwnd): (hwnd, self.backend.identity(hwnd)) for hwnd in windows}
        if self._window is None:
            self._window = self.backend.foreground()
            self._identity = self.backend.identity(self._window)
        if self._window not in windows or self.backend.identity(self._window) != self._identity:
            raise RuntimeError("The selected desktop window closed or changed identity; restart after selecting a window")
        items = self._snapshot_reader(self._window)
        targets = {}
        for raw in items[:200]:
            if not isinstance(raw, dict) or not raw.get("runtime_id"):
                continue
            ident = hashlib.sha256(f"{self._window}:{raw['runtime_id']}".encode()).hexdigest()[:16]
            targets[ident] = {"target_id": ident, "name": str(raw.get("name", ""))[:500],
                              "role": str(raw.get("role", "")), "text": str(raw.get("text", ""))[:2000],
                              "enabled": raw.get("enabled") is True, "bounds": raw.get("bounds")}
            targets[ident]["focused"] = raw.get("focused") is True
        self._targets = targets
        entries = [{"window_id": str(hwnd), "title": title[:200]} for hwnd, title in list(windows.items())[:40]]
        return ComputerState(active_application="desktop", active_window=windows[self._window],
            visible_ui=tuple(json.dumps(redact(item), ensure_ascii=True) for item in [
                {"windows": entries, "selected_window_id": str(self._window)}, *targets.values()]))

    def register_tools(self, registry):
        for tool_id, schema in TOOL_SCHEMAS.items():
            if registry.contains(tool_id):
                raise ValueError("A desktop-team controller is already registered in this application")
            async def handler(arguments, selected_tool=tool_id):
                return await self.execute(selected_tool, arguments)
            mutates = tool_id.rsplit(".", 1)[-1] in {"click", "type", "key"}
            permission = "keyboard.write" if tool_id.endswith((".type", ".key")) else "mouse.click" if tool_id.endswith(".click") else "window.control"
            registry.register(ToolSpec(tool_id, tool_id, "Select an observed Windows UI target; mutations require approval",
                frozenset({permission}), RiskLevel.HIGH if mutates else RiskLevel.MEDIUM,
                handler, schema, category="computer"))

    async def execute(self, action_type, arguments):
        return await self._serialized(self._execute, action_type, arguments)

    def bind_decision(self, decision, state):
        """Freeze the planning observation before runtime/approval observations."""
        arguments = decision["arguments"]
        self._bound = {"window": self._window, "identity": self._identity}
        if "target_id" in arguments:
            self._bound["target"] = dict(self._targets[arguments["target_id"]])
        if "window_id" in arguments:
            self._bound["focus"] = self._windows.get(arguments["window_id"])

    @staticmethod
    def _signature(target):
        return {key: value for key, value in target.items() if key != "focused"}

    def _execute(self, action_type, arguments):
        if action_type not in TOOL_SCHEMAS or set(arguments) != set(TOOL_SCHEMAS[action_type]):
            raise ValueError("Unsupported desktop tool or argument schema")
        operation = action_type.rsplit(".", 1)[-1]
        if operation == "launch":
            application = arguments["application"]
            if application not in LAUNCH_APPS:
                raise ValueError("Only named desktop applications can be launched")
            before = self.backend.foreground()
            self._launcher.launch(application)
            # Process launch completion does not imply that its window is ready.
            for _ in range(30):
                current = self.backend.foreground()
                titles = self.backend.windows()
                if current in titles and (current != before or application in titles[current].casefold()):
                    self._window, self._identity = current, self.backend.identity(current)
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Application launched but no target window was verified; observe windows before replanning")
            return {"launched": application}
        if operation == "focus":
            selected = self._bound.get("focus") if self._bound else self._windows.get(arguments["window_id"])
            if not selected or self.backend.identity(selected[0]) != selected[1]:
                raise ValueError("Window must come from a fresh observation")
            self.backend.focus(selected[0])
            if self.backend.foreground() != selected[0]:
                raise RuntimeError("Windows refused to focus the requested window")
            self._window, self._identity = selected
            return {"focused": str(self._window)}
        target = self._targets.get(arguments.get("target_id"))
        if not target:
            raise ValueError("Target must come from the current observed UI")
        before = dict(target)
        if self._bound:
            if (self._window, self._identity) != (self._bound["window"], self._bound["identity"]):
                raise ValueError("The selected window changed since planning")
            before = self._bound.get("target", before)
        self._observe()
        target = self._targets.get(arguments["target_id"])
        if not target or self._signature(target) != self._signature(before) or not target.get("enabled"):
            raise ValueError("The target changed or became unavailable; observe and replan")
        context = " ".join([self.backend.windows().get(self._window, ""), target["name"], target["role"]]).casefold()
        if any(term in context for term in _UNSAFE_CONTEXT):
            raise ValueError("Shell and developer-console input is outside the desktop workflow")
        if operation == "type":
            if target["role"] not in {"ControlType.Edit", "ControlType.Document"}:
                raise ValueError("Text input requires an observed editable control")
            text = arguments["text"]
            if not isinstance(text, str) or not text or len(text) > 4000 or any(ord(char) < 32 and char not in "\n\t\r" for char in text):
                raise ValueError("Text must contain 1..4000 ordinary characters")
        if operation == "key" and arguments["key"] not in ALLOWED_KEYS:
            raise ValueError("Unsupported key; arbitrary hotkeys are forbidden")
        bounds = target.get("bounds")
        if not isinstance(bounds, list) or len(bounds) != 4 or not all(type(v) is int for v in bounds):
            raise ValueError("Target lacks observed integer bounds")
        left, top, width, height = bounds
        if width <= 0 or height <= 0:
            raise ValueError("Target bounds are empty")
        x, y = left + width // 2, top + height // 2
        self.backend.focus(self._window)
        if self.backend.foreground() != self._window or not self.backend.point_in_window(self._window, x, y):
            raise RuntimeError("Target window is obscured or lost focus; input was withheld")
        self.backend.click(x, y)
        if operation == "click":
            return {"clicked": target["target_id"]}
        if self.backend.foreground() != self._window:
            raise RuntimeError("Window lost focus after the target click; keyboard input was withheld")
        self._observe()
        focused = self._targets.get(arguments["target_id"])
        if not focused or not focused["focused"]:
            raise RuntimeError("The requested control did not receive keyboard focus; input was withheld")
        if operation == "key":
            self.backend.hotkey(*arguments["key"].split("+"))
            return {"pressed": arguments["key"]}
        previous = self.backend.clipboard_read()
        try:
            self.backend.clipboard_write(arguments["text"])
            if self.backend.foreground() != self._window:
                raise RuntimeError("Window lost focus before paste; input was withheld")
            self.backend.hotkey("ctrl", "v")
            time.sleep(0.1)
        finally:
            if self.backend.clipboard_read() == arguments["text"]:
                self.backend.clipboard_write(previous)
        return {"typed_characters": len(arguments["text"])}
