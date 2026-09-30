from app.agents.tools import ToolRegistry
from app.computer.desktop import register_desktop_tools


class FakeKeyboard:
    def __init__(self):
        self.calls = []

    def type_text(self, text):
        self.calls.append(("type", text))

    def press_hotkey(self, *keys):
        self.calls.append(("hotkey", keys))


class FakeLauncher:
    def __init__(self):
        self.calls = []

    def launch(self, application):
        self.calls.append(application)


def test_desktop_tools_use_allowlisted_launcher_and_keyboard():
    keyboard, launcher = FakeKeyboard(), FakeLauncher()
    launch, type_visible, calculator = register_desktop_tools(
        ToolRegistry(), keyboard=keyboard, launcher=launcher)
    assert launch({"application": "notepad"}) == "notepad"
    assert type_visible({"text": "hello"}) == "typed"
    assert calculator({"expression": "12+8"}) == "12+8"
    assert launcher.calls == ["notepad", "calculator"]
    assert keyboard.calls == [
        ("type", "hello"),
        ("type", "12+8"),
        ("hotkey", ("enter",)),
    ]
