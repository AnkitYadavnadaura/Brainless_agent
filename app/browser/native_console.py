"""Serialized native control of explicitly owned browser windows on Windows.

Only runtime-owned JavaScript expressions belong in ``evaluate``. Model replies
are data and must never be passed as scripts, hotkeys, or process arguments.
There is no remote-debugging port and no access to profile secrets here.
"""
from __future__ import annotations

import asyncio
import ctypes
import hashlib
import json
import math
import os
import re
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from urllib.parse import urlsplit

from app.providers.base_provider import ProviderError, UserInterventionRequired
from app.browser.url_validation import normalize_web_url
from app.computer.ocr import OcrReader, OcrUnavailable
from app.safety.redaction import redact
from app.browser.console_protocol import wrap_console_expression, parse_console_receipt
from app.browser.dom_observation import OBSERVE_DOM, ACT_DOM


_DESKTOP_LOCK = threading.Lock()
_BROWSER_SUFFIXES = (
    "Google Chrome", "Microsoft Edge", "Brave", "Chromium", "Mozilla Firefox",
    "Firefox", "Vivaldi", "Opera", "Opera GX",
)
_PROVIDER_HOSTS = frozenset({"chatgpt.com", "chat.openai.com", "gemini.google.com"})
_WINDOW_FOCUS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$fleetHandle)
$root.SetFocus()
"""
_CONSOLE_ACCESSIBILITY_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$node = [System.Windows.Automation.AutomationElement]::FocusedElement
$items = @()
for ($i = 0; $i -lt 12 -and $null -ne $node; $i++) {
    $items += @{ name = $node.Current.Name; type = $node.Current.ControlType.ProgrammaticName }
    $node = [System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($node)
}
ConvertTo-Json -InputObject $items -Compress
"""

_CONSOLE_RECEIPT_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$fleetHandle)
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$candidate = [System.Windows.Automation.AutomationElement]::FocusedElement
$searchRoot = $root
for ($depth=0; $depth -lt 12 -and $null -ne $candidate; $depth++) {
    if ($candidate.Current.NativeWindowHandle -eq $fleetHandle) { break }
    if ($candidate.Current.Name -match '^(Console|Console panel|Console messages)$') { $searchRoot=$candidate }
    $candidate = $walker.GetParent($candidate)
}
$queue = [System.Collections.Generic.Queue[object]]::new()
$queue.Enqueue($searchRoot)
$deadline = [DateTime]::UtcNow.AddSeconds(2)
$count = 0
while ($queue.Count -gt 0 -and $count -lt 1000 -and [DateTime]::UtcNow -lt $deadline) {
    $node = $queue.Dequeue()
    $count++
    try {
        if (-not $node.Current.IsPassword) {
            $name = $node.Current.Name
            $position = $name.IndexOf($fleetPrefix, [StringComparison]::Ordinal)
            if ($position -ge 0) {
                @{receipt=$name.Substring($position)} | ConvertTo-Json -Compress
                exit
            }
        }
        $child = $walker.GetFirstChild($node)
        while ($null -ne $child -and $queue.Count -lt 1000) {
            $queue.Enqueue($child)
            $child = $walker.GetNextSibling($child)
        }
    } catch [System.Windows.Automation.ElementNotAvailableException] { continue }
}
@{receipt=''} | ConvertTo-Json -Compress
"""

# Inspect only the explicitly owned window. Values are read only from named
# browser address bars and chat composers, never password or arbitrary inputs.
_PAGE_ACCESSIBILITY_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class FleetDpi { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow(); }'
[void][FleetDpi]::SetProcessDPIAware()
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$fleetHandle)
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
function RuntimeId($node) { return (($node.GetRuntimeId()) -join '.') }
if ($fleetMode -eq 'point' -or $fleetMode -eq 'focused' -or $fleetMode -eq 'address') {
    if ($fleetMode -eq 'point') {
        $node = [System.Windows.Automation.AutomationElement]::FromPoint([System.Windows.Point]::new($fleetX,$fleetY))
    } else { $node = [System.Windows.Automation.AutomationElement]::FocusedElement }
    $hitType = if ($null -ne $node) { $node.Current.ControlType.ProgrammaticName } else { '' }
    $addressValue = $null
    $addressFocused = $false
    if ($fleetMode -eq 'address' -and $null -ne $node -and -not $node.Current.IsPassword -and $hitType -eq 'ControlType.Edit' -and
        $node.Current.Name -in @('Address and search bar','Search or enter address','Search or enter web address','Search with Google or enter address')) {
        $pattern=$null
        if ($node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)) {
            $addressValue=$pattern.Current.Value
            $addressFocused=$true
        }
    }
    $hitRect = if ($null -ne $node) { $r=$node.Current.BoundingRectangle; @($r.X,$r.Y,$r.Width,$r.Height) } else { @() }
    $ids = @()
    for ($depth=0; $depth -lt 40 -and $null -ne $node; $depth++) {
        $ids += (RuntimeId $node)
        if ($node.Current.NativeWindowHandle -eq $fleetHandle) { break }
        $node = $walker.GetParent($node)
    }
    ConvertTo-Json -InputObject @{ancestors=$ids;hit_type=$hitType;hit_rect=$hitRect;address_focused=$addressFocused;address_value=$addressValue;owned=($null -ne $node -and $node.Current.NativeWindowHandle -eq $fleetHandle)} -Compress
    exit
}
$addresses = @('Address and search bar','Search or enter address','Search or enter web address','Search with Google or enter address')
$composers = @('Ask anything','Message ChatGPT','Chat with ChatGPT','Send a message','Enter a prompt here','Enter a prompt','Enter a prompt for Gemini','Type a prompt here','Ask Gemini')
$sendNames = @('Send prompt','Send message','Send')
$queue = [System.Collections.Generic.Queue[object]]::new()
$queue.Enqueue(@{node=$root;parent=-1})
$items = [System.Collections.Generic.List[object]]::new()
$url = ''
$incomplete = $false
while ($queue.Count -gt 0 -and $items.Count -lt 2500) {
    $entry = $queue.Dequeue()
    $node = $entry.node
    try {
        $current=$node.Current
        $name=$current.Name
        $type=$current.ControlType.ProgrammaticName
        $rect=$current.BoundingRectangle
        $id=$items.Count
        $value=$null
        $editable=($type -eq 'ControlType.Edit')
        $editablePattern=$null
        if (-not $current.IsPassword -and $node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$editablePattern)) {
            $editable=$editable -or -not $editablePattern.Current.IsReadOnly
        }
        if (($fleetMode -in @('focus_composer','invoke_send','copy_response','copy_message')) -and (RuntimeId $node) -eq $fleetRuntimeId) {
            if ([FleetDpi]::GetForegroundWindow() -ne [IntPtr]$fleetHandle -or $current.IsPassword -or
                ($current.IsOffscreen -and $fleetMode -notin @('copy_response','copy_message')) -or -not $current.IsEnabled) {
                throw 'Owned chat control is no longer available'
            }
            if ($fleetMode -eq 'focus_composer' -and $composers -contains $name -and $type -in @('ControlType.Edit','ControlType.Document')) {
                $node.SetFocus()
                ConvertTo-Json -InputObject @{acted=$true} -Compress
                exit
            }
            if ((($fleetMode -eq 'invoke_send' -and $sendNames -contains $name) -or
                 ($fleetMode -eq 'copy_response' -and $name -in @('Copy response','Copy','Copy text')) -or
                 ($fleetMode -eq 'copy_message' -and $name -eq 'Copy message')) -and $type -eq 'ControlType.Button') {
                $invoke=$null
                if ($node.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)) {
                    $invoke.Invoke()
                    ConvertTo-Json -InputObject @{acted=$true} -Compress
                    exit
                }
            }
            ConvertTo-Json -InputObject @{acted=$false} -Compress
            exit
        }
        if (-not $current.IsPassword -and ($addresses -contains $name -or $composers -contains $name)) {
            $pattern=$null
            if ($node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)) {
                $value=$pattern.Current.Value
            } elseif ($composers -contains $name) {
                if ($node.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern,[ref]$pattern)) {
                    $value=$pattern.DocumentRange.GetText(128001)
                }
            }
            if ($addresses -contains $name -and $type -eq 'ControlType.Edit') { $url=$value }
        }
        $items.Add(@{id=$id;parent=$entry.parent;name=$name;type=$type;runtime_id=(RuntimeId $node);
            enabled=$current.IsEnabled;offscreen=$current.IsOffscreen;focused=$current.HasKeyboardFocus;
            password=$current.IsPassword;editable=$editable;
            rect=@($rect.X,$rect.Y,$rect.Width,$rect.Height);value=$value})
        $child=$walker.GetFirstChild($node)
        while ($null -ne $child) {
            $queue.Enqueue(@{node=$child;parent=$id})
            $child=$walker.GetNextSibling($child)
        }
    } catch [System.Windows.Automation.ElementNotAvailableException] {
        $incomplete = $true
        continue
    } catch { throw }
}
if ($fleetMode -eq 'snapshot') {
    ConvertTo-Json -InputObject @{url=$url;nodes=$items.ToArray();truncated=($queue.Count -gt 0 -or $incomplete)} -Depth 6 -Compress
} else { ConvertTo-Json -InputObject @{acted=$false} -Compress }
"""

_COMPOSER_NAMES = {
    'chatgpt': {'ask anything', 'message chatgpt', 'chat with chatgpt', 'send a message'},
    'gemini': {'enter a prompt here', 'enter a prompt', 'enter a prompt for gemini', 'type a prompt here', 'ask gemini'},
}
_SEND_NAMES = {'chatgpt': {'send prompt', 'send message'}, 'gemini': {'send message', 'send'}}
_ASSISTANT_NAMES = {'chatgpt': {'chatgpt said', 'assistant'}, 'gemini': {'gemini said', 'gemini response'}}


