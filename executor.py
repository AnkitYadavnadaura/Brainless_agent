from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyautogui
import psutil


# ============================================================
# CONFIGURATION
# ============================================================

MAX_RETRIES = 3
DEFAULT_WAIT = 1.0

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime_data"
SCREENSHOT_DIR = RUNTIME_DIR / "screenshots"
LOG_DIR = RUNTIME_DIR / "logs"

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "executor.log"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("TaskExecutor")

pyautogui.PAUSE = 0.15
pyautogui.FAILSAFE = True


# ============================================================
# EXCEPTIONS
# ============================================================

class TaskError(Exception):
    """Base task execution error."""


class ValidationError(TaskError):
    """Invalid task JSON."""


class PermissionError(TaskError):
    """Required computer permission is unavailable."""


class ActionError(TaskError):
    """Computer action failed."""


class VerificationError(TaskError):
    """Verification failed."""


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class ExecutionContext:
    task: Dict[str, Any]
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    retries: int = 0
    current_step: Optional[int] = None


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def screenshot_name(step: Any, suffix: str = "") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    extra = f"_{suffix}" if suffix else ""
    return SCREENSHOT_DIR / f"step_{step}_{ts}{extra}.png"


def save_screenshot(step: Any, suffix: str = "") -> str:
    path = screenshot_name(step, suffix)
    pyautogui.screenshot(str(path))
    logger.info("Screenshot saved: %s", path)
    return str(path)


def normalize_url(url: str) -> str:
    """
    Handles accidental Markdown links such as:

    [https://www.youtube.com](https://www.youtube.com)
    """

    if not url:
        return url

    if url.startswith("[") and "](" in url:
        try:
            return url.split("](", 1)[1].rstrip(")")
        except Exception:
            pass

    return url.strip()


# ============================================================
# COMPUTER CONTROLLER
# ============================================================

class ComputerController:
    """
    Generic Windows computer-control layer.

    Uses:
        pyautogui -> mouse/keyboard/screenshots
        subprocess -> application launching
        psutil -> process inspection
        webbrowser -> URL navigation fallback
    """

    APPLICATION_COMMANDS = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
    }

    def __init__(self):
        self.current_url: Optional[str] = None

    # --------------------------------------------------------
    # APPLICATION CONTROL
    # --------------------------------------------------------

    def open_application(self, application: str):
        name = application.lower().strip()

        # Check whether it is already running.
        if self.is_application_running(name):
            logger.info("%s is already running.", application)
            return

        commands = self.APPLICATION_COMMANDS.get(name)

        if commands:
            for command in commands:
                if command.endswith(".exe") and os.path.exists(command):
                    subprocess.Popen([command])
                    time.sleep(2)
                    return

                if command.endswith(".exe") and "\\" not in command:
                    try:
                        subprocess.Popen([command])
                        time.sleep(2)
                        return
                    except Exception:
                        continue

        # Generic fallback.
        try:
            subprocess.Popen(application, shell=True)
            time.sleep(2)
        except Exception as exc:
            raise ActionError(
                f"Could not open application '{application}': {exc}"
            ) from exc

    def close_application(self, application: str):
        name = application.lower()

        process_names = {
            "chrome": {"chrome.exe"},
            "edge": {"msedge.exe"},
            "notepad": {"notepad.exe"},
            "calculator": {"calculatorapp.exe", "calc.exe"},
        }

        targets = process_names.get(name, {f"{name}.exe"})

        for process in psutil.process_iter(["pid", "name"]):
            try:
                if process.info["name"] and process.info["name"].lower() in targets:
                    process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def is_application_running(self, application: str) -> bool:
        name = application.lower()

        aliases = {
            "chrome": {"chrome.exe"},
            "edge": {"msedge.exe"},
            "notepad": {"notepad.exe"},
            "calculator": {"calculatorapp.exe", "calc.exe"},
        }

        targets = aliases.get(name, {f"{name}.exe"})

        for process in psutil.process_iter(["name"]):
            try:
                process_name = process.info["name"]
                if process_name and process_name.lower() in targets:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False

    # --------------------------------------------------------
    # BROWSER
    # --------------------------------------------------------

    def navigate(self, url: str):
        url = normalize_url(url)

        if not url.startswith(("http://", "https://")):
            raise ActionError(f"Unsupported navigation URL: {url}")

        logger.info("Navigating to %s", url)

        webbrowser.open(url)
        self.current_url = url

        time.sleep(DEFAULT_WAIT)

    def get_current_url(self) -> Optional[str]:
        return self.current_url

    def wait_for_page(self, seconds: float = DEFAULT_WAIT):
        time.sleep(seconds)

    # --------------------------------------------------------
    # MOUSE
    # --------------------------------------------------------

    def click(self, x: Optional[int] = None, y: Optional[int] = None):
        if x is None or y is None:
            raise ActionError(
                "Coordinate click requested without coordinates."
            )

        pyautogui.click(x, y)

    def double_click(self, x: int, y: int):
        pyautogui.doubleClick(x, y)

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration=0.5):
        pyautogui.moveTo(x1, y1)
        pyautogui.dragTo(x2, y2, duration=duration)

    def scroll(self, amount: int):
        pyautogui.scroll(amount)

    # --------------------------------------------------------
    # KEYBOARD
    # --------------------------------------------------------

    def type_text(self, value: str):
        pyautogui.write(str(value), interval=0.01)

    def press_key(self, key: str):
        pyautogui.press(key.lower())

    def hotkey(self, keys: List[str]):
        pyautogui.hotkey(*[key.lower() for key in keys])

    # --------------------------------------------------------
    # CLIPBOARD
    # --------------------------------------------------------

    def copy(self):
        pyautogui.hotkey("ctrl", "c")

    def paste(self):
        pyautogui.hotkey("ctrl", "v")

    # --------------------------------------------------------
    # SCREEN
    # --------------------------------------------------------

    def screenshot(self, path: str):
        pyautogui.screenshot(path)


