"""Declarative catalog for broad task routing and website-assisted planning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AutomationDefinition:
    automation_id: str
    name: str
    category: str
    objective: str
    tools: frozenset[str]
    permissions: frozenset[str]
    external_dependency: str | None = None


def _definitions() -> tuple[AutomationDefinition, ...]:
    groups = {
        "desktop": [
            ("launch-calculator", "Open Calculator", "desktop.launch"),
            ("calculate-expression", "Calculate expression", "desktop.calculator"),
            ("launch-notepad", "Open Notepad", "desktop.launch"),
            ("type-visible-text", "Type visible text", "desktop.type"),
            ("launch-paint", "Open Paint", "desktop.launch"),
            ("launch-explorer", "Open File Explorer", "desktop.launch"),
            ("launch-settings", "Open Windows Settings", "desktop.launch"),
            ("capture-desktop", "Capture desktop evidence", "screen.capture"),
            ("click-screen-control", "Click a verified screen control", "mouse.click"),
            ("type-keyboard-text", "Type keyboard text", "keyboard.write"),
            ("open-task-manager", "Open Task Manager", "desktop.launch"),
            ("open-terminal", "Open terminal", "desktop.launch"),
            ("open-control-panel", "Open Control Panel", "desktop.launch"),
            ("open-device-manager", "Open Device Manager", "desktop.launch"),
            ("open-system-info", "Open system information", "desktop.launch"),
            ("open-snipping-tool", "Open Snipping Tool", "desktop.launch"),
            ("open-calendar", "Open Calendar", "desktop.launch"),
            ("open-clock", "Open Clock", "desktop.launch"),
            ("open-photos", "Open Photos", "desktop.launch"),
            ("open-wordpad", "Open WordPad", "desktop.launch"),
        ],
        "browser": [
            ("navigate-url", "Navigate to a URL", "browser.navigate"),
            ("read-page-title", "Read page title", "browser.read_title"),
            ("fill-web-form", "Fill a verified web form", "browser.type"),
            ("search-web", "Search the web", "browser.navigate"),
            ("research-topic", "Research a topic through the chatbot website", "browser.navigate"),
            ("open-chatgpt", "Open ChatGPT webpage", "browser.navigate"),
            ("open-gemini", "Open Gemini webpage", "browser.navigate"),
            ("open-claude", "Open Claude webpage", "browser.navigate"),
            ("capture-webpage", "Capture webpage evidence", "screen.capture"),
            ("play-youtube", "Play a YouTube video", "youtube.play"),
            ("open-documentation", "Open technical documentation", "browser.navigate"),
            ("compare-web-sources", "Compare web sources", "browser.navigate"),
            ("extract-page-title", "Extract page title", "browser.read_title"),
            ("open-localhost", "Open a local web app", "browser.navigate"),
            ("inspect-browser-state", "Inspect browser state", "browser.read_title"),
            ("open-search-results", "Open search results", "browser.navigate"),
            ("submit-safe-form", "Submit a non-sensitive form", "browser.type"),
            ("open-video-reference", "Open a video reference", "browser.navigate"),
            ("open-3d-reference", "Open a 3D reference", "browser.navigate"),
            ("open-game-dev-reference", "Open game development reference", "browser.navigate"),
        ],
        "files": [
            ("write-text-file", "Write a text file", "filesystem.write"),
            ("write-json-file", "Write a JSON file", "filesystem.write"),
            ("write-csv-file", "Write a CSV file", "filesystem.write"),
            ("create-project-folder", "Create a project folder", "filesystem.write"),
            ("save-research-notes", "Save research notes", "filesystem.write"),
            ("save-task-result", "Save task result", "filesystem.write"),
            ("create-markdown-report", "Create a Markdown report", "filesystem.write"),
            ("create-config-file", "Create a configuration file", "filesystem.write"),
            ("export-browser-evidence", "Export browser evidence", "filesystem.write"),
            ("prepare-media-manifest", "Prepare media manifest", "filesystem.write"),
            ("prepare-blender-manifest", "Prepare Blender manifest", "filesystem.write"),
            ("prepare-unreal-manifest", "Prepare Unreal manifest", "filesystem.write"),
            ("save-automation-plan", "Save automation plan", "filesystem.write"),
            ("save-learning-record", "Save learning record", "filesystem.write"),
            ("save-verification-report", "Save verification report", "filesystem.write"),
        ],
        "video": [
            ("video-trim", "Trim a video", "video.edit"),
            ("video-transcode", "Transcode a video", "video.edit"),
            ("video-extract-audio", "Extract audio from video", "video.edit"),
            ("video-change-format", "Change video format", "video.edit"),
            ("video-resize", "Resize a video", "video.edit"),
            ("video-add-subtitles", "Add subtitles to a video", "video.edit"),
            ("video-burn-captions", "Burn captions into a video", "video.edit"),
            ("video-join-clips", "Join video clips", "video.edit"),
            ("video-extract-frame", "Extract a video frame", "video.edit"),
            ("video-create-preview", "Create a video preview", "video.edit"),
            ("video-normalize-audio", "Normalize video audio", "video.edit"),
            ("video-remove-silence", "Remove silent sections", "video.edit"),
            ("video-add-watermark", "Add a watermark", "video.edit"),
            ("video-create-social-cut", "Create a social-media cut", "video.edit"),
            ("video-verify-output", "Verify a rendered video", "video.edit"),
        ],
        "blender": [
            ("blender-open-project", "Open a Blender project", "blender.open"),
            ("blender-create-scene", "Create a Blender scene", "blender.scene"),
            ("blender-add-cube", "Create a cube in Blender", "blender.scene"),
            ("blender-add-sphere", "Create a sphere in Blender", "blender.scene"),
            ("blender-add-camera", "Add a camera in Blender", "blender.scene"),
            ("blender-add-light", "Add a light in Blender", "blender.scene"),
            ("blender-apply-material", "Apply a material in Blender", "blender.scene"),
            ("blender-model-object", "Model a 3D object", "blender.scene"),
            ("blender-import-model", "Import a 3D model", "blender.scene"),
            ("blender-export-model", "Export a 3D model", "blender.scene"),
            ("blender-render-image", "Render a Blender image", "blender.render"),
            ("blender-render-animation", "Render a Blender animation", "blender.render"),
            ("blender-create-turntable", "Create a turntable render", "blender.render"),
            ("blender-setup-lighting", "Set up Blender lighting", "blender.scene"),
            ("blender-verify-scene", "Verify a Blender scene", "blender.inspect"),
        ],
        "unreal": [
            ("unreal-open-project", "Open an Unreal project", "unreal.open"),
            ("unreal-create-project", "Create an Unreal project", "unreal.project"),
            ("unreal-create-level", "Create an Unreal level", "unreal.editor"),
            ("unreal-add-static-mesh", "Add a static mesh", "unreal.editor"),
            ("unreal-add-camera", "Add an Unreal camera", "unreal.editor"),
            ("unreal-add-light", "Add an Unreal light", "unreal.editor"),
            ("unreal-import-asset", "Import an Unreal asset", "unreal.editor"),
            ("unreal-create-material", "Create an Unreal material", "unreal.editor"),
            ("unreal-create-blueprint", "Create a Blueprint", "unreal.editor"),
            ("unreal-create-character", "Create a character prototype", "unreal.editor"),
            ("unreal-create-ui", "Create Unreal UI", "unreal.editor"),
            ("unreal-package-build", "Package an Unreal build", "unreal.build"),
            ("unreal-run-editor-test", "Run an Unreal editor test", "unreal.test"),
            ("unreal-capture-screenshot", "Capture an Unreal screenshot", "unreal.editor"),
            ("unreal-verify-project", "Verify an Unreal project", "unreal.inspect"),
        ],
    }
    result: list[AutomationDefinition] = []
    for category, items in groups.items():
        for automation_id, name, tool in items:
            external = "ffmpeg" if category == "video" else "blender" if category == "blender" else "unreal" if category == "unreal" else None
            result.append(AutomationDefinition(
                automation_id, name, category, name, frozenset({tool}), frozenset(),
                external,
            ))
    assert len(result) == 100
    return tuple(result)


AUTOMATIONS = _definitions()
AUTOMATIONS_BY_ID = {item.automation_id: item for item in AUTOMATIONS}


class AutomationCatalog:
    def __init__(self, definitions: tuple[AutomationDefinition, ...] = AUTOMATIONS) -> None:
        self._definitions = {item.automation_id: item for item in definitions}

    def get(self, automation_id: str) -> AutomationDefinition:
        return self._definitions[automation_id]

    def all(self) -> tuple[AutomationDefinition, ...]:
        return tuple(self._definitions.values())

    def matching(self, text: str) -> tuple[AutomationDefinition, ...]:
        lowered = text.casefold()
        return tuple(item for item in self._definitions.values()
                     if item.name.casefold() in lowered or item.category in lowered
                     or item.automation_id.replace("-", " ") in lowered)

    @staticmethod
    def reasoning_prompt(goal: str, candidates: tuple[AutomationDefinition, ...]) -> str:
        data: list[dict[str, Any]] = [
            {"id": item.automation_id, "objective": item.objective,
             "tools": sorted(item.tools), "external_dependency": item.external_dependency}
            for item in candidates
        ]
        return (
            "Use the browser website reasoning session to plan this task. "
            "Choose only from the provided automation catalog. Return JSON with "
            "selected_id, ordered_steps, required_inputs, expected_outputs, and "
            "verification. Never return executable code or shell commands.\n"
            f"GOAL={goal}\nCATALOG={data}"
        )