def _accessible_page(snapshot: dict, provider: str) -> dict:
    """Extract only explicit chat controls/assistant groups from a bounded tree.

    Unknown/localized page layouts fail closed. An arbitrary text node, user
    prompt, or old answer changing text is never proof of a new assistant turn.
    """
    nodes = snapshot.get('nodes', [])
    if (snapshot.get('truncated') or not isinstance(nodes, list) or len(nodes) > 2500
            or any(not isinstance(item, dict) for item in nodes)):
        return {'error': 'accessibility_incomplete'}
    visible = [item for item in nodes if isinstance(item, dict) and not item.get('offscreen')]
    named = lambda item: str(item.get('name', '')).strip().rstrip(':').casefold()
    composers = [item for item in visible if named(item) in _COMPOSER_NAMES[provider]
                 and item.get('type') in {'ControlType.Edit', 'ControlType.Document'} and item.get('enabled')]
    buttons = [item for item in visible if item.get('type') == 'ControlType.Button']
    response_buttons = [item for item in nodes if item.get('type') == 'ControlType.Button']
    copy_controls = {}
    send = [item for item in buttons if named(item) in _SEND_NAMES[provider] and item.get('enabled')]
    busy = any(named(item) in {'stop generating', 'stop response', 'stop', 'stop streaming'} for item in buttons)
    labels = {named(item) for item in visible}
    # Coordination prompts mention CAPTCHA/MFA as constraints. Those words in
    # conversation prose are not evidence of an authentication challenge.
    challenge_labels = {'verify you are human', 'verify you are a human', 'verify you’re human',
                        'verify you are human by completing the action below', 'captcha', 'recaptcha',
                        "i'm not a robot", 'i’m not a robot', 'verification code',
                        'two-step verification', 'complete the captcha'}
    if any(name.rstrip('.!') in challenge_labels for name in labels):
        return {'error': 'challenge'}
    # Anonymous ChatGPT/Gemini can expose a working composer. A visible login
    # control still means this tab is not a signed-in team member.
    if any(named(item) in {'log in', 'login', 'sign in'} for item in visible
           if item.get('type') in {'ControlType.Button', 'ControlType.Hyperlink'}):
        return {'error': 'login'}
    if any(name.startswith(('too many requests', 'you have reached your limit', 'usage limit reached')) for name in labels):
        return {'error': 'rate_limit'}
    # Reply history is read from the loaded accessibility tree, including the
    # portions scrolled outside the viewport. Input targets still use visible.
    groups = [item for item in nodes if named(item) in _ASSISTANT_NAMES[provider]
              and item.get('type') in {'ControlType.Group', 'ControlType.Document'}]
    if not groups and provider == 'chatgpt':
        # Current ChatGPT exposes the answer as an unnamed/text-named Group
        # followed by its own Response actions group (Copy response, Rate
        # response). Bind this structural pair; never take arbitrary page text.
        for actions in nodes:
            if named(actions) != 'response actions' or actions.get('type') != 'ControlType.Group':
                continue
            controls = [item for item in response_buttons if item.get('parent') == actions.get('id')]
            control_names = {named(item) for item in controls}
            if ('rate response' not in control_names
                    or not control_names.intersection({'copy response', 'copied', 'copied!'})):
                continue
            siblings = [item for item in nodes if item.get('parent') == actions.get('parent')
                        and item.get('id', -1) < actions.get('id', -1)]
            # Chromium can flatten an older offscreen reply from Group into
            # Text. It is still the same assistant turn, authenticated by its
            # own response-action footer; ignoring it makes counts stop growing.
            if siblings and siblings[-1].get('type') in {'ControlType.Group', 'ControlType.Text'}:
                groups.append(siblings[-1])
                copies = [item for item in controls if named(item) == 'copy response']
                if len(copies) == 1:
                    copy_controls[siblings[-1]['id']] = copies[0]
    if not groups and provider == 'gemini':
        # Gemini's author label is accessibility-only Text. Its sibling holds
        # the answer; Good/Bad response buttons belong to the enclosing turn.
        # All three structural anchors are required, even though the label is
        # offscreen. A user typing "Gemini said" is not an assistant response.
        by_id = {item.get('id'): item for item in nodes if isinstance(item, dict)}
        def belongs(item, ancestor):
            for _ in range(40):
                parent = item.get('parent')
                if parent == ancestor:
                    return True
                item = by_id.get(parent, {})
                if not item:
                    break
            return False
        for label in nodes:
            if (named(label) != 'gemini said' or label.get('type') != 'ControlType.Text'
                    or not label.get('offscreen')):
                continue
            heading = by_id.get(label.get('parent'), {})
            content = by_id.get(heading.get('parent'), {})
            turn = by_id.get(content.get('parent'), {})
            if any(item.get('type') != 'ControlType.Group' for item in (heading, content, turn)):
                continue
            controls = {named(item) for item in response_buttons if belongs(item, turn.get('id'))}
            candidates = [item for item in nodes if item.get('parent') == content.get('id')
                          and item.get('id', -1) > heading.get('id', -1) and item.get('type') == 'ControlType.Group']
            if {'good response', 'bad response'} <= controls and len(candidates) == 1:
                groups.append(candidates[0])
                copies = [item for item in response_buttons if named(item) in {'copy', 'copy response', 'copy text'}
                          and belongs(item, turn.get('id'))]
                if len(copies) == 1:
                    copy_controls[candidates[0]['id']] = copies[0]
    selector = 'uia:' + provider + ':assistant'
    text = ''
    user_copy = None
    if groups:
        group = groups[-1]
        if provider == 'chatgpt':
            footers = [item for item in nodes if item.get('parent') == group.get('parent')
                       and item.get('id', -1) < group.get('id', -1)
                       and named(item) == 'your message actions' and item.get('type') == 'ControlType.Group']
            if footers:
                controls = [item for item in response_buttons if item.get('parent') == footers[-1]['id']]
                copies = [item for item in controls if named(item) == 'copy message']
                if len(copies) == 1 and any(named(item) == 'edit message' for item in controls):
                    user_copy = copies[0]
        children = {}
        for item in nodes:
            children.setdefault(item.get('parent'), []).append(item)
        pieces = []
        stack = ([group] if group.get('type') == 'ControlType.Text'
                 else list(reversed(children.get(group.get('id'), []))))
        seen = set()
        # The snapshot is breadth-first. Reading it in that order can put the
        # closing JSON brace before nested lines. Walk each subtree in UI order.
        while stack:
            item = stack.pop()
            if item.get('id') in seen:
                continue
            seen.add(item.get('id'))
            if item.get('type') == 'ControlType.Text':
                value = str(item.get('name', '')).strip()
                if value and named(item) not in _ASSISTANT_NAMES[provider]:
                    pieces.append(value)
            else:
                stack.extend(reversed(children.get(item.get('id'), [])))
        text = '\n'.join(pieces)
    if len(text) > 128_000:
        return {'error': 'response_too_large'}
    return dict(url=snapshot.get('url', ''), ready=len(composers) == 1, busy=busy,
                composer=composers[0] if len(composers) == 1 else None,
                send=send[0] if len(send) == 1 else None, text=text, selector=selector,
                copy_response=copy_controls.get(groups[-1]['id']) if groups else None,
                user_copy=user_copy,
                count=len(groups), snapshots={selector: {'count': len(groups)}}, channel='accessibility')


class NativeTransportError(ProviderError):
    """A failed operation; ``submitted`` marks a possibly executed expression."""

    def __init__(self, message: str, *, submitted: bool = False) -> None:
        super().__init__(message)
        self.submitted = submitted


class NativeAccessibilityError(NativeTransportError):
    """The read-only UIA observation failed; another observation method may be used."""


class NativeLaunchError(NativeTransportError):
    """A launch failure with evidence about whether a window could have opened."""

    def __init__(self, message: str, *, launched: bool = True) -> None:
        super().__init__(message)
        self.launched = launched


class NativeConsoleIntervention(UserInterventionRequired):
    """Console setup or uncertain execution needs the owner, without replay."""

    def __init__(self, message: str, *, submitted: bool = False) -> None:
        super().__init__(message)
        self.submitted = submitted


def _marker_title(title: str, marker: str) -> bool:
    # Edge inserts a zero-width space in its brand and a profile label between
    # the page title and browser name. Keep the entire nonce boundary exact.
    title = title.replace('\u200b', '')
    if title == marker:
        return True
    separators = (' - ', ' \u2014 ', ' \u2013 ')
    if any(
        title == marker + separator + suffix
        for separator in separators
        for suffix in _BROWSER_SUFFIXES
    ):
        return True
    for sep1 in separators:
        for sep2 in separators:
            prefix, suffix = marker + sep1, sep2 + 'Microsoft Edge'
            if title.startswith(prefix) and title.endswith(suffix):
                profile = title[len(prefix):-len(suffix)]
                if bool(profile.strip()) and len(profile) <= 200 and all(ord(c) >= 32 for c in profile):
                    return True
    return False


def _console_accessible(items: object) -> bool:
    """Require the focused console input, not merely a page mentioning it."""
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        return False
    focused = items[0]
    name = str(focused.get("name", "")).strip().casefold()
    control = str(focused.get("type", ""))
    input_control = control in {"ControlType.Edit", "ControlType.Document", "ControlType.Custom"}
    exact = name in {
        "console prompt", "console input", "web console input",
        "javascript expression to evaluate", "javascript input",
    }
    if input_control and exact:
        return True
    # Firefox versions sometimes expose a document named 'Web Console'.
    ancestors = [str(item.get("name", "")).casefold() for item in items[1:] if isinstance(item, dict)]
    return input_control and name == "web console" and any("developer tools" in item for item in ancestors)


