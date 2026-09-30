"""Parse runtime-owned PowerShell programs without inspecting the desktop."""
import os
import subprocess

import pytest

from app.autonomy.desktop_team_controller import _SNAPSHOT_SCRIPT
from app.browser.native_console import _CONSOLE_ACCESSIBILITY_SCRIPT, _PAGE_ACCESSIBILITY_SCRIPT, _WINDOW_FOCUS_SCRIPT, _CONSOLE_RECEIPT_SCRIPT


@pytest.mark.skipif(os.name != 'nt', reason='Windows PowerShell parser')
@pytest.mark.parametrize('script', [_SNAPSHOT_SCRIPT.replace('__HWND__', '100'),
                                  _CONSOLE_ACCESSIBILITY_SCRIPT, _PAGE_ACCESSIBILITY_SCRIPT, _WINDOW_FOCUS_SCRIPT,
                                  _CONSOLE_RECEIPT_SCRIPT],
                         ids=['desktop', 'console', 'provider', 'window-focus', 'console-receipt'])
def test_accessibility_scripts_have_valid_powershell_syntax(script):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
        "$source=[Console]::In.ReadToEnd(); $tokens=$null; $errors=$null; "
        "[void][System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors); "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { $_.Message }; exit 1 }"],
        input=script, text=True, capture_output=True, timeout=10,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert result.returncode == 0, result.stdout + result.stderr
