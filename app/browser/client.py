"""Allowlisted generic browser client layered over an owned Playwright context."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4
from typing import Any

from app.browser.actions import BrowserAction, BrowserActionType
from app.browser.observer import BrowserObserver, ObservedElement, PageObservation
from app.browser.permissions import BrowserPermission, PermissionManager
from app.browser.policies import BrowserPolicy, DEFAULT_BROWSER_POLICY
from app.browser.sessions import BrowserSessionStore
from app.browser.validator import BrowserActionValidator, BrowserTargetStaleError


@dataclass(slots=True)
class BrowserTab:
    id: str
    page: Any = field(repr=False)
    url: str = "about:blank"
    title: str = ""
    state: str = "active"
    site: str = ""


@dataclass(slots=True)
class BrowserSession:
    session_id: str = field(default_factory=lambda: uuid4().hex)
    tabs: dict[str, BrowserTab] = field(default_factory=dict)
    active_tab_id: str | None = None


class BrowserClient:
    """Controls only tabs it created; provider tabs and raw script are excluded."""

    def __init__(self, context, *, permissions: PermissionManager | None = None,
                 policy: BrowserPolicy = DEFAULT_BROWSER_POLICY,
                 observer: BrowserObserver | None = None,
                 store: BrowserSessionStore | None = None,
                 browser_id: str = "",
                 session_id: str | None = None) -> None:
        self.context = context
        self.permissions = permissions or PermissionManager({
            BrowserPermission.READ, BrowserPermission.NAVIGATE,
            BrowserPermission.WRITE,
        })
        self.policy = policy
        self.observer = observer or BrowserObserver()
        self.store = store
        self.browser_id = browser_id
        self.session = BrowserSession(session_id=session_id or uuid4().hex)
        self.validator = BrowserActionValidator(self.permissions, policy)
        self._observations: dict[str, PageObservation] = {}
        self._targets: dict[str, dict[str, tuple[Any, ObservedElement]]] = {}
        self._generation: dict[str, int] = {}

    async def new_tab(self) -> BrowserTab:
        self.permissions.require("new_tab")
        page = await self.context.new_page()
        tab = BrowserTab(uuid4().hex, page)
        self.session.tabs[tab.id] = tab
        self.session.active_tab_id = tab.id
        self._generation[tab.id] = 0
        await self._persist(tab, "new_tab")
        return tab

    async def restore_session(self) -> list[BrowserTab]:
        if self.store is None:
            return []
        restored = []
        for record in self.store.tabs(self.session.session_id):
            if record["browser_id"] != self.browser_id:
                continue
            page = await self.context.new_page()
            tab = BrowserTab(record["tab_id"], page, state="restoring")
            self.session.tabs[tab.id] = tab
            self._generation[tab.id] = 0
            await tab.page.goto(
                self.policy.validate_url(record["url"]),
                wait_until="domcontentloaded")
            tab.url, tab.title = tab.page.url, await tab.page.title()
            tab.state = "restored"
            self.session.active_tab_id = tab.id
            restored.append(tab)
        return restored

    async def active_tab(self) -> BrowserTab:
        tab_id = self.session.active_tab_id
        tab = self.session.tabs.get(tab_id or "")
        if tab is None:
            return await self.new_tab()
        if tab.page.is_closed():
            tab.state = "closed"
            self._invalidate(tab.id)
            raise RuntimeError("The active browser tab was closed")
        return tab

    async def observe(self, tab_id: str | None = None) -> PageObservation:
        tab = self._tab(tab_id)
        if tab.page.is_closed():
            tab.state = "closed"
            self._invalidate(tab.id)
            raise RuntimeError("Cannot observe a closed browser tab")
        generation = self._generation.get(tab.id, 0) + 1
        observation = await self.observer.observe(tab.id, tab.page, generation)
        if observation.url != "about:blank":
            self.policy.validate_url(observation.url)
        self._generation[tab.id] = generation
        self._observations[tab.id] = observation
        self._targets[tab.id] = {
            item.target_id: (
                tab.page.locator(BrowserObserver.SELECTOR).nth(
                    int(item.target_id.rsplit(":", 1)[1])),
                item,
            )
            for item in observation.elements
        }
        tab.url, tab.title = observation.url, observation.title
        tab.site = observation.url.split("/", 3)[2] if "://" in observation.url else ""
        await self._persist(tab, "observe")
        return observation

    async def execute(self, action: BrowserAction, *,
                      confirm_external: bool = False) -> Any:
        if not isinstance(action, BrowserAction):
            raise TypeError("BrowserClient accepts only validated BrowserAction objects")
        kind = BrowserActionType(action.action).value
        if kind in {"new_tab", "navigate"} and self.session.active_tab_id is None:
            tab = await self.new_tab()
        else:
            tab = self._tab(action.tab_id)
        self.session.active_tab_id = tab.id
        observation = self._observations.get(tab.id)
        self.validator.validate(action, observation, confirm_external=confirm_external)
        if kind == "navigate":
            await tab.page.goto(action.url, wait_until="domcontentloaded")
            self._invalidate(tab.id)
        elif kind == "back":
            await tab.page.go_back(wait_until="domcontentloaded")
            self._invalidate(tab.id)
        elif kind == "forward":
            await tab.page.go_forward(wait_until="domcontentloaded")
            self._invalidate(tab.id)
        elif kind == "refresh":
            await tab.page.reload(wait_until="domcontentloaded")
            self._invalidate(tab.id)
        elif kind == "new_tab":
            tab = await self.new_tab()
        elif kind == "switch_tab":
            tab = self._tab(action.tab_id)
            await tab.page.bring_to_front()
            self.session.active_tab_id = tab.id
        elif kind == "close_tab":
            tab = self._tab(action.tab_id)
            await tab.page.close()
            tab.state = "closed"
            self.session.tabs.pop(tab.id)
            self._invalidate(tab.id)
            if self.store:
                self.store.remove_tab(self.session.session_id, tab.id)
            self.session.active_tab_id = next(iter(self.session.tabs), None)
            return {"closed_tab": tab.id}
        elif kind in {"click", "double_click", "type", "clear", "press",
                      "select", "hover", "read_text", "read_attribute", "play", "pause"}:
            locator = await self._resolve_target(tab.id, action.target)
            if kind == "click":
                await locator.click()
                self._invalidate(tab.id)
            elif kind == "double_click":
                await locator.dblclick()
                self._invalidate(tab.id)
            elif kind == "type":
                await locator.fill(action.text)
            elif kind == "clear":
                await locator.fill("")
            elif kind == "press":
                await locator.press(action.key)
                self._invalidate(tab.id)
            elif kind == "select":
                await locator.select_option(action.value)
            elif kind == "hover":
                await locator.hover()
            elif kind == "read_text":
                return await locator.inner_text()
            elif kind == "read_attribute":
                return await locator.get_attribute(action.attribute)
            elif kind == "play":
                playing = await locator.evaluate(
                    "(element) => Promise.resolve(element.play()).then(() => "
                    "!element.paused && !element.ended).catch(() => false)")
                if playing is not True:
                    raise RuntimeError("Browser media playback could not be confirmed")
                return {"playing": True}
            elif kind == "pause":
                paused = await locator.evaluate(
                    "(element) => { element.pause(); return element.paused; }")
                if paused is not True:
                    raise RuntimeError("Browser media pause could not be confirmed")
                return {"paused": True}
        elif kind == "scroll":
            delta = action.amount if action.direction == "down" else -action.amount
            await tab.page.mouse.wheel(0, delta)
            self._invalidate(tab.id)
        elif kind == "wait":
            await tab.page.wait_for_load_state(
                "domcontentloaded", timeout=action.timeout_ms or 10_000)
        else:
            raise ValueError(f"Browser action is not implemented: {kind}")
        if tab.id in self.session.tabs:
            tab.url = tab.page.url
            if kind != "new_tab" and tab.url != "about:blank":
                self.policy.validate_url(tab.url)
            await self._persist(tab, kind)
        return {"tab_id": tab.id, "url": tab.page.url}

    def _tab(self, tab_id: str | None = None) -> BrowserTab:
        selected = tab_id or self.session.active_tab_id
        tab = self.session.tabs.get(selected or "")
        if tab is None:
            raise ValueError("Browser tab is not owned by this client")
        if tab.page.is_closed():
            tab.state = "closed"
            self._invalidate(tab.id)
            raise RuntimeError("Browser tab is closed")
        return tab

    async def _resolve_target(self, tab_id: str, target_id: str):
        pair = self._targets.get(tab_id, {}).get(target_id)
        if pair is None:
            raise BrowserTargetStaleError(
                "Browser target is missing or stale; observe the page again")
        locator, observed = pair
        try:
            if not await locator.is_visible():
                raise BrowserTargetStaleError("Observed browser target is no longer visible")
            tag = await locator.evaluate("(node) => node.tagName.toLowerCase()")
            role = (await locator.get_attribute("role")) or tag
            name = ((await locator.get_attribute("aria-label"))
                    or (await locator.get_attribute("placeholder"))
                    or (await locator.inner_text())
                    or (await locator.get_attribute("title"))
                    or "").strip()[:300]
            href = await locator.get_attribute("href") if tag == "a" else None
            input_type = await locator.get_attribute("type")
            enabled = await locator.is_enabled()
        except BrowserTargetStaleError:
            raise
        except Exception as error:
            raise BrowserTargetStaleError(
                "Observed browser target disappeared; observe the page again") from error
        if (role != observed.role or name != observed.name or href != observed.href
                or input_type != observed.input_type or enabled != observed.enabled):
            raise BrowserTargetStaleError(
                "Browser target changed after observation; observe the page again")
        return locator

    def _invalidate(self, tab_id: str) -> None:
        self._observations.pop(tab_id, None)
        self._targets.pop(tab_id, None)

    async def _persist(self, tab: BrowserTab, last_action: str) -> None:
        if self.store is None or tab.page.is_closed():
            return
        tab.url = tab.page.url
        if not tab.url.startswith("https://"):
            return
        tab.title = (await tab.page.title())[:500]
        self.store.save_tab(self.session.session_id, tab.id, tab.url, tab.title,
                            tab.state, last_action, browser_id=self.browser_id)

    async def close(self) -> None:
        for tab in list(self.session.tabs.values()):
            if not tab.page.is_closed():
                await tab.page.close()
            tab.state = "closed"
            if self.store:
                self.store.remove_tab(self.session.session_id, tab.id)
        self.session.tabs.clear()
        self.session.active_tab_id = None
