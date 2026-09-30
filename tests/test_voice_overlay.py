import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.voice import overlay as overlay_module
from app.voice.overlay import TopmostQuestionOverlay, _OverlayPanel, _pin_without_activation


def test_dismiss_waits_until_question_has_transitioned_to_status():
    overlay = TopmostQuestionOverlay()
    processed = threading.Event()

    def consume_dismiss():
        action, value, acknowledged = overlay._commands.get(timeout=1)
        assert action == "dismiss"
        assert value is None
        acknowledged.set()
        processed.set()

    worker = threading.Thread(target=consume_dismiss)
    overlay._thread = worker
    worker.start()

    overlay.dismiss()

    worker.join(timeout=1)
    assert processed.is_set()
    assert not worker.is_alive()


class FakeWindow:
    def __init__(self, _root=None):
        self.exists = True
        self.events = []
        self.configuration = {}

    def withdraw(self): self.events.append("withdraw")
    def title(self, text): self.window_title = text
    def configure(self, **values): self.configuration.update(values)
    def overrideredirect(self, enabled): self.borderless = enabled
    def resizable(self, *_): pass
    def protocol(self, *_): pass
    def update_idletasks(self): pass
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def winfo_reqwidth(self): return 372
    def winfo_reqheight(self): return 160
    def winfo_exists(self): return self.exists
    def winfo_id(self): return 123
    def geometry(self, value): self.position = value
    def attributes(self, *values): self.events.append(("attributes", values))
    def deiconify(self): self.events.append("deiconify")
    def lift(self): self.events.append("lift")
    def destroy(self): self.exists = False


class FakeLabel:
    def __init__(self, _window, **values):
        self.values = values

    def pack(self, **_): pass
    def configure(self, **values): self.values.update(values)


def test_questions_and_working_status_reuse_one_edge_panel_without_tk_activation(monkeypatch):
    pinned = []
    monkeypatch.setattr(overlay_module, "_pin_without_activation", lambda window: pinned.append(window) or True)
    tk = SimpleNamespace(Toplevel=FakeWindow, Label=FakeLabel)
    panel = _OverlayPanel(tk, object())

    panel.show("Which browser profile should I use?", question=True)
    window = panel.window
    assert panel.hint.values["text"] == "Answer aloud to continue"
    assert window.position == "+1532+856"
    assert window.configuration["takefocus"] is False

    panel.show("Working…", question=False)
    panel.keep_visible()

    assert panel.window is window
    assert window.exists
    assert panel.message.values["text"] == "Working…"
    assert panel.hint.values["text"] == "Brainless Agent is active"
    assert window.events == ["withdraw"]
    assert pinned == [window, window, window]
    panel.close()
    assert not window.exists


def test_panel_retains_tk_fallback_without_requesting_focus(monkeypatch):
    monkeypatch.setattr(overlay_module, "_pin_without_activation", lambda _: False)
    panel = _OverlayPanel(SimpleNamespace(Toplevel=FakeWindow, Label=FakeLabel), object())

    panel.show("Opening your browser", question=False)

    assert panel.window.events == ["withdraw", ("attributes", ("-topmost", True)), "deiconify", "lift"]


def test_windows_overlay_is_topmost_without_changing_foreground_window(monkeypatch):
    events = []
    api = SimpleNamespace(
        GetAncestor=lambda handle, flag: 456,
        SetWindowPos=lambda *args: events.append(("position", args)) or True,
        ShowWindow=lambda *args: events.append(("show", args)) or True,
        SetWindowDisplayAffinity=lambda *args: events.append(("capture", args)) or True,
    )
    get_style = lambda *_: 0x00040000  # An ordinary app window before conversion.
    set_style = lambda *args: events.append(("style", args))
    monkeypatch.setattr(overlay_module, "_windows_api", lambda: (api, get_style, set_style))

    assert _pin_without_activation(FakeWindow())

    assert events[0] == ("style", (456, -20, 0x08000080))
    assert events[1] == ("capture", (456, 0x11))
    assert events[2] == ("position", (456, -1, 0, 0, 0, 0, 0x53))
    assert events[3] == ("show", (456, 4))


def test_show_status_updates_existing_overlay_worker_without_starting_another():
    overlay = TopmostQuestionOverlay()
    overlay._thread = SimpleNamespace(is_alive=lambda: True)

    overlay.show_status(" Opening the selected profile ")
    overlay.show("What would you like to do?")

    assert overlay._commands.get_nowait() == ("status", "Opening the selected profile", None)
    assert overlay._commands.get_nowait() == ("show", "What would you like to do?", None)
    with pytest.raises(ValueError, match="cannot be empty"):
        overlay.show_status("  ")


def test_overlay_dismiss_command_keeps_working_panel_until_close(monkeypatch):
    import sys

    pending = []
    root = SimpleNamespace(
        withdraw=lambda: None, title=lambda _: None, configure=lambda **_: None,
        after=lambda _delay, callback: pending.append(callback) or f"timer-{len(pending)}",
        after_cancel=Mock(),
        quit=Mock(), destroy=Mock(),
    )
    root.mainloop = lambda: pending[0]()
    monkeypatch.setitem(sys.modules, "tkinter", SimpleNamespace(Tk=lambda: root))
    events = []
    panel = SimpleNamespace(
        show=lambda text, **options: events.append((text, options["question"])),
        keep_visible=lambda: None, close=lambda: events.append(("closed", False)),
    )
    monkeypatch.setattr(overlay_module, "_OverlayPanel", lambda *_: panel)
    acknowledged = threading.Event()
    overlay = TopmostQuestionOverlay()
    overlay._commands.put(("show", "Allow browser access?", None))
    overlay._commands.put(("dismiss", None, acknowledged))
    overlay._commands.put(("status", "Opening YouTube", None))
    overlay._commands.put(("close", None, None))

    overlay._run()

    assert acknowledged.is_set()
    assert events == [
        ("Allow browser access?", True), ("Working…", False),
        ("Opening YouTube", False), ("closed", False),
    ]
    root.quit.assert_called_once()
    root.destroy.assert_called_once()
    assert root.after_cancel.call_count >= 1
