"""Task-scoped capability catalog projected from registered runtime tools."""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from typing import Any


_CAPABILITY_INFO = {
    "browser": "Navigate and interact with supported browser pages",
    "desktop": "Control visible desktop applications and capture screen evidence",
    "files": "Read or write files through registered, permission-gated operations",
    "media": "Find and play supported audio or video content",
    "email": "Compose and send email through an authenticated mail application",
    "development": "Work with registered development tools and workspace operations",
    "creative": "Operate registered 3D, Blender, Unreal, or creative tools",
    "system": "Use other registered runtime capabilities",
}
_CATEGORY_TERMS = {
    "browser": ("browser", "web", "website", "chrome", "internet", "search", "url", "youtube", "crawl", "click", "button", "link", "page", "explore", "navigate", "site"),
    "desktop": ("desktop", "computer", "window", "screen", "mouse", "click", "keyboard",
                "type", "application", "app", "software", "calculator"),
    "files": ("file", "files", "folder", "directory", "document", "save", "read", "write",
              "delete", "rename"),
    "media": ("music", "song", "video", "movie", "youtube", "spotify", "play", "pause",
              "skip ad", "skip", "forward", "backward", "rewind", "next video", "audio"),
    "email": ("email", "e-mail", "gmail", "mail", "send a message", "send email"),
    "development": ("code", "coding", "repository", "repo", "git", "vscode", "terminal",
                    "command", "python", "extension", "build", "test"),
    "creative": ("blender", "unreal", "3d", "scene", "model", "render", "game engine",
                 "game-editor"),
}


def _capability_for(function: dict[str, Any]) -> str:
    tool_id = function["function"]
    namespace = tool_id.split(".", 1)[0].casefold()
    category = str(function.get("category", "")).casefold()
    if namespace in {"browser"}:
        return "browser"
    if namespace in {"youtube", "video", "audio", "media"}:
        return "media"
    if namespace in {"gmail", "email", "mail"}:
        return "email"
    if namespace in {"filesystem", "file"}:
        return "files"
    if namespace in {"desktop", "keyboard", "mouse", "screen"}:
        return "desktop"
    if namespace in {"vscode", "process", "git"}:
        return "development"
    if namespace in {"blender", "unreal", "3d", "game"} or any(
            term in category for term in ("blender", "unreal", "3d", "creative", "game")):
        return "creative"
    return "system"


def build_action_catalog(
    functions: Iterable[dict[str, Any]],
    objective: str,
    template_id: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Return compact, relevant capability groups and their exact registered schemas."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for function in functions:
        grouped[_capability_for(function)].append(function)

    text = objective.casefold()
    selected = {
        capability for capability, terms in _CATEGORY_TERMS.items()
        if any(term in text for term in terms)
    }
    if template_id == "creative_3d_operator":
        selected.add("creative")
    if not selected:
        selected = set(grouped)
    if "media" in selected:
        selected.add("browser")
    if "desktop" in selected:
        selected.add("browser")
    if "browser" in selected:
        selected.add("desktop")
    if "development" in selected:
        selected.add("files")
    if "email" in selected:
        selected.add("browser")

    capabilities = []
    allowed: dict[str, dict[str, Any]] = {}
    for capability in sorted(selected):
        actions = sorted(grouped.get(capability, ()), key=lambda item: item["function"])
        if not actions:
            continue
        capabilities.append({
            "capability": capability,
            "description": _CAPABILITY_INFO.get(capability, _CAPABILITY_INFO["system"]),
            "actions": actions,
        })
        allowed.update((item["function"], item) for item in actions)

    return {"capabilities": capabilities}, allowed


def capability_summary(functions: Iterable[dict[str, Any]]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for function in functions:
        counts[_capability_for(function)] += 1
    return json.dumps([
        {"capability": capability,
         "description": _CAPABILITY_INFO.get(capability, _CAPABILITY_INFO["system"]),
         "available_actions": count}
        for capability, count in sorted(counts.items())
    ], ensure_ascii=True, sort_keys=True)