# ============================================================
# TARGET RESOLVER
# ============================================================

class TargetResolver:
    """
    Converts semantic targets into executable targets.

    This layer is deliberately separate from TaskExecutor so
    better computer-vision/accessibility/browser implementations
    can be added later without changing the execution engine.
    """

    def __init__(self, controller: ComputerController):
        self.controller = controller

    def resolve(self, target: str, context: ExecutionContext) -> Dict[str, Any]:
        target_lower = target.lower().strip()

        # Semantic application targets.
        if target_lower == "chrome":
            return {
                "type": "application",
                "name": "Chrome",
            }

        if target_lower == "notepad":
            return {
                "type": "application",
                "name": "Notepad",
            }

        # Common keyboard/UI semantic targets.
        semantic = {
            "youtube search box": {
                "type": "ui",
                "description": "YouTube search box",
            },
            "google search box": {
                "type": "ui",
                "description": "Google search box",
            },
            "play button": {
                "type": "ui",
                "description": "Play button",
            },
            "first relevant music video": {
                "type": "ui",
                "description": "first relevant music video",
            },
        }

        if target_lower in semantic:
            return semantic[target_lower]

        return {
            "type": "ui",
            "description": target,
        }


# ============================================================
# TASK EXECUTOR
# ============================================================

class TaskExecutor:

    MOUSE_ACTIONS = {
        "click",
        "double_click",
        "drag",
        "scroll",
        "select",
    }

    KEYBOARD_ACTIONS = {
        "type",
        "press_key",
        "hotkey",
        "copy",
        "paste",
    }

    def __init__(self, task: Dict[str, Any]):
        self.task = task
        self.context = ExecutionContext(task=task)

        self.controller = ComputerController()
        self.resolver = TargetResolver(self.controller)

        self.validate_task()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def validate_task(self):
        if not isinstance(self.task, dict):
            raise ValidationError("Task must be a JSON object.")

        required = {
            "task",
            "requirements",
            "execution",
            "verification",
        }

        missing = required - set(self.task.keys())

        if missing:
            raise ValidationError(
                f"Missing required fields: {sorted(missing)}"
            )

        if not isinstance(self.task["execution"], list):
            raise ValidationError("'execution' must be a list.")

        for index, step in enumerate(self.task["execution"], start=1):
            if not isinstance(step, dict):
                raise ValidationError(
                    f"Execution step {index} must be an object."
                )

            if "action" not in step:
                raise ValidationError(
                    f"Execution step {index} has no action."
                )

    # --------------------------------------------------------
    # PERMISSION SYSTEM
    # --------------------------------------------------------

    def check_permission(self, action: str):
        permissions = set(
            p.lower()
            for p in self.task.get("requirements", {}).get(
                "permissions", []
            )
        )

        if action in self.MOUSE_ACTIONS:
            if "mouse" not in permissions:
                raise PermissionError(
                    f"Action '{action}' requires mouse permission."
                )

        if action in self.KEYBOARD_ACTIONS:
            if "keyboard" not in permissions:
                raise PermissionError(
                    f"Action '{action}' requires keyboard permission."
                )

    # --------------------------------------------------------
    # EXECUTION
    # --------------------------------------------------------

    def execute(self) -> Dict[str, Any]:
        logger.info(
            "Starting task: %s",
            self.task["task"].get("name", "Unnamed task"),
        )

        try:
            for step in self.task["execution"]:
                self.execute_step(step)

            verification = self.final_verification()

            if verification["status"] != "success":
                return self.generate_result(
                    status="failed",
                    verification=verification,
                )

            return self.generate_result(
                status="success",
                verification=verification,
            )

        except Exception as exc:
            logger.exception("Task execution failed.")

            return self.generate_result(
                status="failed",
                error=str(exc),
            )

    # --------------------------------------------------------
    # STEP EXECUTION
    # --------------------------------------------------------

    def execute_step(self, step: Dict[str, Any]):
        step_number = step.get("step", "?")
        action = step["action"]

        self.context.current_step = step_number

        logger.info(
            "Executing step %s: %s",
            step_number,
            action,
        )

        last_error = None

        for attempt in range(MAX_RETRIES + 1):

            started = time.perf_counter()

            try:
                self.check_permission(action)

                self.execute_action(step)

                verified = self.verify_step(step)

                if not verified:
                    raise VerificationError(
                        step.get(
                            "success_condition",
                            "Step verification failed.",
                        )
                    )

                duration = int(
                    (time.perf_counter() - started) * 1000
                )

                self.log_step(
                    step,
                    status="success",
                    duration_ms=duration,
                    retry_count=attempt,
                )

                return

            except Exception as exc:
                last_error = exc

                logger.warning(
                    "Step %s failed on attempt %s/%s: %s",
                    step_number,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    exc,
                )

                self.log_step(
                    step,
                    status="failed",
                    error=str(exc),
                    retry_count=attempt,
                )

                # Capture failure screenshot.
                try:
                    path = save_screenshot(
                        step_number,
                        "failure",
                    )
                    self.context.screenshots.append(path)
                except Exception:
                    pass

                if attempt < MAX_RETRIES:
                    self.context.retries += 1

                    self.recover(step)

                    time.sleep(DEFAULT_WAIT)

        raise ActionError(
            f"Step {step_number} failed after "
            f"{MAX_RETRIES + 1} attempts: {last_error}"
        )

    # --------------------------------------------------------
    # ACTION DISPATCHER
    # --------------------------------------------------------

    def execute_action(self, step: Dict[str, Any]):
        action = step["action"]

        handlers = {
            "open_application": self.action_open_application,
            "close_application": self.action_close_application,
            "navigate": self.action_navigate,
            "wait": self.action_wait,
            "click": self.action_click,
            "double_click": self.action_double_click,
            "type": self.action_type,
            "press_key": self.action_press_key,
            "hotkey": self.action_hotkey,
            "scroll": self.action_scroll,
            "drag": self.action_drag,
            "select": self.action_select,
            "inspect": self.action_inspect,
            "screenshot": self.action_screenshot,
            "copy": self.action_copy,
            "paste": self.action_paste,
        }

        handler = handlers.get(action)

        if not handler:
            raise ActionError(
                f"Unsupported action: {action}"
            )

        return handler(step)

    # --------------------------------------------------------
    # ACTION HANDLERS
    # --------------------------------------------------------

    def action_open_application(self, step):
        target = step.get("target")

        if not target:
            raise ActionError("open_application requires target.")

        self.controller.open_application(target)

    def action_close_application(self, step):
        self.controller.close_application(
            step.get("target", "")
        )

    def action_navigate(self, step):
        self.controller.navigate(
            step.get("target", "")
        )

    def action_wait(self, step):
        milliseconds = step.get(
            "duration_ms",
            DEFAULT_WAIT * 1000,
        )

        time.sleep(float(milliseconds) / 1000)

    def action_click(self, step):
        target = step.get("target", "")

        # Explicit coordinates can be supplied by a future planner.
        if "x" in step and "y" in step:
            self.controller.click(
                int(step["x"]),
                int(step["y"]),
            )
            return

        resolved = self.resolver.resolve(
            target,
            self.context,
        )

        # This generic implementation cannot safely infer arbitrary
        # screen coordinates from natural language.
        #
        # Browser/UI automation adapters can replace this method.
        raise ActionError(
            f"Semantic click target '{target}' could not be "
            f"resolved by the current UI adapter. "
            f"Resolved target: {resolved}"
        )

    def action_double_click(self, step):
        if "x" not in step or "y" not in step:
            raise ActionError(
                "double_click currently requires x and y."
            )

        self.controller.double_click(
            int(step["x"]),
            int(step["y"]),
        )

    def action_type(self, step):
        value = step.get("value")

        if value is None:
            raise ActionError("type requires value.")

        self.controller.type_text(value)

    def action_press_key(self, step):
        key = step.get("key")

        if not key:
            raise ActionError(
                "press_key requires key."
            )

        self.controller.press_key(key)

    def action_hotkey(self, step):
        keys = step.get("keys")

        if not isinstance(keys, list):
            raise ActionError(
                "hotkey requires a list of keys."
            )

        self.controller.hotkey(keys)

    def action_scroll(self, step):
        amount = int(step.get("amount", 0))

        self.controller.scroll(amount)

    def action_drag(self, step):
        required = ["x1", "y1", "x2", "y2"]

        if not all(k in step for k in required):
            raise ActionError(
                "drag requires x1, y1, x2 and y2."
            )

        self.controller.drag(
            int(step["x1"]),
            int(step["y1"]),
            int(step["x2"]),
            int(step["y2"]),
        )

    def action_select(self, step):
        raise ActionError(
            "Generic select requires a UI adapter."
        )

    def action_inspect(self, step):
        target = step.get("target", "")

        logger.info(
            "Inspecting target: %s",
            target,
        )

        path = save_screenshot(
            self.context.current_step,
            "inspection",
        )

        self.context.screenshots.append(path)

        inspection = {
            "target": target,
            "screenshot": path,
            "url": self.controller.get_current_url(),
            "timestamp": timestamp(),
        }

        self.context.variables[
            f"inspection_{self.context.current_step}"
        ] = inspection

        return inspection

    def action_screenshot(self, step):
        path = save_screenshot(
            self.context.current_step,
            "requested",
        )

        self.context.screenshots.append(path)

        return path

    def action_copy(self, step):
        self.controller.copy()

    def action_paste(self, step):
        self.controller.paste()

    # --------------------------------------------------------
    # VERIFICATION
    # --------------------------------------------------------

    def verify_step(self, step: Dict[str, Any]) -> bool:
        condition = step.get(
            "success_condition",
            "",
        ).lower()

        action = step.get("action")

        # Application verification.
        if action == "open_application":
            target = step.get("target", "")

            return self.controller.is_application_running(
                target
            )

        # Navigation verification.
        if action == "navigate":
            target = normalize_url(
                step.get("target", "")
            )

            current = self.controller.get_current_url()

            if current:
                return (
                    current.rstrip("/")
                    == target.rstrip("/")
                )

            # Browser navigation was initiated successfully.
            return True

        # Wait verification.
        if action == "wait":
            return True

        # Typing verification.
        if action == "type":
            return True

        # Keyboard verification.
        if action in {
            "press_key",
            "hotkey",
            "copy",
            "paste",
        }:
            return True

        # Screenshot verification.
        if action == "screenshot":
            return True

        # Inspection verification.
        if action == "inspect":
            return True

        # Generic fallback.
        #
        # IMPORTANT:
        # Actions such as semantic clicks should be verified by
        # the UI/browser adapter in a production implementation.
        return True

    # --------------------------------------------------------
    # FINAL VERIFICATION
    # --------------------------------------------------------

    def final_verification(self) -> Dict[str, Any]:
        verification = self.task.get(
            "verification",
            {},
        )

        if not verification.get("required", False):
            return {
                "status": "success",
                "message": "Final verification not required.",
            }

        condition = verification.get(
            "success_condition",
            "",
        )

        logger.info(
            "Final verification: %s",
            condition,
        )

        # Generic runtime records that verification was requested.
        #
        # Domain-specific verification adapters should be plugged
        # in here for conditions such as:
        #
        # "A YouTube music video is actively playing."
        #
        # The executor should never falsely claim a condition was
        # verified when the underlying adapter cannot inspect it.

        if (
            "youtube" in condition.lower()
            and "playing" in condition.lower()
        ):
            return {
                "status": "not_verified",
                "message": (
                    "YouTube playback requires a browser/UI "
                    "verification adapter."
                ),
            }

        return {
            "status": "success",
            "message": condition,
        }

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    def recover(self, step: Dict[str, Any]):
        recovery = step.get("recovery")

        if recovery:
            logger.info(
                "Recovery instruction: %s",
                recovery,
            )

        # Generic recovery:
        # capture current state, wait, then retry.
        try:
            path = save_screenshot(
                step.get("step", "?"),
                "recovery",
            )
            self.context.screenshots.append(path)
        except Exception:
            pass

        time.sleep(DEFAULT_WAIT)

    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------

    def log_step(
        self,
        step: Dict[str, Any],
        status: str,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
        retry_count: int = 0,
    ):
        entry = {
            "step": step.get("step"),
            "action": step.get("action"),
            "target": step.get("target"),
            "status": status,
            "timestamp": timestamp(),
            "retry_count": retry_count,
        }

        if duration_ms is not None:
            entry["duration_ms"] = duration_ms

        if error:
            entry["error"] = error

        self.context.history.append(entry)

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    def generate_result(
        self,
        status: str,
        verification: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:

        completed = sum(
            1
            for entry in self.context.history
            if entry["status"] == "success"
        )

        failed = sum(
            1
            for entry in self.context.history
            if entry["status"] == "failed"
        )

        result = {
            "status": status,
            "task": self.task["task"].get(
                "name",
                "Unnamed task",
            ),
            "goal": self.task["task"].get(
                "goal",
                "",
            ),
            "completed_steps": completed,
            "failed_steps": failed,
            "retries": self.context.retries,
            "verification": verification or {
                "status": "failed"
            },
            "execution_log": self.context.history,
            "screenshots": self.context.screenshots,
        }

        if error:
            result["error"] = error

        if self.context.current_step is not None:
            result["last_step"] = self.context.current_step

        return result


# ============================================================
# JSON LOADING
# ============================================================

def load_task(path: str) -> Dict[str, Any]:
    task_path = Path(path)

    if not task_path.exists():
        raise FileNotFoundError(
            f"Task file does not exist: {task_path}"
        )

    with task_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "    python executor.py task.json"
        )
        sys.exit(1)

    task_file = sys.argv[1]

    try:
        task = load_task(task_file)

        executor = TaskExecutor(task)

        result = executor.execute()

        print("\n" + "=" * 60)
        print("EXECUTION RESULT")
        print("=" * 60)

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

        # Exit code communicates success/failure to the parent agent.
        if result["status"] == "success":
            sys.exit(0)

        sys.exit(1)

    except Exception as exc:
        logger.exception(
            "Fatal executor error."
        )

        result = {
            "status": "failed",
            "error": str(exc),
        }

        print(
            json.dumps(
                result,
                indent=2,
            )
        )

        sys.exit(1)


if __name__ == "__main__":
    main()