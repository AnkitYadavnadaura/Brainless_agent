"""Send Gmail through a user-selected, owned installed-browser profile."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.browser.fleet_discovery import (
    BrowserInventory,
    discover_browsers,
    profile_launch_arguments,
)
from app.browser.methods import MethodUnavailable, run_methods
from app.browser.task_scripts import GMAIL_SEND


_SEND_GMAIL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class GmailWindow { [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow(); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd); }'
$payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__PAYLOAD__')) | ConvertFrom-Json
$handle = [IntPtr]::new([long]__HWND__)
$fgDeadline = [DateTime]::UtcNow.AddSeconds(5)
do {
    [GmailWindow]::SetForegroundWindow($handle) | Out-Null
    if ([GmailWindow]::GetForegroundWindow() -eq $handle) { break }
    Start-Sleep -Milliseconds 250
} while ([DateTime]::UtcNow -lt $fgDeadline)
if ([GmailWindow]::GetForegroundWindow() -ne $handle) { throw 'Owned Gmail window is not foreground' }
$root = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
function Nodes {
    $queue = [System.Collections.Generic.Queue[object]]::new()
    $queue.Enqueue($root)
    $result = [System.Collections.Generic.List[object]]::new()
    while ($queue.Count -gt 0 -and $result.Count -lt 4000) {
        $node = $queue.Dequeue()
        try {
            $current = $node.Current
            if (-not $current.IsOffscreen -and -not $current.IsPassword) { $result.Add($node) }
            $child = $walker.GetFirstChild($node)
            while ($null -ne $child -and $queue.Count -lt 4000) {
                $queue.Enqueue($child)
                $child = $walker.GetNextSibling($child)
            }
        } catch {}
    }
    return $result
}
function Find-One([string]$namePattern, [string[]]$types, [int]$timeoutSeconds = 12) {
    $deadline = [DateTime]::UtcNow.AddSeconds($timeoutSeconds)
    do {
        if ([GmailWindow]::GetForegroundWindow() -ne $handle) { [GmailWindow]::SetForegroundWindow($handle) | Out-Null }
        if ([GmailWindow]::GetForegroundWindow() -ne $handle) { throw 'Gmail window lost foreground ownership' }
        $matches = @()
        foreach ($node in (Nodes)) {
            $current = $node.Current
            if ($current.IsEnabled -and $types -contains $current.ControlType.ProgrammaticName -and
                $current.Name -match $namePattern) { $matches += $node }
        }
        if ($matches.Count -eq 1) { return $matches[0] }
        if ($matches.Count -gt 1) { throw "Gmail control is ambiguous: $namePattern" }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Gmail control was not found: $namePattern"
}
function Invoke-Button([string]$namePattern) {
    if ([GmailWindow]::GetForegroundWindow() -ne $handle) { [GmailWindow]::SetForegroundWindow($handle) | Out-Null }
    if ([GmailWindow]::GetForegroundWindow() -ne $handle) { throw 'Gmail window lost foreground ownership' }
    $node = Find-One $namePattern @('ControlType.Button')
    $pattern = $null
    if (-not $node.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
        throw "Gmail button cannot be invoked: $namePattern"
    }
    $pattern.Invoke()
}
function Fill-Field([string]$namePattern, [string[]]$types, [string]$value) {
    if ([GmailWindow]::GetForegroundWindow() -ne $handle) { [GmailWindow]::SetForegroundWindow($handle) | Out-Null }
    if ([GmailWindow]::GetForegroundWindow() -ne $handle) { throw 'Gmail window lost foreground ownership' }
    $node = Find-One $namePattern $types
    $pattern = $null
    if ($node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$pattern)) {
        $pattern.SetValue($value)
        return
    }
    $node.SetFocus()
    $previous = [System.Windows.Forms.Clipboard]::GetDataObject()
    try {
        [System.Windows.Forms.Clipboard]::SetText($value)
        [System.Windows.Forms.SendKeys]::SendWait('^a')
        [System.Windows.Forms.SendKeys]::SendWait('^v')
    } finally {
        if ([System.Windows.Forms.Clipboard]::GetText() -eq $value) {
            if ($null -ne $previous) {
                [System.Windows.Forms.Clipboard]::SetDataObject($previous, $true)
            } else {
                [System.Windows.Forms.Clipboard]::Clear()
            }
        }
    }
}
function Read-Field([string]$namePattern, [string[]]$types) {
    $node = Find-One $namePattern $types 2
    $pattern = $null
    if ($node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$pattern)) {
        return $pattern.Current.Value
    }
    $pattern = $null
    if ($node.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$pattern)) {
        return $pattern.DocumentRange.GetText(20001).TrimEnd()
    }
    throw "Gmail draft field cannot be verified: $namePattern"
}
$sendClicked = $false
$stage = 'compose'
try {
    Invoke-Button '^Compose$'
    $stage = 'recipient'
    Fill-Field '^(To recipients|Recipients|To)$' @('ControlType.Edit','ControlType.Document') $payload.to
    $recipient = Find-One '^(To recipients|Recipients|To)$' @('ControlType.Edit','ControlType.Document') 2
    $recipient.SetFocus()
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    $stage = 'subject'
    Fill-Field '^Subject$' @('ControlType.Edit') $payload.subject
    $stage = 'body'
    Fill-Field '^Message Body$' @('ControlType.Edit','ControlType.Document') $payload.body
    $stage = 'draft_verification'
    if ((Read-Field '^Subject$' @('ControlType.Edit')) -ne $payload.subject) {
        throw 'Gmail subject did not match the approved draft'
    }
    $observedBody = (Read-Field '^Message Body$' @('ControlType.Edit','ControlType.Document')).Replace("`r`n", "`n")
    $expectedBody = ([string]$payload.body).Replace("`r`n", "`n")
    if ($observedBody -ne $expectedBody) { throw 'Gmail body did not match the approved draft' }
    $stage = 'recipient_verification'
    $chipDeadline = [DateTime]::UtcNow.AddSeconds(5)
    $recipientConfirmed = $false
    do {
        foreach ($node in (Nodes)) {
            if ($node.Current.Name -eq $payload.to) { $recipientConfirmed = $true; break }
        }
        if (-not $recipientConfirmed) { Start-Sleep -Milliseconds 200 }
    } while (-not $recipientConfirmed -and [DateTime]::UtcNow -lt $chipDeadline)
    if (-not $recipientConfirmed) { throw 'Gmail did not confirm the exact recipient in the draft' }
    $stage = 'send'
    $sendButton = Find-One '^Send(?:\s*\(.*\))?$' @('ControlType.Button')
    $sendPattern = $null
    if (-not $sendButton.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$sendPattern)) {
        throw 'Gmail send button cannot be invoked'
    }
    $sendClicked = $true
    $sendPattern.Invoke()
    $stage = 'send_confirmation'
    $toastDeadline = [DateTime]::UtcNow.AddSeconds(15)
    $sent = $false
    do {
        foreach ($node in (Nodes)) {
            if ($node.Current.Name -match 'Message sent') { $sent = $true; break }
        }
        if (-not $sent) { Start-Sleep -Milliseconds 250 }
    } while (-not $sent -and [DateTime]::UtcNow -lt $toastDeadline)
    if (-not $sent) { throw 'Send was activated but Gmail confirmation was not observed' }
    @{ok=$true;sent=$true} | ConvertTo-Json -Compress
} catch {
    if ($stage -eq 'compose') {
        foreach ($node in (Nodes)) {
            if ($node.Current.Name -match 'Sign in|Choose an account') {
                $stage = 'login_required'
                break
            }
        }
    }
    @{ok=$false;sent=$sendClicked;error=$stage} | ConvertTo-Json -Compress
    exit 1
}
"""


