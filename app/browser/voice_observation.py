"""Read-only viewport evidence for governed browser voice follow-ups."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.computer.ocr import OcrReader, OcrUnavailable
from app.safety.redaction import redact


# Runtime-owned extraction code. Website content is evidence, never instructions.
_VIEWPORT_SCRIPT = """() => {
  const visible = node => {
    const r = node.getBoundingClientRect(), s = getComputedStyle(node);
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 &&
      r.top < innerHeight && r.left < innerWidth && s.display !== 'none' &&
      s.visibility !== 'hidden' && s.opacity !== '0' && !node.closest('[aria-hidden="true"]');
  };
  const elements = [], videos = [], seen = new Set();
  const nodes = document.querySelectorAll('a,button,input,select,[role="button"],[role="link"]');
  for (const node of [...nodes].slice(0, 1200)) {
    if (!visible(node)) continue;
    const label = (node.getAttribute('aria-label') || node.getAttribute('title') ||
      node.innerText || node.getAttribute('placeholder') || '').trim().slice(0, 180);
    if (elements.length < 60 && label) elements.push({role: node.getAttribute('role') ||
      node.tagName.toLowerCase(), label, href: node.tagName === 'A' ? node.href : null,
      enabled: !node.disabled});
    if (node.tagName === 'A' && videos.length < 20) {
      const url = new URL(node.href, location.href);
      if (['www.youtube.com', 'youtube.com', 'm.youtube.com'].includes(url.hostname) &&
          url.pathname === '/watch' && url.searchParams.get('v') && !seen.has(url.searchParams.get('v'))) {
        const card = node.closest('ytd-rich-item-renderer,ytd-video-renderer,ytd-compact-video-renderer');
        const titleNode = card && card.querySelector('#video-title,#video-title-link,[title]');
        const title = (titleNode && (titleNode.getAttribute('title') || titleNode.textContent) || label).trim().slice(0, 200);
        seen.add(url.searchParams.get('v'));
        videos.push({title, url: 'https://www.youtube.com/watch?v=' + encodeURIComponent(url.searchParams.get('v'))});
      }
    }
  }
  const text = [];
  if (document.body) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node, length = 0, count = 0;
    while ((node = walker.nextNode()) && count++ < 2500 && length < 5000) {
      const parent = node.parentElement;
      if (!parent || parent.closest('script,style,noscript,input,textarea,[contenteditable]:not([contenteditable="false"])') || !visible(parent)) continue;
      const value = node.textContent.trim();
      if (value) { text.push(value); length += value.length; }
    }
  }
  const video = document.querySelector('video');
  return {visible_text: text.join(' ').slice(0, 5000), elements, videos,
    player: video ? {present: true, paused: video.paused, ended: video.ended,
      current_time: video.currentTime, ready_state: video.readyState} : {present: false}};
}"""


class BrowserVoiceObserver:
    """Capture the existing user tab only; this class never navigates or clicks."""

    def __init__(self, browser, *, ocr: OcrReader | None = None) -> None:
        self.browser = browser
        self.ocr = ocr or OcrReader()

    async def capture(self) -> dict[str, Any]:
        page = self.browser.current_user_page()
        if page is None:
            return {"available": False, "reason": "No user browser tab is open",
                    "trust": "untrusted_observation_data"}
        url = page.url
        snapshot: dict[str, Any] = {
            "available": True, "tab_id": self.browser.tab_id_for(page), "url": url,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "trust": "untrusted_observation_data", "visible_text": "", "elements": [],
            "videos": [], "player": {"present": False}, "ocr_text": "", "ocr_status": "unavailable",
        }
        try:
            snapshot["title"] = (await asyncio.wait_for(page.title(), timeout=3))[:300]
            details = await asyncio.wait_for(page.evaluate(_VIEWPORT_SCRIPT), timeout=4)
            snapshot.update({key: details[key] for key in ("visible_text", "elements", "videos", "player")
                             if key in details})
            snapshot["dom_status"] = "captured"
        except Exception as error:
            snapshot["dom_status"] = "unavailable"
            snapshot["dom_error"] = type(error).__name__
        try:
            # Hide editable content in the OCR image; never inspect passwords or drafts.
            image = await page.screenshot(type="png", full_page=False, timeout=5_000,
                mask=[page.locator('input,textarea,[contenteditable]:not([contenteditable="false"])')])
            snapshot["ocr_text"] = (await asyncio.wait_for(
                asyncio.to_thread(self.ocr.read_bytes, image), timeout=7))[:5000]
            snapshot["ocr_status"] = "captured" if snapshot["ocr_text"] else "empty"
        except OcrUnavailable as error:
            snapshot["ocr_error"] = str(error)
        except Exception as error:
            snapshot["ocr_status"] = "failed"
            snapshot["ocr_error"] = type(error).__name__
        if page.is_closed() or page.url != url or self.browser.current_user_page() is not page:
            return {"available": False, "tab_id": snapshot["tab_id"],
                    "reason": "The browser page changed during observation; observe again",
                    "trust": "untrusted_observation_data"}
        return redact(snapshot)
