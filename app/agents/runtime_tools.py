"""Production tool adapters registered behind AgentManager permission checks."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import re
from pathlib import Path
from typing import Any

from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.browser.browser_manager import BrowserManager
from app.computer.keyboard import Keyboard
from app.computer.mouse import Mouse
from app.computer.screenshot import ScreenshotRecorder
from app.safety.permissions import Permission
from app.computer.desktop import register_desktop_tools
from app.autonomy.vscode_worker import VscodeWorker
from app.browser.url_validation import normalize_web_url
from urllib.parse import parse_qs, quote_plus, urlsplit


def _normalize_url_argument(arguments: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(arguments)
    normalized["url"] = normalize_web_url(normalized["url"])
    return normalized


def register_capability_skilling_tool(registry: ToolRegistry, coordinator) -> None:
    async def skill_develop(arguments: dict[str, Any]) -> dict[str, Any]:
        result = await coordinator.develop(arguments["plan"])
        return result.snapshot()

    registry.register(ToolSpec(
        "skill.develop", "Develop missing capability",
        "Execute a browser-authorized structured self-skilling plan through VS Code workers",
        frozenset({Permission.PROCESS_EXECUTE.value, Permission.FILESYSTEM_READ.value,
                   Permission.FILESYSTEM_WRITE.value}),
        RiskLevel.HIGH, skill_develop, ("plan",), "skill result",
        category="self-improvement", destructive=True,
    ))


def register_runtime_tools(registry: ToolRegistry, browser: BrowserManager, repository_root: Path,
                           keyboard: Keyboard | None = None, mouse: Mouse | None = None,
                           screenshots: ScreenshotRecorder | None = None,
                           capability_skilling=None, gmail_profiles=None, external_browser=None) -> None:
    """Register real adapters; callers must invoke them through AgentManager."""
    async def browser_open(arguments: dict[str, Any]) -> str:
        if external_browser is not None and external_browser.active:
            return await external_browser.open()
        try:
            page = await browser.open_user_page()
            return page.url
        except Exception:
            if external_browser is not None:
                return await external_browser.open()
            raise

    async def browser_observe(arguments: dict[str, Any]) -> dict[str, Any]:
        if external_browser is not None and external_browser.active:
            return await external_browser.observe()
        try:
            from app.browser.voice_observation import BrowserVoiceObserver

            return await BrowserVoiceObserver(browser).capture()
        except Exception:
            if external_browser is not None:
                return await external_browser.observe()
            raise

    async def browser_title(arguments: dict[str, Any]) -> str:
        if external_browser is not None and external_browser.active:
            return str((await external_browser.observe()).get("title", ""))
        try:
            page = await browser.page_for(str(arguments["url"]))
            return await page.title()
        except Exception:
            if external_browser is not None:
                return str((await external_browser.observe()).get("title", ""))
            raise

    async def browser_navigate(arguments: dict[str, Any]) -> str:
        if external_browser is not None and external_browser.active:
            return await external_browser.navigate(str(arguments["url"]))
        try:
            page = await browser.page_for(str(arguments["url"]), exact=True)
            return page.url
        except Exception:
            if external_browser is not None:
                return await external_browser.navigate(str(arguments["url"]))
            raise

    async def browser_type(arguments: dict[str, Any]) -> str:
        if external_browser is not None and external_browser.active:
            await external_browser.interact("type", target=str(arguments["selector"]), text=str(arguments["text"]))
            return "typed into the observed external browser control"
        page = await browser.page_for(str(arguments["url"]))
        await page.locator(str(arguments["selector"])).fill(str(arguments["text"]))
        return "typed"

    async def _resolve_locator(page, target: str):
        try:
            loc = page.locator(target).first
            if await loc.count() > 0 and await loc.is_visible():
                return loc
        except Exception:
            pass
        try:
            loc = page.get_by_role("button", name=target).first
            if await loc.count() > 0 and await loc.is_visible():
                return loc
        except Exception:
            pass
        try:
            loc = page.get_by_role("link", name=target).first
            if await loc.count() > 0 and await loc.is_visible():
                return loc
        except Exception:
            pass
        try:
            loc = page.get_by_text(target, exact=False).first
            if await loc.count() > 0 and await loc.is_visible():
                return loc
        except Exception:
            pass
        return page.locator(target).first

    async def browser_click(arguments: dict[str, Any]) -> str:
        target = str(arguments.get("selector") or arguments.get("target") or "").strip()
        if not target:
            raise ValueError("Target selector or runtime ID is required")
        if external_browser is not None and external_browser.active:
            if not (re.fullmatch(r"[-0-9.]{1,180}", target) or target.startswith("ocr.")):
                obs = await external_browser.observe()
                elements = obs.get("elements", [])
                matched = None
                for el in elements:
                    label = el.get("label", "").casefold()
                    if target.casefold() in label or label in target.casefold():
                        matched = el.get("runtime_id")
                        break
                if matched:
                    target = matched
                else:
                    raise ValueError(f"Could not find an observed external browser element matching '{target}'")
            await external_browser.interact("click", target=target)
            return f"Clicked observed external browser control: {target}"
        url = str(arguments.get("url", "")).strip() if arguments.get("url") else None
        page = await browser.page_for(url) if url else browser.current_user_page()
        if page is None:
            page = await browser.open_user_page()
        locator = await _resolve_locator(page, target)
        await locator.wait_for(state="visible", timeout=15_000)
        await locator.click()
        return f"Clicked control: {target}"

    async def browser_crawl(arguments: dict[str, Any]) -> dict[str, Any]:
        url = str(arguments.get("url", "")).strip()
        if not url:
            raise ValueError("A starting URL is required for crawling")
        max_pages = int(arguments.get("max_pages", 5))
        max_depth = int(arguments.get("max_depth", 2))
        if max_pages < 1 or max_pages > 50:
            raise ValueError("max_pages must be between 1 and 50")
        if max_depth < 0 or max_depth > 5:
            raise ValueError("max_depth must be between 0 and 5")
        if browser._context is None:
            await browser.start()
        client = browser.browser_client()
        from app.skills.generic_web import GenericWebSkill

        skill = GenericWebSkill(client)
        result = await skill.crawl(url, max_pages=max_pages, max_depth=max_depth)
        return {
            "start_url": result.start_url,
            "pages_crawled": len(result.pages),
            "pages": [
                {"url": page.url, "title": page.title, "depth": page.depth}
                for page in result.pages
            ],
            "skipped_links": result.skipped_links,
            "truncated": result.truncated,
        }

    async def gmail_open(arguments: dict[str, Any]) -> str:
        if gmail_profiles is None:
            raise RuntimeError("Installed Gmail profiles are not configured")
        if external_browser is gmail_profiles:
            await external_browser.select_profile(arguments["profile_id"], arguments["profile_label"])
        return await gmail_profiles.open_gmail(arguments["profile_id"], arguments["profile_label"])

    async def gmail_send_email(arguments: dict[str, Any]) -> str:
        recipient = str(arguments["to"]).strip()
        subject = str(arguments["subject"]).strip()
        body = str(arguments["body"]).strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
            raise ValueError("A single valid email recipient is required")
        if not subject or not body or len(subject) > 998 or len(body) > 20_000:
            raise ValueError("Email subject and body are required and must be within supported limits")

        if gmail_profiles is not None:
            profile_id = str(arguments["profile_id"]).strip()
            profile_label = str(arguments["profile_label"]).strip()
            if not profile_id:
                raise ValueError("A discovered browser profile must be selected before sending email")
            if not profile_label:
                raise ValueError("The selected browser profile must be identified for approval")
            return await gmail_profiles.send(
                profile_id, profile_label, recipient, subject, body)

        page = await browser.page_for("https://mail.google.com/")
        if (urlsplit(page.url).hostname or "").casefold() not in {
                "mail.google.com", "gmail.com"}:
            raise RuntimeError("Gmail did not open in the managed browser")
        compose = page.locator('div[gh="cm"], button[aria-label="Compose"]').first
        await compose.wait_for(state="visible", timeout=15_000)
        await compose.click()

        to_field = page.locator('input[name="to"], textarea[name="to"]').first
        await to_field.wait_for(state="visible", timeout=15_000)
        await to_field.fill(recipient)
        await to_field.press("Enter")
        subject_field = page.locator('input[name="subjectbox"]')
        await subject_field.wait_for(state="visible", timeout=15_000)
        await subject_field.fill(subject)
        message_body = page.locator(
            'div[aria-label="Message Body"][contenteditable="true"], '
            'div[role="textbox"][aria-label="Message Body"]'
        ).first
        await message_body.wait_for(state="visible", timeout=15_000)
        await message_body.fill(body)
        sent_to = page.locator(f'div[email="{recipient}"]')
        if not await sent_to.count():
            raise RuntimeError("Gmail did not confirm the requested recipient in the draft")
        send_button = page.locator(
            'div[role="button"][aria-label^="Send"], button[aria-label^="Send"]'
        ).first
        await send_button.wait_for(state="visible", timeout=15_000)
        await send_button.click()
        confirmation = page.get_by_text("Message sent", exact=False)
        await confirmation.wait_for(state="visible", timeout=15_000)
        return f"Email sent to {recipient}"

    def type_keys(arguments: dict[str, Any]) -> str:
        (keyboard or Keyboard()).type_text(str(arguments["text"]))
        return "typed"

    def click_mouse(arguments: dict[str, Any]) -> str:
        (mouse or Mouse()).click(int(arguments["x"]), int(arguments["y"]))
        return "clicked"

    def write_file(arguments: dict[str, Any]) -> str:
        path = (repository_root / str(arguments["path"])).resolve()
        if repository_root.resolve() not in path.parents:
            raise ValueError("Filesystem writes must remain inside the repository")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(arguments["content"]), encoding="utf-8")
        return str(path)

    async def execute_process(arguments: dict[str, Any]) -> dict[str, object]:
        command = arguments["command"]
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            raise ValueError("command must be a non-empty list of strings")
        process = await asyncio.create_subprocess_exec(*command, cwd=str(repository_root),
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        return {"returncode": process.returncode, "stdout": stdout.decode(), "stderr": stderr.decode()}

    async def screenshot(arguments: dict[str, Any]) -> str:
        if screenshots is None:
            raise RuntimeError("Screenshot recorder is not configured")
        page = await browser.page_for(str(arguments["url"]))
        return str(await screenshots.capture(page, str(arguments["label"])))

    async def youtube_search(arguments: dict[str, Any]) -> str:
        """Show YouTube results while leaving video selection to the user."""
        query = arguments["query"]
        if not isinstance(query, str) or not query.strip():
            raise ValueError("YouTube search text is required")
        if external_browser is not None and external_browser.active:
            return await external_browser.search_youtube(query)
        page = await browser.page_for(
            f"https://www.youtube.com/results?search_query={quote_plus(query.strip())}", exact=True)
        return page.url

    async def youtube_play(arguments: dict[str, Any]) -> str:
        """Select one YouTube video and confirm its player starts."""
        if external_browser is not None and external_browser.active:
            return await external_browser.play_youtube(arguments["query"])
        query = str(arguments["query"]).strip()
        if not query:
            raise ValueError("YouTube search text, video URL, or 'recommendation' is required")
        parsed_query = urlsplit(query)
        allowed_hosts = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
        recommendation = query.casefold() in {
            "recommendation", "any video", "any", "video", "a video", "play video",
            "play a video", "current", "continue", "resume",
        }
        selected_result = None
        if parsed_query.scheme and (
                parsed_query.scheme != "https"
                or (parsed_query.hostname or "").casefold() not in allowed_hosts):
            raise ValueError("YouTube URL must use HTTPS and a supported YouTube host")

        if recommendation:
            page = browser.current_user_page()
            if page is None or (urlsplit(page.url).hostname or "").casefold() not in allowed_hosts:
                page = await browser.page_for("https://www.youtube.com/", exact=True)
            else:
                await page.bring_to_front()
            # An existing player is the user's current video. Resume it rather
            # than opening recommendations or replacing the current selection.
            if urlsplit(page.url).path.rstrip("/") not in {"/watch", "/live"}:
                selected_result = await _first_youtube_result(page, (
                    "ytd-rich-item-renderer a#thumbnail[href*='/watch']",
                    "ytd-video-renderer a#video-title[href*='/watch']",
                    "a#video-title-link[href*='/watch']",
                ), visible_only=True)
        elif parsed_query.scheme and parsed_query.path == "/results":
            page = await browser.page_for(query, exact=True)
            selected_result = await _first_youtube_result(page, (
                "ytd-video-renderer a#video-title[href*='/watch']",
                "ytd-video-renderer a#thumbnail[href*='/watch']",
            ))
        elif parsed_query.scheme:
            if not (parsed_query.path == "/watch" or
                    (parsed_query.hostname or "").casefold() == "youtu.be"):
                raise ValueError("Provide a YouTube video URL or search query")
            page = await browser.page_for(query, exact=True)
        else:
            page = await browser.page_for(
                f"https://www.youtube.com/results?search_query={quote_plus(query)}", exact=True)
            selected_result = await _first_youtube_result(page, (
                "ytd-video-renderer a#video-title[href*='/watch']",
                "ytd-video-renderer a#thumbnail[href*='/watch']",
            ))

        if selected_result is not None:
            result_link, target_url = selected_result
            await result_link.click()
            await page.wait_for_url("**/watch**", timeout=15_000)
            target_parts = urlsplit(target_url)
            target_id = (parse_qs(target_parts.query).get("v") or
                         [target_parts.path.lstrip("/")])[0]
            current_id = (parse_qs(urlsplit(page.url).query).get("v") or
                          [urlsplit(page.url).path.lstrip("/")])[0]
            if target_id and current_id != target_id:
                raise RuntimeError("YouTube opened a different video than the selected result")

        await page.locator("video").first.wait_for(state="attached", timeout=15_000)
        video = page.locator("video").first
        playing = await video.evaluate(
            "(element) => !element.paused && !element.ended && element.readyState >= 2")
        if not playing:
            play_button = page.locator(
                "button.ytp-large-play-button, button.ytp-play-button[aria-label*='Play']")
            if not await play_button.count():
                raise RuntimeError("The selected YouTube video has no available play control")
            await play_button.first.click()
            await page.wait_for_function(
                "() => { const video = document.querySelector('video'); "
                "return video && !video.paused && !video.ended && video.readyState >= 2; }",
                timeout=15_000)
        title = (await page.title()).strip()
        if not title:
            raise RuntimeError("YouTube playback started but the video title could not be verified")
        return f"Playing YouTube video: {title}"

    async def youtube_control(arguments: dict[str, Any]) -> str:
        """Apply a bounded transport control to the currently open YouTube player."""
        action = str(arguments["action"]).strip().casefold()
        seconds = arguments["seconds"]
        if action not in {"play", "pause", "skip_ad", "forward", "backward", "next_video"}:
            raise ValueError("Unsupported YouTube player action")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
            raise ValueError("YouTube control seconds must be numeric")
        if action in {"forward", "backward"} and not 1 <= seconds <= 120:
            raise ValueError("YouTube seek must be between 1 and 120 seconds")
        if action not in {"forward", "backward"} and seconds != 0:
            raise ValueError("YouTube control seconds must be zero for this action")
        if external_browser is not None and external_browser.active:
            return await external_browser.control_youtube(action, seconds)

        page = browser.current_user_page()
        if page is None:
            raise RuntimeError("No active YouTube video is open in the browser")
        current = urlsplit(page.url)
        if ((current.hostname or "").casefold() not in {
                "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
                or current.path.rstrip("/") not in {"/watch", "/live"}):
            raise RuntimeError("No active YouTube video is open in the browser")
        await page.bring_to_front()

        if action == "skip_ad":
            skip_button = page.locator(
                "button.ytp-ad-skip-button, button.ytp-skip-ad-button, "
                ".ytp-ad-skip-button-modern"
            )
            if not await skip_button.count() or not await skip_button.first.is_visible():
                raise RuntimeError("There is no skippable YouTube ad right now")
            await skip_button.first.click()
            return "Skipped the YouTube ad"

        if action == "next_video":
            next_button = page.locator("button.ytp-next-button")
            if not await next_button.count() or not await next_button.first.is_visible():
                raise RuntimeError("YouTube has no available next-video control")
            previous_url = page.url
            await next_button.first.click()
            await page.wait_for_function(
                "(previous) => location.href !== previous && location.pathname === '/watch'",
                previous_url,
                timeout=15_000,
            )
            return f"Started the next YouTube video: {(await page.title()).strip()}"

        video = page.locator("video").first
        await video.wait_for(state="attached", timeout=15_000)
        if action in {"play", "pause"}:
            if action == "play":
                await video.evaluate("(element) => element.play()")
            else:
                await video.evaluate("(element) => element.pause()")
            expected = "playing" if action == "play" else "paused"
            paused = action == "pause"
            await page.wait_for_function(
                "() => { const video = document.querySelector('video'); "
                "return video && video.paused === " + str(paused).lower() + "; }",
                timeout=10_000,
            )
            return f"YouTube video {expected}"

        delta = float(seconds) * (1 if action == "forward" else -1)
        position = await video.evaluate(
            "(element, delta) => {"
            " const target = Math.max(0, Math.min(element.duration || Infinity, "
            "element.currentTime + delta));"
            " element.currentTime = target;"
            " return element.currentTime;"
            "}", delta,
        )
        return f"Moved YouTube playback to {int(position)} seconds"

    async def _first_youtube_result(page, selectors: tuple[str, ...], *, visible_only: bool = False):
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        try:
            await page.locator(", ".join(selectors)).first.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError as error:
            raise RuntimeError("No matching YouTube video was found; playback was not started") from error
        for selector in selectors:
            links = page.locator(selector)
            for index in range(min(await links.count(), 30)):
                link = links.nth(index)
                if not await link.is_visible():
                    continue
                if visible_only and not await link.evaluate(
                        "(element) => { const r = element.getBoundingClientRect(); "
                        "return r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 "
                        "&& r.top < innerHeight && r.left < innerWidth; }"):
                    continue
                href = await link.get_attribute("href")
                if href and "/watch" in href:
                    target_url = href if href.startswith("https://") else f"https://www.youtube.com{href}"
                    target = urlsplit(target_url)
                    if ((target.hostname or "").casefold() in {
                            "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
                            and target.path == "/watch" and parse_qs(target.query).get("v")):
                        return link, target_url
        raise RuntimeError("No matching YouTube video was found; playback was not started")

    vscode_worker = VscodeWorker(repository_root)

    def vscode_discover(arguments: dict[str, Any]) -> dict[str, str | None]:
        return asdict(vscode_worker.discover())

    async def vscode_open(arguments: dict[str, Any]) -> dict[str, str]:
        return await vscode_worker.open_workspace()

    async def vscode_open_file(arguments: dict[str, Any]) -> dict[str, str]:
        return await vscode_worker.open_file(str(arguments["path"]))

    async def vscode_list_extensions(arguments: dict[str, Any]) -> list[str]:
        return await vscode_worker.list_extensions()

    async def vscode_install_extension(arguments: dict[str, Any]) -> dict[str, Any]:
        return await vscode_worker.install_extension(str(arguments["extension_id"]))

    async def vscode_uninstall_extension(arguments: dict[str, Any]) -> dict[str, Any]:
        return await vscode_worker.uninstall_extension(str(arguments["extension_id"]))

    async def vscode_validate(arguments: dict[str, Any]) -> dict[str, Any]:
        return await vscode_worker.validate(str(arguments.get("command", "python -m pytest -q")))

    async def vscode_delegate(arguments: dict[str, Any]) -> dict[str, Any]:
        return await vscode_worker.delegate(
            str(arguments["worker"]), str(arguments["prompt"]))

    async def skill_develop(arguments: dict[str, Any]) -> dict[str, Any]:
        if capability_skilling is None:
            raise RuntimeError("Capability self-skilling is not configured")
        result = await capability_skilling.develop(arguments["plan"])
        return result.snapshot()

    def vscode_coordinate(arguments: dict[str, Any]) -> str:
        packet = vscode_worker.write_coordination_packet(
            str(arguments["task_id"]), str(arguments["objective"]),
            arguments["plan"] if isinstance(arguments["plan"], dict) else {},
        )
        return str(packet)

    if external_browser is not None:
        async def select_profile(arguments):
            return await external_browser.select_profile(arguments["profile_id"], arguments["profile_label"])

        async def external_action(arguments):
            return await external_browser.interact(
                arguments["action"], target=arguments["target"], text=arguments["text"],
                key=arguments["key"], direction=arguments["direction"],
                amount=arguments["amount"] if arguments["amount"] is not None else 3)

        registry.register(ToolSpec("browser.select_profile", "Select browser profile",
            "Select the exact user-chosen installed profile, or managed / Managed browser. "
            "Requires a profile ID and its exact label from profile discovery.",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.LOW,
            select_profile, ("profile_id", "profile_label"), "profile selection", category="browser"))
        registry.register(ToolSpec("browser.external_action", "Interact with external website",
            "Act on the selected external browser using observed elements[].runtime_id as target. "
            "Actions: click, type, press, scroll, back, forward, refresh. Set unused fields to null; "
            "scroll direction up/down and amount 1-10. Never supply CSS, JavaScript, or invented coordinates.",
            frozenset({Permission.BROWSER_READ.value, Permission.BROWSER_CLICK.value,
                       Permission.BROWSER_TYPE.value}), RiskLevel.HIGH, external_action,
            ("action", "target", "text", "key", "direction", "amount"), "interaction result", category="browser"))

    registry.register(ToolSpec("browser.open", "Open browser",
                               "Open or bring forward the user browser tab without choosing a website",
                               frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
                               browser_open, (), "url", category="browser"))
    registry.register(ToolSpec("browser.observe", "Observe current browser tab",
                               "Read the current user tab, visible controls, video choices, and screenshot OCR without navigating",
                               frozenset({Permission.BROWSER_READ.value, Permission.SCREEN_READ.value}), RiskLevel.LOW,
                               browser_observe, (), "browser observation", category="browser"))
    registry.register(ToolSpec("browser.read_title", "Read browser title", "Open a page and read its title",
                               frozenset({Permission.BROWSER_READ.value, Permission.BROWSER_NAVIGATE.value}
                                         | ({Permission.SCREEN_READ.value} if external_browser else set())), RiskLevel.LOW,
                               browser_title, ("url",), "string",
                               argument_validator=_normalize_url_argument))
    registry.register(ToolSpec("browser.navigate", "Navigate browser", "Open a URL in the persistent browser",
                               frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
                               browser_navigate, ("url",), "url",
                               argument_validator=_normalize_url_argument))
    registry.register(ToolSpec("browser.type", "Type in browser", "Fill a verified DOM field",
                               frozenset({Permission.BROWSER_NAVIGATE.value, Permission.BROWSER_TYPE.value}), RiskLevel.MEDIUM,
                               browser_type, ("url", "selector", "text"), "string",
                               argument_validator=_normalize_url_argument))
    registry.register(ToolSpec("browser.click", "Click browser element",
                               "Click a visible button, link, or interactive element by selector, label, or runtime ID",
                               frozenset({Permission.BROWSER_CLICK.value, Permission.BROWSER_NAVIGATE.value}),
                               RiskLevel.MEDIUM, browser_click, ("selector",), "string", category="browser"))
    registry.register(ToolSpec("browser.crawl", "Crawl website",
                               "Crawl visible links on one HTTPS origin with strict page and depth bounds",
                               frozenset({Permission.BROWSER_NAVIGATE.value, Permission.BROWSER_READ.value}),
                               RiskLevel.MEDIUM, browser_crawl, ("url",), "crawl results",
                               category="browser", argument_validator=_normalize_url_argument))
    gmail_arguments = ("to", "subject", "body", "profile_id", "profile_label") if gmail_profiles is not None else (
        "to", "subject", "body")
    if gmail_profiles is not None:
        registry.register(ToolSpec(
            "gmail.open", "Open Gmail in selected profile",
            "Open Gmail in the exact user-selected installed browser profile before collecting email details. "
            "This opens the website without composing or sending a message.",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM, gmail_open,
            ("profile_id", "profile_label"), "open confirmation", category="email"))
    registry.register(ToolSpec(
        "gmail.send_email", "Send Gmail email",
        "Compose and send one email in the signed-in Gmail account using the explicitly "
        "selected installed browser profile. Requires recipient, subject, body, and profile; "
        "high-risk execution requires runtime approval.",
        frozenset({Permission.BROWSER_NAVIGATE.value, Permission.BROWSER_TYPE.value,
                   Permission.BROWSER_CLICK.value}),
        RiskLevel.HIGH, gmail_send_email, gmail_arguments, "send confirmation",
        category="email", destructive=True,
    ))
    registry.register(ToolSpec("keyboard.write", "Type keys", "Type through the OS keyboard", frozenset({Permission.KEYBOARD_WRITE.value}),
                               RiskLevel.HIGH, type_keys, ("text",), "string"))
    registry.register(ToolSpec("mouse.click", "Click mouse", "Click through the OS mouse", frozenset({Permission.MOUSE_CLICK.value}),
                               RiskLevel.HIGH, click_mouse, ("x", "y"), "string"))
    registry.register(ToolSpec("filesystem.write", "Write repository file", "Write a UTF-8 file inside the repository",
                               frozenset({Permission.FILESYSTEM_WRITE.value}), RiskLevel.HIGH, write_file,
                               ("path", "content"), "path"))
    registry.register(ToolSpec("process.execute", "Execute process", "Run an explicit command in the repository",
                               frozenset({Permission.PROCESS_EXECUTE.value}), RiskLevel.HIGH, execute_process,
                               ("command",), "process result"))
    registry.register(ToolSpec("screen.capture", "Capture browser screenshot", "Capture evidence from a browser page",
                               frozenset({Permission.SCREEN_READ.value, Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
                               screenshot, ("url", "label"), "path"))
    registry.register(ToolSpec("youtube.search", "Search YouTube",
                               "Open YouTube search results without selecting or playing a video",
                               frozenset({Permission.BROWSER_NAVIGATE.value, Permission.BROWSER_READ.value}),
                               RiskLevel.MEDIUM, youtube_search, ("query",), "url", category="media"))
    registry.register(ToolSpec("youtube.play", "Play YouTube video",
                               "Search YouTube and play a video by title/query or an exact YouTube video URL",
                               frozenset({Permission.BROWSER_NAVIGATE.value, Permission.SCREEN_READ.value}
                                         | ({Permission.BROWSER_READ.value} if external_browser else set())), RiskLevel.MEDIUM,
                               youtube_play, ("query",), "string"))
    registry.register(ToolSpec(
        "youtube.control", "Control YouTube playback",
        "Control the currently open YouTube video with action play, pause, skip_ad, "
        "forward, backward, or next_video. Set seconds to a value from 1 to 120 only "
        "for forward/backward; use 0 for all other actions.",
        frozenset({Permission.BROWSER_NAVIGATE.value, Permission.SCREEN_READ.value}
                  | ({Permission.BROWSER_READ.value} if external_browser else set())),
        RiskLevel.MEDIUM, youtube_control, ("action", "seconds"), "player status",
        category="media",
    ))
    registry.register(ToolSpec(
        "vscode.discover", "Discover coding workers",
        "Discover VS Code, Copilot, Codex, Python, and Git executables",
        frozenset({Permission.FILESYSTEM_READ.value}), RiskLevel.LOW,
        vscode_discover, (), "worker availability", category="vscode",
    ))
    registry.register(ToolSpec(
        "vscode.open_workspace", "Open VS Code workspace",
        "Open the repository in VS Code through its CLI",
        frozenset({Permission.WINDOW_CONTROL.value}), RiskLevel.MEDIUM,
        vscode_open, (), "workspace", category="vscode",
    ))
    registry.register(ToolSpec(
        "vscode.open_file", "Open VS Code workspace file",
        "Open a validated file inside the workspace",
        frozenset({Permission.WINDOW_CONTROL.value, Permission.FILESYSTEM_READ.value}),
        RiskLevel.MEDIUM, vscode_open_file, ("path",), "file", category="vscode",
    ))
    registry.register(ToolSpec(
        "vscode.list_extensions", "List VS Code extensions",
        "Read installed VS Code extension identifiers",
        frozenset({Permission.FILESYSTEM_READ.value}), RiskLevel.LOW,
        vscode_list_extensions, (), "extension identifiers", category="vscode",
    ))
    registry.register(ToolSpec(
        "vscode.install_extension", "Install VS Code extension",
        "Install a validated extension identifier through the VS Code CLI",
        frozenset({Permission.PROCESS_EXECUTE.value, Permission.WINDOW_CONTROL.value}),
        RiskLevel.HIGH, vscode_install_extension, ("extension_id",), "process result",
        category="vscode", destructive=True,
    ))
    registry.register(ToolSpec(
        "vscode.uninstall_extension", "Uninstall VS Code extension",
        "Uninstall a validated extension identifier through the VS Code CLI",
        frozenset({Permission.PROCESS_EXECUTE.value, Permission.WINDOW_CONTROL.value}),
        RiskLevel.HIGH, vscode_uninstall_extension, ("extension_id",), "process result",
        category="vscode", destructive=True,
    ))
    registry.register(ToolSpec(
        "vscode.validate", "Validate repository in VS Code workflow",
        "Run an allow-listed repository validation command",
        frozenset({Permission.PROCESS_EXECUTE.value, Permission.FILESYSTEM_READ.value}),
        RiskLevel.HIGH, vscode_validate, ("command",), "process result", category="vscode",
    ))
    registry.register(ToolSpec(
        "vscode.delegate", "Delegate to Copilot or Codex",
        "Send one browser-authorized coding prompt to an installed local coding agent",
        frozenset({Permission.PROCESS_EXECUTE.value, Permission.FILESYSTEM_READ.value,
                   Permission.FILESYSTEM_WRITE.value}),
        RiskLevel.HIGH, vscode_delegate, ("worker", "prompt"), "process result", category="vscode",
        destructive=True,
    ))
    registry.register(ToolSpec(
        "vscode.coordinate", "Write coding coordination packet",
        "Persist a browser-authorized plan for local coding workers",
        frozenset({Permission.FILESYSTEM_WRITE.value}), RiskLevel.MEDIUM,
        vscode_coordinate, ("task_id", "objective", "plan"), "path", category="vscode",
    ))
    launch_desktop, type_visible, calculator = register_desktop_tools(
        registry, keyboard=keyboard)
    registry.register(ToolSpec("desktop.launch", "Launch desktop app", "Open an allow-listed visible Windows app",
                               frozenset({Permission.WINDOW_CONTROL.value}), RiskLevel.MEDIUM,
                               launch_desktop, ("application",), "application"))
    registry.register(ToolSpec("desktop.type", "Type visibly", "Type text into the focused visible app",
                               frozenset({Permission.KEYBOARD_WRITE.value, Permission.WINDOW_CONTROL.value}),
                               RiskLevel.HIGH, type_visible, ("text",), "string"))
    registry.register(ToolSpec("desktop.calculator", "Calculate visibly", "Open Calculator and enter an expression",
                               frozenset({Permission.KEYBOARD_WRITE.value, Permission.WINDOW_CONTROL.value}),
                               RiskLevel.MEDIUM, calculator, ("expression",), "expression"))
