"""Observe-plan-validate-execute loop for generic browser tasks."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any

from app.browser.actions import BrowserAction
from app.browser.client import BrowserClient
from app.browser.validator import BrowserTargetStaleError

if TYPE_CHECKING:
    from app.browser.observer import PageObservation


Planner = Callable[[str, "PageObservation"], Awaitable[Mapping[str, Any]]]
Confirmation = Callable[[str], Awaitable[bool]]


class BrowserAgent:
    def __init__(self, browser: BrowserClient, planner: Planner, *,
                 confirm: Confirmation | None = None, max_actions: int = 24) -> None:
        if type(max_actions) is not int or not 1 <= max_actions <= 24:
            raise ValueError("Browser agent action limit must be between 1 and 24")
        self.browser, self.planner = browser, planner
        self.confirm = confirm
        self.max_actions = max_actions

    async def execute(self, goal: str) -> dict[str, Any]:
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 4_000:
            raise ValueError("Browser task must contain 1-4000 characters")
        task = goal.strip()
        if self.browser.session.active_tab_id is None:
            await self.browser.new_tab()
        history = []
        for _ in range(self.max_actions):
            observation = await self.browser.observe()
            challenge_text = (observation.title + "\n" + observation.visible_text).casefold()
            intervention_markers = (
                "captcha", "verify you are human", "verify you're human",
                "unusual traffic", "security challenge", "two-factor",
                "two factor", "mfa required", "sign in to continue",
            )
            if any(marker in challenge_text for marker in intervention_markers):
                return {
                    "status": "user_intervention_required",
                    "result": "The page requires sign-in or human verification. "
                              "Complete it in the browser, then resume the task.",
                    "actions": history,
                }
            decision = await self.planner(task, observation)
            if not isinstance(decision, Mapping):
                raise ValueError("Browser planner must return a structured object")
            if "crawl" in decision:
                if set(decision) != {"crawl"} or not isinstance(decision["crawl"], Mapping):
                    raise ValueError("Browser crawl plan contains unsupported fields")
                crawl_plan = dict(decision["crawl"])
                allowed_crawl_fields = {"start_url", "max_pages", "max_depth"}
                if (set(crawl_plan) - allowed_crawl_fields
                        or not isinstance(crawl_plan.get("start_url"), str)):
                    raise ValueError("Browser crawl plan requires an HTTPS start_url")
                from app.skills.generic_web import GenericWebSkill

                result = await GenericWebSkill(self.browser).crawl(
                    crawl_plan["start_url"],
                    max_pages=crawl_plan.get("max_pages", 10),
                    max_depth=crawl_plan.get("max_depth", 2),
                )
                return {
                    "status": "truncated" if result.truncated else "completed",
                    "result": f"Crawled {len(result.pages)} pages from {result.start_url}",
                    "pages": [
                        {"url": page.url, "title": page.title, "text": page.text,
                         "depth": page.depth}
                        for page in result.pages
                    ],
                    "skipped_links": result.skipped_links,
                    "truncated": result.truncated,
                }
            if decision.get("done") is True:
                if set(decision) - {"done", "result"}:
                    raise ValueError("Browser completion response contains unsupported fields")
                if "result" in decision and not isinstance(decision["result"], str):
                    raise ValueError("Browser completion result must be text")
                return {"status": "completed", "result": decision.get("result", ""),
                        "actions": history, "observation": observation}
            if set(decision) != {"action"}:
                raise ValueError("Browser planner response must contain one action or completion")
            raw_action = decision.get("action")
            action = (raw_action if isinstance(raw_action, BrowserAction)
                      else BrowserAction.from_mapping(raw_action))
            try:
                result = await self.browser.execute(action)
            except BrowserTargetStaleError as error:
                history.append({"action": action.action,
                                "recovery": "reobserve",
                                "reason": str(error)})
                continue
            except PermissionError as error:
                if ("explicit user confirmation" not in str(error)
                        or self.confirm is None
                        or not await self.confirm(str(error))):
                    return {"status": "user_intervention_required",
                            "result": str(error), "actions": history}
                result = await self.browser.execute(action, confirm_external=True)
            history.append({"action": action.action, "result": result})
        return {"status": "action_limit_reached",
                "result": "Browser task stopped at its bounded action limit",
                "actions": history}
