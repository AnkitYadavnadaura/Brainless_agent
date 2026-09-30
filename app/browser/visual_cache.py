"""Visual element caching and multimodal LLM screenshot analysis for browser automation."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


class VisualElementCache:
    """Store and retrieve analyzed UI element coordinates for fast subsequent reuse."""

    def __init__(self, cache_file: Path | None = None) -> None:
        self.cache_file = cache_file or (Path(__file__).resolve().parents[2] / "data" / "visual_elements_cache.json")
        self._cache: dict[str, dict[str, Any]] = {}
        self.load_from_disk()

    @staticmethod
    def _normalize_key(url: str, window_bounds: tuple[int, int, int, int] | None = None) -> str:
        parts = urlsplit(url)
        clean_url = f"{parts.scheme}://{parts.netloc}{parts.path}".rstrip("/")
        if window_bounds:
            w, h = window_bounds[2], window_bounds[3]
            return f"{clean_url}@{w}x{h}"
        return clean_url

    def get(self, url: str, window_bounds: tuple[int, int, int, int] | None = None) -> list[dict[str, Any]] | None:
        """Retrieve cached elements for a given URL and viewport."""
        key = self._normalize_key(url, window_bounds)
        entry = self._cache.get(key)
        if entry:
            return [dict(item) for item in entry.get("elements", [])]
        clean_url = self._normalize_key(url, None)
        entry = self._cache.get(clean_url)
        if entry:
            return [dict(item) for item in entry.get("elements", [])]
        for k, e in self._cache.items():
            if k == clean_url or k.startswith(clean_url + "@"):
                return [dict(item) for item in e.get("elements", [])]
        return None

    def put(self, url: str, window_bounds: tuple[int, int, int, int] | None,
            elements: list[dict[str, Any]], screenshot_hash: str | None = None) -> None:
        """Store analyzed elements for future use."""
        if not elements or not url:
            return
        key = self._normalize_key(url, window_bounds)
        self._cache[key] = {
            "url": url,
            "bounds": list(window_bounds) if window_bounds else None,
            "hash": screenshot_hash,
            "elements": [dict(e) for e in elements],
        }
        self.save_to_disk()

    def find_by_label(self, url: str, label: str) -> dict[str, Any] | None:
        """Look up a cached element by matching text/label."""
        elements = self.get(url)
        if not elements:
            return None
        target = label.strip().casefold()
        for elem in elements:
            elem_text = elem.get("label", elem.get("text", "")).strip().casefold()
            if target == elem_text or target in elem_text or elem_text in target:
                return dict(elem)
        return None

    def invalidate(self, url: str | None = None) -> None:
        """Invalidate cache entries for a specific URL or clear all."""
        if url:
            clean_url = self._normalize_key(url, None)
            keys_to_remove = [k for k in self._cache if k.startswith(clean_url)]
            for k in keys_to_remove:
                self._cache.pop(k, None)
        else:
            self._cache.clear()
        self.save_to_disk()

    def load_from_disk(self) -> None:
        if self.cache_file and self.cache_file.is_file():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._cache = data
            except Exception as error:
                logger.warning("Could not load visual element cache: %s", error)

    def save_to_disk(self) -> None:
        if not self.cache_file:
            return
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
        except Exception as error:
            logger.warning("Could not save visual element cache to disk: %s", error)


_default_cache = VisualElementCache()


def get_visual_cache() -> VisualElementCache:
    return _default_cache


async def analyze_screenshot_with_llm(
    provider: Any,
    image_bytes: bytes,
    url: str,
    window_bounds: tuple[int, int, int, int] = (0, 0, 800, 600),
    elements_hint: list[dict[str, Any]] | None = None,
    cache: VisualElementCache | None = None,
) -> list[dict[str, Any]]:
    """Send screenshot and observed content to Browser LLM to detect buttons and coordinates.

    Saves results into VisualElementCache for future use.
    """
    cache = cache or get_visual_cache()
    cached = cache.get(url, window_bounds)
    if cached:
        return cached

    image_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    prompt = (
        "You are an expert visual UI analysis engine. Analyze the provided webpage screenshot and detect all visible "
        "interactive buttons, clickable links, input fields, tabs, and key content controls with their exact bounding box coordinates.\n\n"
        f"PAGE_URL: {url}\n"
        f"VIEWPORT_BOUNDS: {list(window_bounds)}\n"
    )
    if elements_hint:
        prompt += f"OBSERVED_HINTS: {json.dumps(elements_hint[:25], ensure_ascii=True)}\n"

    prompt += (
        "\nReturn only a valid JSON array of objects with exact coordinates [left, top, width, height] relative to the viewport:\n"
        '[{"label": "button text", "type": "button|link|input|control", "rect": [x, y, w, h], "confidence": 0.95, "purpose": "description"}]\n'
        "Do not include markdown prose outside the JSON code block."
    )

    try:
        # Check if provider supports multimodal complete with images
        import inspect
        complete_multimodal = getattr(provider, "complete_multimodal", None)
        complete = getattr(provider, "complete", None)
        response: str | None = None

        if callable(complete_multimodal):
            try:
                res = complete_multimodal(prompt, image_bytes=image_bytes)
                res = await res if inspect.isawaitable(res) else res
                if isinstance(res, str):
                    response = res
            except Exception:
                pass

        if response is None and callable(complete):
            try:
                res = complete(prompt, image_bytes=image_bytes)
                res = await res if inspect.isawaitable(res) else res
                if isinstance(res, str):
                    response = res
            except TypeError:
                pass
            if response is None:
                try:
                    res = complete(prompt)
                    res = await res if inspect.isawaitable(res) else res
                    if isinstance(res, str):
                        response = res
                except Exception:
                    pass

        if response is None and hasattr(provider, "send_prompt") and hasattr(provider, "extract_response"):
            try:
                await provider.send_prompt(prompt)
                await provider.wait_for_response(30)
                res = await provider.extract_response()
                if isinstance(res, str):
                    response = res
            except Exception:
                pass

        if response is None:
            return []

        if not isinstance(response, str):
            return []

        # Parse JSON from response
        import re
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.IGNORECASE | re.DOTALL)
        candidate = fenced.group(1).strip() if fenced else response.strip()
        data = None
        try:
            data = json.loads(candidate)
        except Exception:
            bracket_match = re.search(r"(\[.*\])", candidate, re.DOTALL)
            if bracket_match:
                try:
                    data = json.loads(bracket_match.group(1))
                except Exception:
                    pass

        if not isinstance(data, list):
            return []

        analyzed_elements = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", item.get("text", ""))).strip()
            rect = item.get("rect")
            if not label or not isinstance(rect, list) or len(rect) != 4:
                continue
            x, y, w, h = int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])
            elem_type = str(item.get("type", "button")).lower()
            runtime_id = f"visual.{x}.{y}"
            analyzed_elements.append({
                "label": label,
                "type": f"ControlType.{elem_type.capitalize()}",
                "rect": [window_bounds[0] + x, window_bounds[1] + y, w, h],
                "runtime_id": runtime_id,
                "confidence": float(item.get("confidence", 0.9)),
                "purpose": str(item.get("purpose", "")),
                "source": "visual_cache",
            })

        if analyzed_elements:
            cache.put(url, window_bounds, analyzed_elements, screenshot_hash=image_hash)

        return analyzed_elements
    except Exception as error:
        logger.warning("Multimodal screenshot analysis failed: %s", error)
        return []
