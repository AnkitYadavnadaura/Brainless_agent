"""Gmail read/compose workflow; sending is always explicitly confirmed."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.browser.actions import BrowserAction
from app.browser.client import BrowserClient
from app.browser.observer import PageObservation


class GmailSkill:
    URL = "https://mail.google.com/"

    def __init__(self, browser: BrowserClient,
                 confirm_send: Callable[[str], Awaitable[bool]] | None = None) -> None:
        self.browser, self.confirm_send = browser, confirm_send

    async def open(self) -> PageObservation:
        await self.browser.execute(BrowserAction("navigate", url=self.URL))
        observation = await self.browser.observe()
        title_and_text = (observation.title + "\n" + observation.visible_text).casefold()
        if any(marker in title_and_text for marker in (
                "sign in", "choose an account", "verify it's you", "captcha")):
            raise RuntimeError(
                "Gmail requires sign-in or human verification; complete it in the browser and retry")
        return observation

    async def read_visible_page(self) -> dict[str, str]:
        observation = await self.browser.observe()
        title_and_text = (observation.title + "\n" + observation.visible_text).casefold()
        if any(marker in title_and_text for marker in (
                "sign in", "choose an account", "verify it's you", "captcha")):
            raise RuntimeError(
                "Gmail requires sign-in or human verification; complete it in the browser and retry")
        return {"title": observation.title, "text": observation.visible_text,
                "url": observation.url}

    async def compose_and_send(self, recipient: str, subject: str, body: str) -> PageObservation:
        if not recipient.strip() or not subject.strip() or not body.strip():
            raise ValueError("Gmail recipient, subject, and body are required")
        observation = await self.open()
        compose = next((item for item in observation.elements
                        if item.name.casefold() == "compose"), None)
        if compose is None:
            raise RuntimeError("Gmail compose control was not found")
        await self.browser.execute(BrowserAction("click", target=compose.target_id))
        observation = await self.browser.observe()
        fields = {
            "recipient": ("recipients", "to"),
            "subject": ("subject",),
            "body": ("message body", "message"),
        }
        for value, names in (
                (recipient, fields["recipient"]),
                (subject, fields["subject"]),
                (body, fields["body"])):
            element = next((item for item in observation.elements
                            if item.role in {"input", "textarea", "textbox"}
                            and any(name in item.name.casefold() for name in names)), None)
            if element is None:
                raise RuntimeError("A required Gmail draft field was not found")
            await self.browser.execute(BrowserAction(
                "type", target=element.target_id, text=value))
            observation = await self.browser.observe()
        send = next((item for item in observation.elements
                     if "send" in item.name.casefold() and item.external), None)
        if send is None:
            raise RuntimeError("Gmail send control was not found")
        if self.confirm_send is None or not await self.confirm_send(
                f"Send email to {recipient} with subject {subject}?"):
            return observation
        await self.browser.execute(
            BrowserAction("click", target=send.target_id), confirm_external=True)
        return await self.browser.observe()
