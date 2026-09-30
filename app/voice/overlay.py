"""Persistent, non-activating desktop status and questions for voice sessions."""
from __future__ import annotations

import logging
import os
import queue
import threading
from functools import lru_cache


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _windows_api():
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    set_style.restype = ctypes.c_ssize_t
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    if hasattr(user32, "SetWindowDisplayAffinity"):
        user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    return user32, get_style, set_style


def _pin_without_activation(window) -> bool:
    """Keep the Tk wrapper visible and topmost without taking browser focus."""
    try:
        api = _windows_api()
        if api is None:
            return False
        user32, get_style, set_style = api
        # Tk's widget HWND is a child of the actual top-level wrapper.
        widget_handle = int(window.winfo_id())
        handle = user32.GetAncestor(widget_handle, 2) or widget_handle  # GA_ROOT
        style = get_style(handle, -20)  # GWL_EXSTYLE
        # WS_EX_NOACTIVATE prevents both showing and mouse clicks from stealing
        # focus. WS_EX_TOOLWINDOW keeps this passive panel off the taskbar.
        set_style(handle, -20, (style | 0x08000000 | 0x00000080) & ~0x00040000)
        # Keep the visible panel out of captured browser pixels so OCR cannot
        # mistake the assistant's own question for website content.
        try:
            affinity = getattr(user32, "SetWindowDisplayAffinity", None)
            if affinity is not None:
                affinity(handle, 0x11)  # WDA_EXCLUDEFROMCAPTURE (Windows 10 2004+).
        except Exception:
            logger.debug("Voice overlay capture exclusion is unavailable", exc_info=True)
        # HWND_TOPMOST; SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW.
        if not user32.SetWindowPos(handle, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040):
            return False
        user32.ShowWindow(handle, 4)  # SW_SHOWNOACTIVATE, including after minimization.
        return True
    except Exception:
        logger.debug("Native non-activating voice overlay is unavailable", exc_info=True)
        return False


class _OverlayPanel:
    """All Tk operations stay on the overlay thread."""

    def __init__(self, tk, root) -> None:
        self.tk, self.root = tk, root
        self.window = None
        self.message = None
        self.hint = None

    def show(self, text: str, *, question: bool) -> None:
        if self.window is None or not self.window.winfo_exists():
            self.window = self.tk.Toplevel(self.root)
            self.window.withdraw()
            self.window.title("Brainless Agent · Voice assistant")
            self.window.configure(bg="#10151d", padx=16, pady=12, takefocus=False)
            self.window.overrideredirect(True)
            self.window.resizable(False, False)
            self.window.protocol("WM_DELETE_WINDOW", lambda: None)
            self.tk.Label(
                self.window, text="VOICE ASSISTANT", bg="#10151d", fg="#c4f36b",
                font=("Segoe UI", 9, "bold"), anchor="w",
            ).pack(fill="x")
            self.message = self.tk.Label(
                self.window, text=text, bg="#10151d", fg="#f1f4f1",
                font=("Segoe UI", 13), justify="left", wraplength=340, anchor="w",
            )
            self.message.pack(fill="x", pady=(6, 8))
            self.hint = self.tk.Label(
                self.window, bg="#10151d", fg="#87929f", font=("Segoe UI", 9), anchor="w",
            )
            self.hint.pack(fill="x")
        self.message.configure(text=text)
        self.hint.configure(text="Answer aloud to continue" if question else "Brainless Agent is active")
        self.window.update_idletasks()
        x = max(0, self.window.winfo_screenwidth() - self.window.winfo_reqwidth() - 16)
        y = max(0, self.window.winfo_screenheight() - self.window.winfo_reqheight() - 64)
        self.window.geometry(f"+{x}+{y}")
        self.window.update_idletasks()
        self.keep_visible()

    def keep_visible(self) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        if _pin_without_activation(self.window):
            return
        # Tk fallback for platforms without the Windows API. Never focus the panel.
        self.window.attributes("-topmost", True)
        self.window.deiconify()
        self.window.lift()

    def close(self) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None
            self.message = self.hint = None


class TopmostQuestionOverlay:
    """Keep task status and spoken questions visible until the session closes."""

    def __init__(self) -> None:
        self._commands: queue.Queue[
            tuple[str, str | None, threading.Event | None]
        ] = queue.Queue()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def show(self, question: str) -> None:
        self._display("show", question)

    def show_status(self, text: str) -> None:
        self._display("status", text)

    def _display(self, action: str, value: str) -> None:
        text = value.strip()
        if not text:
            raise ValueError("Overlay text cannot be empty")
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name="voice-question-overlay", daemon=True
                )
                self._thread.start()
            self._commands.put((action, text[:2_000], None))

    def dismiss(self) -> None:
        thread = self._thread
        if thread is None or not thread.is_alive():
            return
        updated = threading.Event()
        self._commands.put(("dismiss", None, updated))
        if not updated.wait(timeout=5):
            logger.error("Voice overlay did not update before desktop input")
            raise RuntimeError(
                "The voice overlay could not update its status; desktop input was stopped")

    def close(self) -> None:
        thread = self._thread
        if thread is None:
            return
        self._commands.put(("close", None, None))
        if thread is not threading.current_thread():
            thread.join(timeout=2)

    def _run(self) -> None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.withdraw()
            root.title("Brainless Agent · Voice assistant")
            root.configure(bg="#10151d")
            panel = _OverlayPanel(tk, root)

            running = True
            keep_id = None
            drain_id = None

            def keep_visible() -> None:
                nonlocal keep_id
                if not running:
                    return
                panel.keep_visible()
                keep_id = root.after(500, keep_visible)

            def drain() -> None:
                nonlocal running, drain_id
                while True:
                    try:
                        action, value, completed = self._commands.get_nowait()
                    except queue.Empty:
                        break
                    if action == "show" and value is not None:
                        panel.show(value, question=True)
                    elif action == "status" and value is not None:
                        panel.show(value, question=False)
                    elif action == "dismiss":
                        panel.show("Working…", question=False)
                        if completed is not None:
                            completed.set()
                    elif action == "close":
                        running = False
                        panel.close()
                        if completed is not None:
                            completed.set()
                        root.quit()
                        return
                if running:
                    drain_id = root.after(50, drain)

            drain_id = root.after(50, drain)
            keep_id = root.after(500, keep_visible)
            root.mainloop()
            if keep_id is not None and hasattr(root, "after_cancel"):
                try:
                    root.after_cancel(keep_id)
                except Exception:
                    pass
            if drain_id is not None and hasattr(root, "after_cancel"):
                try:
                    root.after_cancel(drain_id)
                except Exception:
                    pass
            root.destroy()
            del panel
            del root
            import gc
            gc.collect()
        except Exception:
            logger.exception("Could not display the voice question overlay")