class WindowsDesktopBackend:
    """Small injectable Win32/clipboard/input adapter; imports desktop deps lazily."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise NativeTransportError("Native browser control requires Windows")
        from ctypes import wintypes
        import pyautogui
        import pyperclip

        self.input, self.clipboard = pyautogui, pyperclip
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL
        self.user32.BringWindowToTop.argtypes = [wintypes.HWND]
        self.user32.BringWindowToTop.restype = wintypes.BOOL
        self.user32.AttachThreadInput.argtypes = [
            wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        self.user32.AttachThreadInput.restype = wintypes.BOOL
        self.user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                            ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.WindowFromPoint.argtypes = [wintypes.POINT]
        self.user32.WindowFromPoint.restype = wintypes.HWND
        self.user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user32.GetAncestor.restype = wintypes.HWND
        self.user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                                   wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
                                                   ctypes.POINTER(ctypes.c_size_t)]
        self.user32.SendMessageTimeoutW.restype = wintypes.LPARAM
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    def windows(self) -> dict[int, str]:
        from ctypes import wintypes
        result = {}
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def collect(hwnd, _):
            if self.user32.IsWindowVisible(hwnd):
                size = self.user32.GetWindowTextLengthW(hwnd)
                if size:
                    title = ctypes.create_unicode_buffer(size + 1)
                    self.user32.GetWindowTextW(hwnd, title, size + 1)
                    result[int(hwnd)] = title.value
            return True

        callback = callback_type(collect)
        self.user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        if not self.user32.EnumWindows(callback, 0):
            raise NativeTransportError("Could not inspect native browser windows")
        return result

    def spawn(self, argv: list[str]) -> None:
        subprocess.Popen(argv, shell=False)

    def identity(self, hwnd: int) -> tuple[int, str] | None:
        from ctypes import wintypes
        if not self.user32.IsWindow(hwnd):
            return None
        process = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process))
        name = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, name, 256)
        return process.value, name.value

    def focus(self, hwnd: int) -> None:
        identity = self.identity(hwnd)
        if identity is None:
            return
        if self.foreground() == hwnd:
            return
        self.user32.ShowWindow(hwnd, 9)  # SW_RESTORE; never target arbitrary titles.
        self.user32.SetForegroundWindow(hwnd)
        if self._wait_for_foreground(hwnd, identity):
            return
        if self._activate_with_attached_input(hwnd, identity):
            return
        # Windows may deny background SetForegroundWindow even for our owned
        # browser. Ask its accessibility provider to focus it with a bounded
        # subprocess; never simulate keys in the currently active application.
        try:
            subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                 f'$fleetHandle={int(hwnd)};\n' + _WINDOW_FOCUS_SCRIPT],
                shell=False, capture_output=True, timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            pass
        if not self._wait_for_foreground(hwnd, identity) and self.identity(hwnd) == identity:
            # Make this owned window visible in Z order without activating it.
            # A subsequent verified caption click is ordinary desktop input.
            was_topmost = bool(self.user32.GetWindowLongW(hwnd, -20) & 0x0008)
            try:
                self.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0053)
                self._focus_caption(hwnd, identity)
                self._wait_for_foreground(hwnd, identity)
            finally:
                if not was_topmost and self.identity(hwnd) == identity:
                    self.user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0013)

    def _activate_with_attached_input(self, hwnd: int, identity) -> bool:
        """Retry foreground activation with the Windows input queues attached."""
        kernel32 = getattr(self, "kernel32", None)
        attach_thread_input = getattr(self.user32, "AttachThreadInput", None)
        bring_window_to_top = getattr(self.user32, "BringWindowToTop", None)
        if (kernel32 is None or attach_thread_input is None
                or bring_window_to_top is None or self.identity(hwnd) != identity):
            return False
        current_thread = kernel32.GetCurrentThreadId()
        foreground = self.foreground()
        foreground_thread = 0
        target_thread = 0
        if foreground:
            foreground_thread = self.user32.GetWindowThreadProcessId(
                foreground, None)
        target_thread = self.user32.GetWindowThreadProcessId(hwnd, None)
        attached = []
        try:
            for thread_id in dict.fromkeys((foreground_thread, target_thread)):
                if thread_id and thread_id != current_thread:
                    if not attach_thread_input(current_thread, thread_id, True):
                        continue
                    attached.append(thread_id)
            if self.identity(hwnd) != identity:
                return False
            bring_window_to_top(hwnd)
            self.user32.SetForegroundWindow(hwnd)
            return self._wait_for_foreground(hwnd, identity)
        finally:
            for thread_id in reversed(attached):
                attach_thread_input(current_thread, thread_id, False)

    def _wait_for_foreground(self, hwnd: int, identity, timeout: float = 0.75) -> bool:
        deadline = time.monotonic() + timeout
        while self.identity(hwnd) == identity:
            if self.foreground() == hwnd:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.025)
        return False

    def _focus_caption(self, hwnd, identity):
        """Click only a freshly hit-tested, uncovered, inert owned title bar."""
        from ctypes import wintypes
        rect = wintypes.RECT()
        if identity is None or not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return
        # Custom Chromium title bars include tabs and buttons. WM_NCHITTEST
        # must identify HTCAPTION (2), never HTCLIENT or a caption button.
        for dy in (12, 24):
            for fraction in (0.5, 0.7, 0.3, 0.85):
                x, y = int(rect.left + (rect.right - rect.left) * fraction), rect.top + dy
                if not self.point_in_window(hwnd, x, y):
                    continue
                result = ctypes.c_size_t()
                coordinates = (x & 0xffff) | ((y & 0xffff) << 16)
                answered = self.user32.SendMessageTimeoutW(hwnd, 0x0084, 0, coordinates,
                                                          0x0002, 200, ctypes.byref(result))
                if (answered and result.value == 2 and self.identity(hwnd) == identity
                        and self.point_in_window(hwnd, x, y)):
                    self.click(x, y)
                    return

    def foreground(self) -> int:
        return int(self.user32.GetForegroundWindow() or 0)

    def hotkey(self, *keys: str) -> None:
        self.input.hotkey(*keys)

    def click(self, x: int, y: int) -> None:
        self.input.click(x, y)

    def point_in_window(self, hwnd: int, x: int, y: int) -> bool:
        from ctypes import wintypes
        rect = wintypes.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        if not (rect.left <= x < rect.right and rect.top <= y < rect.bottom):
            return False
        hit = self.user32.WindowFromPoint(wintypes.POINT(x, y))
        return bool(hit) and int(self.user32.GetAncestor(hit, 2) or 0) == hwnd

    def window_rect(self, hwnd: int) -> tuple[int, int, int, int]:
        """Physical screen bounds for this exact window, never a model rectangle."""
        from ctypes import wintypes
        rect = wintypes.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise NativeTransportError("Could not inspect the owned browser window bounds")
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top

    def clipboard_read(self) -> str:
        return str(self.clipboard.paste())

    def clipboard_write(self, value: str) -> None:
        self.clipboard.copy(value)

    def console_ready(self, hwnd: int, family: str) -> bool:
        if self.foreground() != hwnd:
            return False
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _CONSOLE_ACCESSIBILITY_SCRIPT],
                shell=False, capture_output=True, encoding="utf-8", timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return result.returncode == 0 and _console_accessible(json.loads(result.stdout)) and self.foreground() == hwnd
        except (OSError, subprocess.SubprocessError, ValueError):
            return False

    def console_focused(self, hwnd: int, family: str) -> bool:
        """Detect an already-focused console so opening it cannot toggle it closed."""
        return self.console_ready(hwnd, family)

    def _accessibility(self, hwnd: int, mode: str, x: int = 0, y: int = 0, runtime_id: str = '') -> dict:
        # All substitutions are runtime-owned integers or a fixed enum. Page
        # text and model output never become PowerShell source.
        if mode not in {'snapshot', 'point', 'focused', 'address', 'focus_composer', 'invoke_send', 'copy_response', 'copy_message'}:
            raise ValueError('Unknown accessibility operation')
        if runtime_id and not re.fullmatch(r'[-0-9.]{1,180}', runtime_id):
            raise ValueError('Invalid accessibility runtime ID')
        prefix = f"$fleetHandle={int(hwnd)}; $fleetMode='{mode}'; $fleetX={int(x)}; $fleetY={int(y)}; $fleetRuntimeId='{runtime_id}';\n"
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', prefix + _PAGE_ACCESSIBILITY_SCRIPT],
                shell=False, capture_output=True, encoding='utf-8', timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode or len(result.stdout) > 2_000_000:
                raise ValueError('Accessibility snapshot unavailable')
            value = json.loads(result.stdout)
            if not isinstance(value, dict):
                raise ValueError('Invalid accessibility snapshot')
            return value
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise NativeAccessibilityError(
                'Could not inspect the owned browser accessibility tree (' + type(error).__name__ + ')') from error

    def console_receipt(self, hwnd: int, nonce: str) -> str:
        """Read only the nonce-specific result printed inside the owned console."""
        if not re.fullmatch(r'[a-f0-9]{32}', nonce) or self.foreground() != hwnd:
            return ''
        prefix = f"$fleetHandle={int(hwnd)}; $fleetPrefix='BRAINLESS_RESULT:{nonce}:';\n"
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', prefix + _CONSOLE_RECEIPT_SCRIPT],
                shell=False, capture_output=True, encoding='utf-8', timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode or len(result.stdout) > 2_000_000 or self.foreground() != hwnd:
                return ''
            value = json.loads(result.stdout)
            return value.get('receipt', '') if isinstance(value, dict) else ''
        except (OSError, subprocess.SubprocessError, ValueError):
            return ''

    def accessibility_snapshot(self, hwnd: int) -> dict:
        return self._accessibility(hwnd, 'snapshot')

    def control_at(self, hwnd: int, x: int, y: int, runtime_id: str) -> bool:
        state = self._accessibility(hwnd, 'point', x, y)
        return bool(state.get('owned')) and runtime_id in state.get('ancestors', [])

    def focused_control(self, hwnd: int, runtime_id: str) -> bool:
        state = self._accessibility(hwnd, 'focused')
        return bool(state.get('owned')) and runtime_id in state.get('ancestors', [])

    def address_bar(self, hwnd: int) -> dict:
        return self._accessibility(hwnd, 'address')

    def focus_composer(self, hwnd: int, runtime_id: str) -> bool:
        return self._accessibility(hwnd, 'focus_composer', runtime_id=runtime_id).get('acted') is True

    def invoke_send(self, hwnd: int, runtime_id: str) -> bool:
        return self._accessibility(hwnd, 'invoke_send', runtime_id=runtime_id).get('acted') is True

    def copy_response(self, hwnd: int, runtime_id: str) -> bool:
        return self._accessibility(hwnd, 'copy_response', runtime_id=runtime_id).get('acted') is True

    def copy_message(self, hwnd: int, runtime_id: str) -> bool:
        return self._accessibility(hwnd, 'copy_message', runtime_id=runtime_id).get('acted') is True

    def close(self, hwnd: int) -> None:
        self.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE, only a recorded owned window.



EXTRACT_DOM_SCRIPT = (
    "(() => {"
    "  const interactiveTags = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];"
    "  const elements = [];"
    "  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);"
    "  let node;"
    "  while ((node = walker.nextNode())) {"
    "    const style = window.getComputedStyle(node);"
    "    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;"
    "    const rect = node.getBoundingClientRect();"
    "    if (rect.width <= 0 || rect.height <= 0) continue;"
    "    const isClickable = interactiveTags.includes(node.tagName) ||"
    "      node.getAttribute('role') === 'button' ||"
    "      node.getAttribute('role') === 'link' ||"
    "      node.onclick !== null ||"
    "      style.cursor === 'pointer';"
    "    if (isClickable || node.tagName === 'CANVAS') {"
    "      const text = (node.innerText || node.getAttribute('aria-label') || node.getAttribute('placeholder') || node.getAttribute('title') || node.value || '').trim();"
    "      elements.push({"
    "        tag: node.tagName.toLowerCase(),"
    "        role: node.getAttribute('role') || node.tagName.toLowerCase(),"
    "        text: text.slice(0, 100),"
    "        rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.width), Math.round(rect.height)],"
    "        selector: node.id ? '#' + node.id : (node.className ? node.tagName.toLowerCase() + '.' + String(node.className).trim().split(/\\s+/).slice(0, 2).join('.') : node.tagName.toLowerCase()),"
    "        visible: rect.bottom > 0 && rect.top < window.innerHeight && rect.right > 0 && rect.left < window.innerWidth"
    "      });"
    "      if (elements.length >= 100) break;"
    "    }"
    "  }"
    "  return {"
    "    url: window.location.href,"
    "    title: document.title,"
    "    viewport: [window.innerWidth, window.innerHeight],"
    "    scroll: [window.scrollX, window.scrollY],"
    "    elements: elements"
    "  };"
    "})()"
)

class NativeConsoleTransport:
    """One desktop input lane shared by every browser/profile/session instance.

    ``evaluate`` accepts a trusted JS *expression* resolving to a dictionary.
    ``tab_index`` selects provider tabs atomically with evaluation/navigation.
    Authentication and console paste protections always require manual setup.
    """

    def __init__(self, backend=None, *, launch_timeout: float = 20.0,
                 result_timeout: float = 12.0, settle_seconds: float = 0.35,
                 poll_seconds: float = 0.1) -> None:
        for name, value in (
            ('launch_timeout', launch_timeout), ('result_timeout', result_timeout),
            ('settle_seconds', settle_seconds), ('poll_seconds', poll_seconds),
        ):
            try:
                valid = (type(value) in (int, float) and math.isfinite(value)
                         and (value >= 0 if name == 'settle_seconds' else value > 0))
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f'{name} must be finite and {"nonnegative" if name == "settle_seconds" else "positive"}')
        self.backend = backend if backend is not None else WindowsDesktopBackend()
        self.launch_timeout, self.result_timeout = launch_timeout, result_timeout
        self.settle_seconds, self.poll_seconds = settle_seconds, poll_seconds
        self._owned: dict[int, object] = {}
        self._pending_launches: dict[str, set[int]] = {}
        self._uncertain: set[int] = set()
        self._uncertain_tabs: set[tuple[int, int]] = set()
        self._native_bindings: dict[tuple[int, int | None], dict] = {}
        self._web_observations: dict[int, dict[str, Any]] = {}
        self.console_diagnostics: dict[int, dict[str, Any]] = {}

    async def _serialized(self, operation, *args):
        def run():
            with _DESKTOP_LOCK:
                return operation(*args)

        # A cancelled coroutine must not release ownership while the thread is
        # still pressing keys. Finish its bounded operation before cancellation.
        task = asyncio.create_task(asyncio.to_thread(run))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # Shield every drain attempt too: cancellation can arrive again
            # during shutdown, and cancelling to_thread cannot stop its worker.
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not task.cancelled():
                # Retrieve failures even if completion raced with cancellation.
                task.exception()
            raise

    def _check_owned(self, hwnd: int) -> None:
        if hwnd not in self._owned or self.backend.identity(hwnd) != self._owned[hwnd]:
            raise NativeTransportError("Browser window is no longer an owned fleet window")

    def _is_uncertain(self, hwnd, tab_index):
        return hwnd in self._uncertain or (any(handle == hwnd for handle, _ in self._uncertain_tabs)
            if tab_index is None else (hwnd, tab_index) in self._uncertain_tabs)

    def _mark_uncertain(self, hwnd, tab_index):
        if tab_index is None:
            self._uncertain.add(hwnd)
        else:
            self._uncertain_tabs.add((hwnd, tab_index))

    def _forget_window(self, hwnd):
        self._owned.pop(hwnd, None)
        self._uncertain.discard(hwnd)
        self._uncertain_tabs = {key for key in self._uncertain_tabs if key[0] != hwnd}
        self._native_bindings = {key: value for key, value in self._native_bindings.items() if key[0] != hwnd}
        self._web_observations.pop(hwnd, None)

    def _check_focus(self, hwnd: int, *, submitted: bool = False) -> None:
        self._check_owned(hwnd)
        if self.backend.foreground() != hwnd:
            raise NativeTransportError("Browser focus changed; input stopped to protect the other window", submitted=submitted)

    def _input(self, hwnd: int, *keys: str, submitted: bool = False) -> None:
        self._check_focus(hwnd, submitted=submitted)
        self.backend.hotkey(*keys)

    def _focus(self, hwnd: int, tab_index: int | None = None) -> None:
        self._check_owned(hwnd)
        if tab_index is not None and (type(tab_index) is not int or not 1 <= tab_index <= 8):
            raise ValueError("Provider tab_index must be between 1 and 8")
        self.backend.focus(hwnd)
        time.sleep(self.settle_seconds)
        self._check_focus(hwnd)
        if tab_index is not None:
            self._input(hwnd, "ctrl", str(tab_index))
            time.sleep(self.settle_seconds)

    def _restore_clipboard(self, previous: str, owned_values: set[str]) -> None:
        # If the owner copied something else during the operation, retain it.
        try:
            if self.backend.clipboard_read() in owned_values:
                self.backend.clipboard_write(previous)
        except Exception:
            pass

    async def launch(self, argv: list[str], marker: str) -> int:
        if not isinstance(argv, list) or not argv or any(not isinstance(part, str) or not part or "\0" in part for part in argv):
            raise ValueError("Browser launch requires a nonempty argv list")
        if not isinstance(marker, str) or not 12 <= len(marker) <= 160 or any(ord(char) < 32 for char in marker):
            raise ValueError("A unique printable window marker is required")
        return await self._serialized(self._launch, list(argv), marker)

    def _launch(self, argv: list[str], marker: str) -> int:
        if marker in self._pending_launches:
            raise NativeLaunchError('A prior launch with this marker is unresolved; inspect it before launching again')
        try:
            existing = set(self.backend.windows())
        except Exception as error:
            raise NativeLaunchError('Could not inspect browser windows before launch', launched=False) from error
        # Record before spawn because an adapter may raise after creating the
        # process. Only a definite subprocess OSError proves no process started.
        self._pending_launches[marker] = existing
        try:
            self.backend.spawn(argv)
        except OSError as error:
            del self._pending_launches[marker]
            raise NativeLaunchError('Browser process could not be started', launched=False) from error
        except Exception as error:
            raise NativeLaunchError('Browser launch outcome is uncertain; inspect its marker before retrying') from error
        try:
            deadline = time.monotonic() + self.launch_timeout
            while time.monotonic() < deadline:
                hwnd = self._recover_launch(marker, fail_ambiguous=True)
                if hwnd is not None:
                    return hwnd
                time.sleep(self.poll_seconds)
        except NativeLaunchError:
            raise
        except Exception as error:
            raise NativeLaunchError('Could not inspect the new browser window after launch') from error
        raise NativeLaunchError("New browser profile window was not identified; existing personal windows were left alone")

    async def recover_launch(self, marker: str) -> int | None:
        """Adopt a late window using its original launch evidence, without input.

        One fresh window enumeration is made for a pending marker. Missing or
        ambiguous matches retain that evidence for a later attempt.
        """
        return await self._serialized(self._recover_launch, marker)

    def _recover_launch(self, marker: str, *, fail_ambiguous: bool = False) -> int | None:
        existing = self._pending_launches.get(marker)
        if existing is None:
            return None
        matches = [hwnd for hwnd, title in self.backend.windows().items()
                   if hwnd not in existing and _marker_title(title, marker)]
        if len(matches) != 1:
            if len(matches) > 1 and fail_ambiguous:
                raise NativeLaunchError('Multiple windows matched the launch marker; no window was adopted')
            return None
        hwnd = matches[0]
        if type(hwnd) is not int or hwnd <= 0 or hwnd in self._owned:
            return None
        identity = self.backend.identity(hwnd)
        if (not isinstance(identity, tuple) or len(identity) != 2
                or type(identity[0]) is not int or identity[0] <= 0
                or not isinstance(identity[1], str) or not identity[1].strip()):
            return None
        self._owned[hwnd] = identity
        del self._pending_launches[marker]
        return hwnd

    async def window_alive(self, hwnd: int) -> bool:
        """Check recorded ownership without focusing or discarding cleanup state.

        Inspection errors propagate: an inaccessible window is not evidence
        that it closed and must not trigger a replacement launch.
        """
        def inspect():
            return hwnd in self._owned and self.backend.identity(hwnd) == self._owned[hwnd]
        return await self._serialized(inspect)

    async def navigate(self, hwnd: int, url: str, new_tab: bool = False,
                       *, tab_index: int | None = None) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in _PROVIDER_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError("Native navigation is limited to the ChatGPT and Gemini HTTPS sites")
        await self._serialized(self._navigate, hwnd, url, new_tab, tab_index)

    async def navigate_gmail(self, hwnd: int) -> None:
        """Navigate an owned external-profile window to Gmail, not an LLM tab."""
        await self._serialized(
            self._navigate, hwnd, "https://mail.google.com/", False, None)

    async def navigate_web(self, hwnd: int, url: str) -> None:
        """Navigate an explicitly owned user window to its requested HTTP(S) site."""
        normalized = normalize_web_url(url)
        if len(normalized) > 8_192:
            raise ValueError("The requested URL is too long")
        def navigate():
            self._web_observations.pop(hwnd, None)
            self._navigate(hwnd, normalized, False, None)
        await self._serialized(navigate)

    async def focus_window(self, hwnd: int) -> None:
        """Bring an owned user window forward without changing its current tab."""
        await self._serialized(self._focus, hwnd)

    async def observe_web(self, hwnd: int) -> dict[str, Any]:
        """Read an owned window using UIA and masked, local screenshot OCR."""
        return await self._serialized(self._observe_web, hwnd)

    async def observe_web_dom(self, hwnd: int, family: str) -> dict[str, Any]:
        """Read the selected page through the console without depending on its UIA tree."""
        def observe():
            self._web_observations.pop(hwnd, None)
            token = uuid.uuid4().hex
            result = self._evaluate(hwnd, family, OBSERVE_DOM.replace('__TOKEN__', json.dumps(token)), None)
            if result.get('available') is True:
                url = normalize_web_url(result.get('url', ''))
                elements = result.get('elements', [])
                if not isinstance(elements, list) or len(elements) > 100:
                    raise NativeTransportError('DOM observation returned invalid controls')
                targets = {item['runtime_id']: item for item in elements
                           if isinstance(item, dict) and isinstance(item.get('runtime_id'), str)
                           and item['runtime_id'].startswith('dom.' + token + '.')}
                self._web_observations[hwnd] = {'url': url, 'targets': targets, 'source': 'dom',
                                                'token': token, 'family': family}
            return {**redact(result), 'backend': 'native', 'window_id': hwnd, 'tab_id': f'native:{hwnd}'}
        return await self._serialized(observe)

    def _web_snapshot(self, hwnd: int) -> dict[str, Any]:
        self._check_focus(hwnd)
        snapshot = self.backend.accessibility_snapshot(hwnd)
        self._check_focus(hwnd)
        nodes = snapshot.get("nodes", [])
        if (snapshot.get("truncated") or not isinstance(nodes, list) or len(nodes) > 2_500
                or any(not isinstance(node, dict) for node in nodes)):
            raise NativeAccessibilityError("The owned webpage accessibility snapshot is incomplete")
        try:
            url = normalize_web_url(snapshot.get("url", ""))
        except ValueError as error:
            raise NativeTransportError("The owned browser is not displaying an identifiable HTTP(S) page") from error
        return {"url": url, "nodes": nodes}

    def _web_bounds(self, hwnd: int) -> tuple[int, int, int, int]:
        bounds = self.backend.window_rect(hwnd)
        if (not isinstance(bounds, (list, tuple)) or len(bounds) != 4
                or any(type(value) not in (int, float) or not math.isfinite(value) for value in bounds)
                or not 1 <= bounds[2] <= 8_192 or not 1 <= bounds[3] <= 8_192
                or bounds[2] * bounds[3] > 32_000_000):
            raise NativeTransportError("The owned browser window has unsupported screen bounds")
        return tuple(int(value) for value in bounds)

    @staticmethod
    def _web_page_nodes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        """Restrict generic control to document descendants, excluding browser chrome."""
        nodes = snapshot["nodes"]
        by_id = {node.get("id"): node for node in nodes}
        documents = {node.get("id") for node in nodes if node.get("type") == "ControlType.Document"}
        result = []
        for node in nodes:
            parent, seen = node.get("parent"), set()
            for _ in range(40):
                if parent in documents:
                    result.append(node)
                    break
                if parent in seen or parent not in by_id:
                    break
                seen.add(parent)
                parent = by_id[parent].get("parent")
        return result

    @staticmethod
    def _web_rect(control: dict[str, Any]) -> tuple[float, float, float, float] | None:
        rect = control.get("rect")
        if (not isinstance(rect, (list, tuple)) or len(rect) != 4
                or any(type(value) not in (int, float) or not math.isfinite(value) for value in rect)
                or rect[2] <= 0 or rect[3] <= 0):
            return None
        return tuple(rect)

    def _observe_web(self, hwnd: int) -> dict[str, Any]:
        self._focus(hwnd)
        self._web_observations.pop(hwnd, None)
        try:
            snapshot = self._web_snapshot(hwnd)
        except NativeTransportError as error:
            if isinstance(error.__cause__, ValueError) and not isinstance(error, NativeAccessibilityError):
                # The fresh owned launch marker/new tab is not a website yet.
                return {"available": False, "backend": "native", "window_id": hwnd,
                        "tab_id": f"native:{hwnd}", "reason": "No HTTP(S) webpage is open in the selected browser yet",
                        "trust": "untrusted_observation_data"}
            raise
        nodes = self._web_page_nodes(snapshot)
        editable = [node for node in snapshot["nodes"] if node.get("password")
                    or node.get("editable") or node.get("type") == "ControlType.Edit"]
        editable_ids = {node.get("id") for node in editable}
        by_id = {node.get("id"): node for node in snapshot["nodes"]}

        def in_editable(node):
            parent, seen = node.get("parent"), set()
            for _ in range(40):
                if parent in editable_ids:
                    return True
                if parent in seen or parent not in by_id:
                    return False
                seen.add(parent)
                parent = by_id[parent].get("parent")
            return True

        elements, text, observed, focused_target = [], [], {}, None
        for node in nodes:
            if node.get("offscreen") or node.get("password") or in_editable(node):
                continue
            rect = self._web_rect(node)
            if rect is None:
                continue
            label = str(node.get("name", ""))[:300]
            is_focused = bool(node.get("focused"))
            is_editable = bool(node.get("editable") or node.get("type") == "ControlType.Edit")
            if node.get("type") == "ControlType.Text" and not is_editable:
                text.append(label)
            runtime_id = node.get("runtime_id")
            if (len(elements) < 100 and isinstance(runtime_id, str)
                    and re.fullmatch(r"[A-Za-z0-9._-]{1,180}", runtime_id)
                    and node.get("type") in {"ControlType.Button", "ControlType.Hyperlink", "ControlType.Edit",
                        "ControlType.ComboBox", "ControlType.CheckBox", "ControlType.RadioButton", "ControlType.ListItem"}):
                elements.append({"runtime_id": runtime_id, "id": node.get("id"), "parent": node.get("parent"),
                                 "type": node["type"], "label": label,
                                 "rect": list(rect), "enabled": bool(node.get("enabled")), "editable": is_editable,
                                 "focused": is_focused})
                observed[runtime_id] = {"name": node.get("name"), "type": node.get("type")}
                if is_focused and focused_target is None:
                    focused_target = runtime_id

        if focused_target is None:
            for node in snapshot.get("nodes", []):
                if node.get("focused") and not node.get("password") and not node.get("offscreen"):
                    rid = node.get("runtime_id")
                    if isinstance(rid, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,180}", rid):
                        observed[rid] = {"name": str(node.get("name", ""))[:300], "type": str(node.get("type", ""))}
                        focused_target = rid
                        break

        titles = self.backend.windows()
        result = {"available": True, "backend": "native", "window_id": hwnd, "tab_id": f"native:{hwnd}",
                  "url": snapshot["url"], "title": str(titles.get(hwnd, ""))[:300],
                  "captured_at": datetime.now(timezone.utc).isoformat(), "trust": "untrusted_observation_data",
                  "visible_text": "\n".join(text)[:5_000], "elements": elements,
                  "focused_target": focused_target,
                  "ocr_text": "", "ocr_status": "unavailable", "dom_status": "accessibility"}
        try:
            from PIL import ImageDraw
            x, y, width, height = self._web_bounds(hwnd)
            self._check_focus(hwnd)
            image = self.backend.input.screenshot(region=(x, y, width, height))
            self._check_focus(hwnd)
            if image.size != (width, height):
                raise NativeTransportError("Screenshot did not match the owned window bounds")
            draw = ImageDraw.Draw(image)
            for node in editable:
                if node.get("offscreen"):
                    continue
                rect = self._web_rect(node)
                if rect is None:
                    raise NativeTransportError("An editable field could not be masked for OCR")
                left, top = max(0, int(rect[0] - x)), max(0, int(rect[1] - y))
                right, bottom = min(width, int(math.ceil(rect[0] + rect[2] - x))), min(height, int(math.ceil(rect[1] + rect[3] - y)))
                if right > left and bottom > top:
                    draw.rectangle((left, top, right, bottom), fill="black")
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            ocr_reader = OcrReader(timeout_seconds=5)
            result["ocr_text"] = ocr_reader.read_bytes(buffer.getvalue())[:5_000]
            result["ocr_status"] = "captured" if result["ocr_text"] else "empty"
            if len(elements) == 0:
                try:
                    ocr_elements = ocr_reader.read_elements(buffer.getvalue())
                    if not ocr_elements and hasattr(ocr_reader, "read_elements_partitioned"):
                        ocr_elements = ocr_reader.read_elements_partitioned(buffer.getvalue())
                    for item in ocr_elements[:50]:
                        runtime_id = f"ocr.{item['left']}.{item['top']}"
                        ocr_rect = [x + item["left"], y + item["top"], item["width"], item["height"]]
                        elements.append({
                            "runtime_id": runtime_id, "id": runtime_id, "parent": None,
                            "type": "ControlType.Button", "label": item["text"],
                            "rect": ocr_rect, "enabled": True, "editable": False,
                            "source": "ocr",
                        })
                        observed[runtime_id] = {
                            "name": item["text"], "type": "ControlType.Button",
                            "rect": ocr_rect, "source": "ocr",
                        }
                    if ocr_elements:
                        result["dom_status"] = "ocr_fallback"
                        if not result.get("focused_target"):
                            for node in snapshot.get("nodes", []):
                                if node.get("type") == "ControlType.Document" and not node.get("password"):
                                    rid = node.get("runtime_id")
                                    if isinstance(rid, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,180}", rid):
                                        observed[rid] = {"name": str(node.get("name", ""))[:300], "type": str(node.get("type", ""))}
                                        result["focused_target"] = rid
                                        break
                except Exception:
                    pass
        except OcrUnavailable as error:
            result["ocr_error"] = str(error)[:300]
        except Exception as error:
            result["ocr_status"] = "failed"
            result["ocr_error"] = type(error).__name__
        try:
            from app.browser.visual_cache import get_visual_cache
            cached = get_visual_cache().get(snapshot["url"], (x, y, width, height))
            if cached:
                result["cached_elements"] = cached
                for item in cached:
                    rid = item.get("runtime_id")
                    if rid and rid not in observed:
                        observed[rid] = {
                            "name": item.get("label", ""),
                            "type": item.get("type", "ControlType.Button"),
                            "rect": item.get("rect"),
                            "source": "visual_cache",
                        }
        except Exception:
            pass

        self._check_focus(hwnd)
        latest = self._web_snapshot(hwnd)
        if latest["url"] != snapshot["url"]:
            return {"available": False, "reason": "The browser page changed during observation; observe again",
                    "window_id": hwnd, "trust": "untrusted_observation_data"}
        self._web_observations[hwnd] = {"url": snapshot["url"], "targets": observed}
        return redact(result)

    async def register_user_region(self, hwnd: int, bounds, expected_url: str) -> str:
        """Bind an explicit user selection to the observed owned page, without input."""
        return await self._serialized(self._register_user_region, hwnd, bounds, expected_url)

    def _register_user_region(self, hwnd, bounds, expected_url):
        self._focus(hwnd)
        snapshot = self._web_snapshot(hwnd)
        observed = self._web_observations.get(hwnd)
        if not observed or observed["url"] != expected_url or snapshot["url"] != expected_url:
            raise NativeTransportError("The selected webpage changed; observe and select again")
        window_bounds = self._web_bounds(hwnd)
        if (not isinstance(bounds, (list, tuple)) or len(bounds) != 4
                or any(type(value) not in {int, float} or not math.isfinite(value) for value in bounds)
                or bounds[2] <= 1 or bounds[3] <= 1):
            raise NativeTransportError("The selected region has invalid bounds")
        x, y, width, height = window_bounds
        left, top, region_width, region_height = bounds
        if (left < x or top < y or left + region_width > x + width
                or top + region_height > y + height):
            raise NativeTransportError("Select a region entirely inside the owned browser window")
        target = "region." + uuid.uuid4().hex
        observed["targets"][target] = {
            "name": "Selected Region", "type": "ControlType.Button",
            "rect": list(bounds), "source": "user_guidance", "window_bounds": window_bounds,
        }
        return target

    async def web_action(self, hwnd: int, action: str, *, target: str | None = None,
                         text: str | None = None, key: str | None = None,
                         direction: str | None = None, amount: int = 3) -> dict[str, Any]:
        """Apply bounded native input to a freshly revalidated observed control."""
        if action not in {"click", "type", "press", "scroll", "back", "forward", "refresh"}:
            raise ValueError("Unsupported native web action")
        if target is not None and (not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,180}", target)):
            raise ValueError("The target must be an observed accessibility runtime ID")
        if action in {"click", "type"} and target is None:
            raise ValueError("An observed target is required")
        if action == "type" and (not isinstance(text, str) or not text or len(text) > 10_000 or "\0" in text):
            raise ValueError("A nonempty text value of at most 10000 characters is required")
        if action == "press" and key not in {"enter", "space", "tab", "escape", "up", "down", "left", "right",
                                              "home", "end", "pageup", "pagedown", "backspace", "delete", "k", "j", "l"}:
            raise ValueError("The key is not allowed for native web input")
        if action == "scroll" and (direction not in {"up", "down"} or type(amount) is not int or not 1 <= amount <= 10):
            raise ValueError("Scrolling needs up/down and 1-10 wheel ticks")
        if action == "press" and target is None and key not in {"space", "k", "j", "l"}:
            raise ValueError("An observed focused target is required for this key")
        return await self._serialized(self._web_action, hwnd, action, target, text, key, direction, amount)

    def _web_action(self, hwnd, action, target, text, key, direction, amount):
        if self._is_uncertain(hwnd, None):
            raise NativeConsoleIntervention("Resolve the uncertain browser input before continuing", submitted=True)
        self._focus(hwnd)
        observed = self._web_observations.get(hwnd)
        if observed and observed.get('source') == 'dom':
            if target not in observed['targets']:
                raise NativeTransportError('Observe a current DOM control before acting on it')
            arguments = {'token': observed['token'], 'target': target, 'action': action, 'text': text}
            self._web_observations.pop(hwnd, None)
            result = self._evaluate(hwnd, observed['family'], ACT_DOM.replace('__ARGS__', json.dumps(arguments)), None)
            if result.get('performed') is not True:
                raise NativeTransportError(str(result.get('error', 'DOM input was not delivered')))
            return {**result, 'window_id': hwnd}
        snapshot = self._web_snapshot(hwnd)
        observed = self._web_observations.get(hwnd)
        if not observed or observed["url"] != snapshot["url"]:
            raise NativeTransportError("Observe the current webpage before acting on it")
        nodes = self._web_page_nodes(snapshot)
        control = None
        if target is not None:
            previous = observed["targets"].get(target)
            if previous and previous.get("source") in {"ocr", "user_guidance", "visual_cache"}:
                if (previous.get("source") == "user_guidance"
                        and previous.get("window_bounds") != self._web_bounds(hwnd)):
                    raise NativeTransportError("The browser window moved; select the region again")
                rect = previous.get("rect")
                if not rect or len(rect) != 4:
                    raise NativeTransportError("The observed OCR target has invalid coordinates")
                control = {"type": "ControlType.Button", "name": previous.get("name"),
                           "rect": rect, "source": previous.get("source"), "runtime_id": target}
            else:
                matches = [node for node in nodes if node.get("runtime_id") == target]
                if not matches and target in observed["targets"]:
                    matches = [node for node in snapshot.get("nodes", []) if node.get("runtime_id") == target]
                if (previous is None or len(matches) != 1 or matches[0].get("password")
                        or matches[0].get("offscreen")
                        or not (matches[0].get("enabled") if "enabled" in matches[0] else True)
                        or any(matches[0].get(field) != previous[field] for field in ("name", "type"))):
                    raise NativeTransportError("The observed webpage target changed; observe again")
                control = matches[0]
        self._web_observations.pop(hwnd, None)
        if action == "click":
            self._native_click(hwnd, control)
        elif action == "type":
            if control.get("type") != "ControlType.Edit":
                raise NativeTransportError("Typing requires an observed, non-password webpage edit field")
            self._native_click(hwnd, control)
            self._check_focus(hwnd)
            if not self.backend.focused_control(hwnd, target):
                raise NativeTransportError("The requested webpage edit field did not receive focus")
            previous_clipboard = self.backend.clipboard_read()
            try:
                self._input(hwnd, "ctrl", "a")
                if not self.backend.focused_control(hwnd, target):
                    raise NativeTransportError("The webpage edit field lost focus before typing")
                self.backend.clipboard_write(text)
                self._input(hwnd, "ctrl", "v", submitted=True)
                self._check_focus(hwnd, submitted=True)
            finally:
                self._restore_clipboard(previous_clipboard, {text})
        elif action == "press":
            if target is None:
                if key in {"space", "k", "j", "l"}:
                    url = urlsplit(snapshot["url"])
                    if (url.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com"}
                            or not (url.path == "/watch" or url.path.startswith("/live/"))):
                        raise NativeTransportError("Untargeted playback keys require the current YouTube video page")
                    possible = nodes + [node for node in snapshot["nodes"] if node.get("type") == "ControlType.Document"]
                    focused = [node for node in possible if node.get("focused") and not node.get("password")
                               and not node.get("editable") and node.get("type") != "ControlType.Edit"]
                    if len(focused) != 1:
                        raise NativeTransportError("A non-editable YouTube page control must be focused")
                    target = focused[0].get("runtime_id")
                    if not target or not self.backend.focused_control(hwnd, target):
                        raise NativeTransportError("The requested webpage control is not focused")
            else:
                if control and control.get("source") in {"ocr", "user_guidance", "visual_cache"}:
                    self._check_focus(hwnd)
                elif not target or not self.backend.focused_control(hwnd, target):
                    raise NativeTransportError("The requested webpage control is not focused")
            self._input(hwnd, key, submitted=True)
        elif action == "scroll":
            x, y, width, height = self._web_bounds(hwnd)
            center_x, center_y = x + width // 2, y + height // 2
            self._check_focus(hwnd)
            if not self.backend.point_in_window(hwnd, center_x, center_y):
                raise NativeTransportError("The owned browser is covered; scrolling stopped")
            self.backend.input.scroll(amount if direction == "up" else -amount, x=center_x, y=center_y)
        else:
            self._input(hwnd, *{"back": ("alt", "left"), "forward": ("alt", "right"),
                                "refresh": ("ctrl", "r")}[action], submitted=True)
        self._check_focus(hwnd, submitted=True)
        self._web_observations.pop(hwnd, None)
        return {"performed": True, "action": action, "window_id": hwnd,
                "verification": "native_input_delivered; observe the page to verify its effect"}

    async def run_owned_operation(self, hwnd: int, operation: Callable[..., Any],
                                  *arguments: Any) -> Any:
        """Run trusted native automation while retaining ownership and input serialization."""
        if not callable(operation):
            raise TypeError("Owned browser operation must be callable")

        def apply():
            self._focus(hwnd)
            return operation(hwnd, *arguments)
        return await self._serialized(apply)

    def _navigate(self, hwnd: int, url: str, new_tab: bool, tab_index: int | None) -> None:
        if self._is_uncertain(hwnd, tab_index):
            raise NativeConsoleIntervention("Resolve the prior uncertain console operation before navigating this window", submitted=True)
        self._focus(hwnd, tab_index)
        previous = self.backend.clipboard_read()
        try:
            if new_tab:
                self._input(hwnd, "ctrl", "t")
            self._input(hwnd, "ctrl", "l")
            time.sleep(self.settle_seconds)
            address_bar = getattr(self.backend, 'address_bar', None)
            if callable(address_bar):
                address = address_bar(hwnd)
                if address.get('owned') and not address.get('address_focused'):
                    # A newly loaded page can steal focus from the omnibox.
                    # Re-select it once before any clipboard paste or Enter.
                    self._input(hwnd, 'ctrl', 'l')
                    time.sleep(self.settle_seconds)
                    address = address_bar(hwnd)
                if not address.get('owned') or not address.get('address_focused'):
                    raise NativeTransportError('Address bar focus was not verified; navigation stopped before paste')
            self.backend.clipboard_write(url)
            self._input(hwnd, "ctrl", "v")
            time.sleep(self.settle_seconds)
            if callable(address_bar):
                address = address_bar(hwnd)
                if (not address.get('owned') or not address.get('address_focused')
                        or address.get('address_value') != url):
                    raise NativeTransportError('Address bar URL was not verified; navigation stopped before Enter')
            self._input(hwnd, "enter")
            time.sleep(self.settle_seconds)
        finally:
            self._restore_clipboard(previous, {url})


    async def extract_console_dom(self, hwnd: int, family: str = "chromium") -> dict[str, Any] | None:
        """Extract live DOM elements directly from the external browser console."""
        try:
            return await self.evaluate(hwnd, family, EXTRACT_DOM_SCRIPT)
        except Exception:
            return None

    async def evaluate(self, hwnd: int, family: str, script: str,
                       *, tab_index: int | None = None, timeout_seconds: float | None = None) -> dict:
        if family not in {"chromium", "firefox"}:
            raise ValueError("Native console family must be chromium or firefox")
        if not isinstance(script, str) or not script.strip() or len(script) > 500_000:
            raise ValueError("A bounded runtime-owned JavaScript expression is required")
        if timeout_seconds is not None and (type(timeout_seconds) not in {int, float}
                                           or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60):
            raise ValueError("Console timeout must be between zero and 60 seconds")
        return await self._serialized(self._evaluate, hwnd, family, script, tab_index, timeout_seconds)

    def _evaluate(self, hwnd: int, family: str, script: str, tab_index: int | None,
                  timeout_seconds: float | None = None) -> dict:
        if self._is_uncertain(hwnd, tab_index):
            raise NativeConsoleIntervention("The previous console operation has an unknown outcome; inspect it before retrying", submitted=True)
        self._focus(hwnd, tab_index)
        shortcut = ("ctrl", "shift", "k" if family == "firefox" else "j")
        nonce = uuid.uuid4().hex
        wrapped = wrap_console_expression(script, nonce)
        self.console_diagnostics[hwnd] = {"status": "preparing", "steps": []}
        previous = self.backend.clipboard_read()
        owned_values = {wrapped}
        submitted = False
        console_confirmed = False
        opened_console = False
        try:
            already_focused = getattr(self.backend, 'console_focused', None)
            if not callable(already_focused) or not already_focused(hwnd, family):
                self._input(hwnd, *shortcut)
                opened_console = True
                time.sleep(self.settle_seconds)
            if not self.backend.console_ready(hwnd, family):
                raise NativeConsoleIntervention(
                    "Could not verify the focused browser console. Use a docked, English-language developer console and complete any manual setup; no script was pasted."
                )
            console_confirmed = True
            self._check_focus(hwnd)
            self.backend.clipboard_write(wrapped)
            self._input(hwnd, "ctrl", "v")
            time.sleep(self.settle_seconds)
            # No 'allow pasting', typed-script fallback, or other bypass of the
            # browser's self-XSS protection. A missing nonce pauses the session.
            self._check_focus(hwnd)
            submitted = True
            self.console_diagnostics[hwnd] = {"status": "submitted", "steps": ["console.submitted"]}
            self._input(hwnd, "enter", submitted=True)
            deadline = time.monotonic() + (timeout_seconds or self.result_timeout)
            next_console_read = time.monotonic()
            while time.monotonic() < deadline:
                self._check_focus(hwnd, submitted=True)
                raw = self.backend.clipboard_read()
                result = parse_console_receipt(raw, nonce)
                channel = "clipboard"
                if result is None and time.monotonic() >= next_console_read:
                    read_receipt = getattr(self.backend, "console_receipt", None)
                    if callable(read_receipt):
                        result = parse_console_receipt(read_receipt(hwnd, nonce), nonce)
                        channel = "console"
                    next_console_read = time.monotonic() + .5
                self._check_focus(hwnd, submitted=True)
                if result is not None:
                    if channel == "clipboard":
                        owned_values.add(raw)
                    steps = result.get("steps", [])
                    self.console_diagnostics[hwnd] = {
                        "status": "completed" if result.get("ok") is True else "failed",
                        "receipt_channel": channel,
                        "steps": [str(step)[:120] for step in steps[:80]] if isinstance(steps, list) else [],
                    }
                    if result.get("ok") is not True:
                        raise NativeTransportError("Browser console expression failed: " + str(result.get("error", "unknown error"))[:500], submitted=True)
                    value = result.get("value")
                    if not isinstance(value, dict):
                        raise NativeTransportError("Browser console returned an invalid result object", submitted=True)
                    return value
                time.sleep(self.poll_seconds)
            self._mark_uncertain(hwnd, tab_index)
            self.console_diagnostics[hwnd]["status"] = "receipt_missing"
            raise NativeConsoleIntervention(
                "No confirmed console result. Console paste protection, developer-tools setup, or a slow expression needs manual inspection. The command will not be replayed; browser protections were not bypassed.",
                submitted=True,
            )
        except (NativeTransportError, NativeConsoleIntervention) as error:
            if submitted:
                error.submitted = True
                self._mark_uncertain(hwnd, tab_index)
            raise
        except Exception as error:
            if submitted:
                self._mark_uncertain(hwnd, tab_index)
            raise NativeTransportError("Native console operation failed: " + type(error).__name__, submitted=submitted) from error
        finally:
            self._restore_clipboard(previous, owned_values)
            if opened_console and console_confirmed and not self._is_uncertain(hwnd, tab_index):
                # Never steal focus back from the owner just to tidy the UI.
                try:
                    self._input(hwnd, *shortcut, submitted=submitted)
                except NativeTransportError:
                    self._mark_uncertain(hwnd, tab_index)

    async def native_action(self, hwnd: int, provider: str, action: str, *, owner: str,
                            tab_index: int | None = None, prompt: str | None = None,
                            request: str | None = None, prompt_hash: str | None = None) -> dict:
        """Console-independent chat controls using observed Windows UIA elements.

        Every operation uses the same desktop lane as console operations. The
        caller must durably record intent before ``submit``. No general model
        authored clicks, hotkeys, scripts, or accessibility selectors are accepted.
        """
        if provider not in _COMPOSER_NAMES or action not in {'bind', 'observe', 'prepare', 'submit', 'read_response'}:
            raise ValueError('Unsupported native chat operation')
        if not isinstance(owner, str) or not owner or len(owner) > 256:
            raise ValueError('A bounded native tab owner is required')
        if action in {'prepare', 'submit'} and (not isinstance(request, str) or not request or len(request) > 128):
            raise ValueError('A bounded request receipt is required')
        if action == 'prepare' and (not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 128_000):
            raise ValueError('A bounded chat prompt is required')
        if prompt_hash is not None and (not isinstance(prompt_hash, str) or not re.fullmatch('[a-f0-9]{64}', prompt_hash)):
            raise ValueError('Expected a SHA-256 prompt fingerprint')
        return await self._serialized(self._native_action, hwnd, provider, action, owner, tab_index, prompt, request, prompt_hash)

    def _native_snapshot(self, hwnd: int, provider: str) -> dict:
        self._check_focus(hwnd)
        snapshot = self.backend.accessibility_snapshot(hwnd)
        self._check_focus(hwnd)
        try:
            url = snapshot.get('url', '')
            # Chromium accessibility commonly omits the scheme in the omnibox.
            if isinstance(url, str) and not url.startswith('https://'):
                url = 'https://' + url
            parsed = urlsplit(url)
            host = 'chatgpt.com' if provider == 'chatgpt' else 'gemini.google.com'
            if (parsed.scheme != 'https' or parsed.hostname != host or parsed.username or parsed.password
                    or parsed.port not in (None, 443) or any(ord(char) < 32 for char in url)):
                return {'error': 'wrong_origin'}
        except (ValueError, TypeError):
            return {'error': 'wrong_origin'}
        return _accessible_page({**snapshot, 'url': url}, provider)

    def _native_click(self, hwnd: int, control: dict, *, submitted: bool = False) -> None:
        if control.get("source") in {"ocr", "user_guidance"}:
            rect = control.get("rect")
            if (not isinstance(rect, (list, tuple)) or len(rect) != 4
                    or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in rect)
                    or rect[2] <= 1 or rect[3] <= 1):
                raise NativeTransportError("OCR control has no usable observed bounds", submitted=submitted)
            x, y = int(rect[0] + rect[2] / 2), int(rect[1] + rect[3] / 2)
            self._check_focus(hwnd, submitted=submitted)
            if not self.backend.point_in_window(hwnd, x, y):
                raise NativeTransportError("Observed OCR control is outside the window bounds", submitted=submitted)
            self._check_focus(hwnd, submitted=submitted)
            self.backend.click(x, y)
            return
        rect, runtime_id = control.get('rect'), control.get('runtime_id')
        if (not isinstance(rect, (list, tuple)) or len(rect) != 4
                or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in rect)
                or rect[2] <= 1 or rect[3] <= 1 or not isinstance(runtime_id, str) or not runtime_id):
            raise NativeTransportError('Native control has no usable observed bounds', submitted=submitted)
        x, y = int(rect[0] + rect[2] / 2), int(rect[1] + rect[3] / 2)
        self._check_focus(hwnd, submitted=submitted)
        if not self.backend.point_in_window(hwnd, x, y) or not self.backend.control_at(hwnd, x, y, runtime_id):
            raise NativeTransportError('Observed chat control moved or is covered; input stopped', submitted=submitted)
        self._check_focus(hwnd, submitted=submitted)
        self.backend.click(x, y)

    def _copy_observed_text(self, hwnd, control, method):
        copy = getattr(self.backend, method, None)
        if not control or not callable(copy):
            return None
        previous = self.backend.clipboard_read()
        marker = 'brainless-copy-' + uuid.uuid4().hex
        owned = {marker}
        try:
            self.backend.clipboard_write(marker)
            self._check_focus(hwnd)
            if not copy(hwnd, control['runtime_id']):
                return None
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                self._check_focus(hwnd)
                value = self.backend.clipboard_read()
                if isinstance(value, str) and value != marker and value.strip():
                    owned.add(value)
                    return value if len(value) <= 128_000 else None
                time.sleep(self.poll_seconds)
            return None
        finally:
            self._restore_clipboard(previous, owned)

    def _native_action(self, hwnd: int, provider: str, action: str, owner: str,
                       tab_index: int | None, prompt: str | None, request: str | None, prompt_hash: str | None = None) -> dict:
        if self._is_uncertain(hwnd, tab_index):
            raise NativeConsoleIntervention('Resolve the uncertain console operation before using native input', submitted=True)
        self._focus(hwnd, tab_index)
        state = self._native_snapshot(hwnd, provider)
        if state.get('error'):
            return state
        key = (hwnd, tab_index)
        if action == 'bind':
            if not state.get('ready'):
                return {'error': 'composer_unavailable'}
            self._native_bindings[key] = dict(owner=owner, provider=provider, url=state['url'])
            return dict(bound=True, **state)
        binding = self._native_bindings.get(key)
        if not binding or binding['owner'] != owner or binding['provider'] != provider:
            return {'error': 'wrong_tab'}
        if state['url'] != binding['url']:
            old_path, new_path = urlsplit(binding['url']).path.rstrip('/'), urlsplit(state['url']).path
            base_path, conversation = ('', '/c/') if provider == 'chatgpt' else ('/app', '/app/')
            # A first send can create a canonical URL. Any other tab/address
            # change needs an explicit bind before it receives input.
            same_path = old_path == new_path.rstrip('/')
            # ChatGPT briefly assigns /c/WEB:<uuid> before its server-side UUID.
            # Permit that one observed transition only during this submitted
            # turn, then pin the canonical conversation normally.
            temporary_chat = (provider == 'chatgpt' and not binding.get('canonicalized')
                              and re.fullmatch(r'/c/WEB:[0-9a-fA-F-]{36}', old_path)
                              and re.fullmatch(r'/c/[0-9a-fA-F-]{36}', new_path))
            if action in {'observe', 'read_response'} and (same_path or (binding.get('submitted') and
                    ((old_path == base_path and new_path.startswith(conversation)) or temporary_chat))):
                binding['url'] = state['url']
                if temporary_chat:
                    binding['canonicalized'] = True
            else:
                return {'error': 'wrong_tab'}
        if action == 'observe':
            return state
        if action == 'read_response':
            if prompt_hash is not None:
                copied_prompt = self._copy_observed_text(hwnd, state.get('user_copy'), 'copy_message')
                if copied_prompt is None or hashlib.sha256(copied_prompt.encode()).hexdigest() != prompt_hash:
                    return {**state, 'request_verified': False}
                after = self._native_snapshot(hwnd, provider)
                if any(after.get(key) != state.get(key) for key in ('url', 'count', 'text')) or after.get('busy'):
                    return {'error': 'response_changed'}
                state = {**after, 'request_verified': True}
            control = state.get('copy_response')
            copy_response = getattr(self.backend, 'copy_response', None)
            if state.get('busy'):
                return {'error': 'response_pending'}
            if not control or not callable(copy_response):
                return state
            previous = self.backend.clipboard_read()
            marker = 'brainless-response-' + uuid.uuid4().hex
            owned_values = {marker}
            try:
                self.backend.clipboard_write(marker)
                self._check_focus(hwnd)
                if not copy_response(hwnd, control['runtime_id']):
                    return state
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    self._check_focus(hwnd)
                    copied = self.backend.clipboard_read()
                    if isinstance(copied, str) and copied != marker and copied.strip():
                        owned_values.add(copied)
                        if len(copied) > 128_000:
                            return {'error': 'response_too_large'}
                        return {**state, 'text': copied, 'copied_response': True}
                    time.sleep(self.poll_seconds)
                return state
            finally:
                self._restore_clipboard(previous, owned_values)
        if state.get('busy'):
            return {'error': 'response_pending'}
        composer = state.get('composer')
        if not composer:
            return {'error': 'composer_unavailable'}
        if action == 'prepare':
            if binding.get('request') == request and binding.get('submitted'):
                return {'error': 'already_submitted'}
            previous = self.backend.clipboard_read()
            try:
                focus_composer = getattr(self.backend, 'focus_composer', None)
                if callable(focus_composer):
                    # Chromium may hit-test an ancestor Group rather than its
                    # editable descendant. Focus the exact observed UIA element,
                    # then independently verify focus before touching clipboard.
                    if not focus_composer(hwnd, composer['runtime_id']):
                        raise NativeTransportError('Observed composer changed before focus; retry readiness')
                else:
                    self._native_click(hwnd, composer)
                if not self.backend.focused_control(hwnd, composer['runtime_id']):
                    raise NativeTransportError('Composer focus was not confirmed; nothing was pasted')
                self._input(hwnd, 'ctrl', 'a')
                if not self.backend.focused_control(hwnd, composer['runtime_id']):
                    raise NativeTransportError('Composer focus changed; paste stopped')
                self.backend.clipboard_write(prompt)
                self._input(hwnd, 'ctrl', 'v')
                time.sleep(self.settle_seconds)
                verified = self._native_snapshot(hwnd, provider)
                actual = (verified.get('composer') or {}).get('value')
                if (verified.get('url') != state['url'] or not isinstance(actual, str)
                        or actual.replace('\r\n', '\n').strip() != prompt.replace('\r\n', '\n').strip()):
                    return {'error': 'input_mismatch'}
                binding.update(request=request, submitted=False, prompt=prompt)
                return dict(prepared=True, **state)
            finally:
                self._restore_clipboard(previous, {prompt})
        if binding.get('request') != request:
            return {'error': 'missing_receipt'}
        if binding.get('submitted'):
            return {'submitted': True, 'duplicate': True, 'url': state['url'], 'channel': 'accessibility'}
        actual = composer.get('value')
        if not isinstance(actual, str) or actual.replace('\r\n', '\n').strip() != binding['prompt'].replace('\r\n', '\n').strip():
            return {'error': 'input_mismatch'}
        button = state.get('send')
        if not button:
            return {'error': 'send_unavailable'}
        # Validate the target before committing the in-memory no-replay receipt.
        # The durable receipt already exists at this point in the caller.
        sent = False
        try:
            self._check_focus(hwnd)
            invoke_send = getattr(self.backend, 'invoke_send', None)
            if callable(invoke_send):
                binding['submitted'] = sent = True
                if invoke_send(hwnd, button.get('runtime_id', '')):
                    self._check_focus(hwnd, submitted=True)
                    return {'submitted': True, 'url': state['url'], 'channel': 'accessibility'}
                # Explicit false certifies that InvokePattern wasn't invoked.
                binding['submitted'] = sent = False
            rect = button.get('rect', [])
            if len(rect) != 4 or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in rect):
                raise NativeTransportError('Native send control has no usable observed bounds')
            x, y = int(rect[0] + rect[2] / 2), int(rect[1] + rect[3] / 2)
            if rect[2] <= 1 or rect[3] <= 1 or not self.backend.point_in_window(hwnd, x, y) or not self.backend.control_at(hwnd, x, y, button.get('runtime_id', '')):
                raise NativeTransportError('Observed send control moved or is covered; input stopped')
            self._check_focus(hwnd)
            binding['submitted'] = sent = True
            self.backend.click(x, y)
            self._check_focus(hwnd, submitted=True)
            return {'submitted': True, 'url': state['url'], 'channel': 'accessibility'}
        except Exception as error:
            if isinstance(error, NativeTransportError):
                error.submitted = sent
                raise
            raise NativeTransportError('Native send outcome is uncertain' if sent else 'Native send failed before input', submitted=sent) from error

    async def hotkey(self, hwnd: int, *keys: str) -> None:
        # Runtime control only; keep the public helper deliberately small.
        allowed = {("ctrl", str(index)) for index in range(1, 9)} | {("esc",)}
        if keys not in allowed:
            raise ValueError("Unsupported native browser hotkey")
        def apply():
            self._focus(hwnd)
            self._input(hwnd, *keys)
        await self._serialized(apply)

    async def click(self, hwnd: int, x: int, y: int) -> None:
        if type(x) is not int or type(y) is not int:
            raise ValueError("Mouse coordinates must be integers")
        def apply():
            self._focus(hwnd)
            if not self.backend.point_in_window(hwnd, x, y):
                raise NativeTransportError("Mouse target is outside the owned browser window")
            self._check_focus(hwnd)
            self.backend.click(x, y)
        await self._serialized(apply)

    async def close(self, hwnd: int) -> None:
        def apply():
            if hwnd not in self._owned:
                raise NativeTransportError('Browser window is no longer an owned fleet window')
            identity = self._owned[hwnd]
            # It may already have been closed manually. Never send WM_CLOSE to
            # a different process that subsequently received the same handle.
            if self.backend.identity(hwnd) != identity:
                self._forget_window(hwnd)
                return
            self.backend.close(hwnd)
            deadline = time.monotonic() + self.launch_timeout
            while self.backend.identity(hwnd) == identity:
                if time.monotonic() >= deadline:
                    raise NativeTransportError(
                        'Owned browser window did not close; resolve its close dialog before retrying')
                time.sleep(self.poll_seconds)
            self._forget_window(hwnd)
        await self._serialized(apply)
