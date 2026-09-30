"""Allow-listed visible desktop application automation adapters."""
from __future__ import annotations

import platform
import subprocess
import time
from typing import Any, Protocol

from app.computer.keyboard import Keyboard


class ApplicationLauncher(Protocol):
    def launch(self, application: str) -> None: ...


class WindowsApplicationLauncher:
    """Launch only named, harmless desktop applications."""

    COMMANDS = {
        "calculator": ["calc.exe"],
        "notepad": ["notepad.exe"],
        "paint": ["mspaint.exe"],
        "explorer": ["explorer.exe"],
        "settings": ["cmd.exe", "/c", "start", "", "ms-settings:"],
    }

    def launch(self, application: str) -> None:
        if platform.system().lower() != "windows":
            raise RuntimeError("Visible application launcher currently supports Windows only")
        try:
            command = self.COMMANDS[application.casefold()]
        except KeyError as error:
            raise ValueError(f"Application is not allow-listed: {application}") from error
        subprocess.Popen(command, shell=False)


def register_desktop_tools(registry, keyboard: Keyboard | None = None,
                           launcher: ApplicationLauncher | None = None) -> None:
    """Register visible actions through the normal ToolRegistry permission path."""
    keys = keyboard or Keyboard()
    apps = launcher or WindowsApplicationLauncher()

    def launch(arguments: dict[str, Any]) -> str:
        application = str(arguments["application"]).casefold()
        apps.launch(application)
        return application

    def type_visible(arguments: dict[str, Any]) -> str:
        text = str(arguments["text"])
        keys.type_text(text)
        return "typed"

    def calculator(arguments: dict[str, Any]) -> str:
        expression = str(arguments["expression"]).strip()
        if not expression or len(expression) > 100:
            raise ValueError("Calculator expression must contain 1-100 characters")
        apps.launch("calculator")
        time.sleep(1)
        keys.type_text(expression)
        keys.press_hotkey("enter")
        return expression

    return launch, type_visible, calculator