class ExternalGmailProfiles:
    """Discover profiles and send only in a fresh, explicitly selected profile."""

    def __init__(self, root: Path, *,
                 discover: Callable[..., BrowserInventory] = discover_browsers,
                 transport_factory: Callable[[], Any] | None = None,
                 ui_runner: Callable[[int, dict[str, str]], dict[str, object]] | None = None) -> None:
        self.root = Path(root)
        self._discover = discover
        self._transport_factory = transport_factory
        self._transport = None
        self._ui_runner = ui_runner or self._run_ui
        self._windows: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self.last_method_attempts: list[dict] = []
        self._last_window: int | None = None

    def diagnostics(self) -> dict:
        """Expose bounded execution metadata, never message payloads or clipboard text."""
        console = getattr(self._transport, 'console_diagnostics', {}) if self._transport else {}
        return {'methods': list(self.last_method_attempts),
                'console': console.get(self._last_window, {}) if isinstance(console, dict) else {}}

    def inventory(self) -> BrowserInventory:
        return self._discover(managed_profile=self.root / "data/browser-profile")

    def catalog(self) -> list[dict[str, str]]:
        inventory = self.inventory()
        browsers = {item.id: item for item in inventory.browsers}
        return [
            {
                "id": profile.id,
                "browser": browsers[profile.browser_id].name,
                "name": profile.name,
                "label": f"{browsers[profile.browser_id].name} — {profile.name}",
            }
            for profile in inventory.profiles
            if profile.browser_id in browsers
        ]

    def _get_transport(self) -> Any:
        if self._transport is None:
            factory = self._transport_factory
            if factory is None:
                from app.browser.native_console import NativeConsoleTransport
                factory = NativeConsoleTransport
            self._transport = factory()
        return self._transport

    def _selected_profile(self, profile_id: str, profile_label: str):
        inventory = self.inventory()
        browsers = {item.id: item for item in inventory.browsers}
        profiles = {item.id: item for item in inventory.profiles}
        profile = profiles.get(profile_id)
        browser = browsers.get(profile.browser_id) if profile else None
        if profile is None or browser is None:
            raise ValueError("The selected browser profile is no longer available; choose again")
        expected_label = f"{browser.name} — {profile.name}"
        if profile_label != expected_label:
            raise ValueError("The selected browser profile label no longer matches discovery")
        return browser, profile

    async def _get_owned_window(self, profile_id: str, browser, profile):
        transport = self._get_transport()
        hwnd = self._windows.get(profile_id)
        if hwnd is not None and not await transport.window_alive(hwnd):
            del self._windows[profile_id]
            hwnd = None
        if hwnd is None:
            marker = "Brainless-Team-" + uuid.uuid4().hex
            marker_url = "data:text/html," + quote(
                f"<!doctype html><title>{marker}</title><p>Browser team starting</p>",
                safe="",
            )
            arguments = profile_launch_arguments(browser, profile, [marker_url])
            hwnd = await transport.launch(arguments, marker)
            self._windows[profile_id] = hwnd
        self._last_window = hwnd
        return transport, hwnd

    async def open_gmail(self, profile_id: str, profile_label: str) -> str:
        browser, profile = self._selected_profile(profile_id, profile_label)
        async with self._lock:
            transport, hwnd = await self._get_owned_window(profile_id, browser, profile)
            await transport.navigate_gmail(hwnd)
        return f"Opened Gmail using {browser.name} / {profile.name}"

    async def send(self, profile_id: str, profile_label: str, recipient: str,
                   subject: str, body: str) -> str:
        browser, profile = self._selected_profile(profile_id, profile_label)

        async with self._lock:
            transport, hwnd = await self._get_owned_window(profile_id, browser, profile)
            await transport.navigate_gmail(hwnd)
            payload = {"to": recipient, "subject": subject, "body": body}

            async def accessibility():
                result = await transport.run_owned_operation(hwnd, self._ui_runner, payload)
                self._verify_send_result(result)

            async def dom():
                result = await transport.evaluate(
                    hwnd, browser.family, GMAIL_SEND.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=True)),
                    timeout_seconds=30)
                self._verify_send_result(result)

            methods = [("accessibility", accessibility)]
            if callable(getattr(transport, "evaluate", None)):
                methods.append(("dom", dom))
            self.last_method_attempts = []
            await run_methods(methods, attempts=self.last_method_attempts)
            return f"Email sent to {recipient} using {browser.name} / {profile.name}"

    @staticmethod
    def _verify_send_result(result) -> None:
        if isinstance(result, dict) and result.get("ok") is True and result.get("sent") is True:
            return
        # Only an explicit pre-send failure permits another method. Timeouts,
        # malformed receipts, and anything after Send must never replay an email.
        if not isinstance(result, dict) or result.get("sent") is not False:
            raise RuntimeError("Gmail send outcome is uncertain; check the Sent folder before retrying")
        if result.get("error") == "login_required":
            raise RuntimeError(
                "Gmail needs a manual sign-in or account selection in the chosen profile; complete it, then retry")
        raise MethodUnavailable("Gmail did not confirm the email was sent: "
                                + str(result.get("error", "external browser interaction failed"))[:300])

    @staticmethod
    def _run_ui(hwnd: int, payload: dict[str, str]) -> dict[str, object]:
        if os.name != "nt":
            raise RuntimeError("External Gmail profile control requires Windows")
        encoded_payload = base64.b64encode(
            json.dumps(payload, ensure_ascii=True).encode("utf-8")).decode("ascii")
        script = (_SEND_GMAIL_SCRIPT
                  .replace("__PAYLOAD__", encoded_payload)
                  .replace("__HWND__", str(int(hwnd))))
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
                capture_output=True, encoding="utf-8", shell=False, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                "Gmail send outcome is uncertain; check the Sent folder before retrying") from error
        try:
            response = json.loads(result.stdout.strip())
        except (ValueError, TypeError) as error:
            raise RuntimeError(
                "Gmail send outcome is uncertain; check the Sent folder before retrying") from error
        if not isinstance(response, dict):
            raise RuntimeError("Gmail UI automation returned an invalid result")
        if result.returncode != 0 and response.get("ok") is True:
            raise RuntimeError(
                "Gmail send outcome is uncertain; check the Sent folder before retrying")
        return response
