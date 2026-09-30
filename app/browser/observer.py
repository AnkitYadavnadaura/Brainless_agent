"""Structured, bounded observations of visible browser controls."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ObservedElement:
    target_id: str
    role: str
    name: str
    visible: bool
    enabled: bool
    href: str | None = None
    input_type: str | None = None
    external: bool = False


@dataclass(frozen=True, slots=True)
class PageObservation:
    tab_id: str
    url: str
    title: str
    visible_text: str
    elements: tuple[ObservedElement, ...]
    generation: int


class BrowserObserver:
    """Uses read-only Playwright locator APIs; no model-provided JavaScript."""

    SELECTOR = (
        "a,button,input,textarea,select,video,[role=button],[role=link],"
        "[role=textbox],[contenteditable=true]"
    )
    MAX_ELEMENTS = 100
    MAX_VISIBLE_TEXT = 20_000

    async def observe(self, tab_id: str, page, generation: int) -> PageObservation:
        title = (await page.title())[:500]
        visible_text = (await page.locator("body").inner_text())[:self.MAX_VISIBLE_TEXT]
        locator = page.locator(self.SELECTOR)
        count = min(await locator.count(), self.MAX_ELEMENTS)
        elements = []
        for index in range(count):
            item = locator.nth(index)
            try:
                if not await item.is_visible():
                    continue
                tag = await item.evaluate("(node) => node.tagName.toLowerCase()")
                role = (await item.get_attribute("role")) or tag
                name = ((await item.get_attribute("aria-label"))
                        or (await item.get_attribute("placeholder"))
                        or (await item.inner_text())
                        or (await item.get_attribute("title"))
                        or "")[:300]
                href = await item.get_attribute("href") if tag == "a" else None
                input_type = await item.get_attribute("type")
                enabled = await item.is_enabled()
                external = (
                    input_type == "submit"
                    or ((tag in {"button", "a"} or role in {"button", "link"})
                        and any(term in name.casefold()
                                for term in ("send", "purchase", "buy now",
                                             "delete", "post", "submit",
                                             "unsubscribe")))
                )
                elements.append(ObservedElement(
                    f"{tab_id}:{generation}:{index}", role[:80], name.strip(),
                    True, enabled, href, input_type, external))
            except Exception:
                # A page can replace controls during observation. Ignore only
                # the stale node and return the rest of the current snapshot.
                continue
        return PageObservation(tab_id, page.url, title, visible_text,
                               tuple(elements), generation)
