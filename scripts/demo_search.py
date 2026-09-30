import asyncio
import sys
from pathlib import Path
import argparse

# Ensure project root is on sys.path so `import app` works when executed as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bootstrap import Application
from app.config.settings import load_settings
from app.autonomy.models import ActionProposal
from app.safety.permissions import Permission
import asyncio
from urllib.parse import quote_plus
from app.agents.models import AgentStatus


class FixedDecisionProvider:
    def __init__(self, proposals):
        self._proposals = list(proposals)

    async def next_action(self, context):
        if not self._proposals:
            return None
        return self._proposals.pop(0)


async def main():
    parser = argparse.ArgumentParser(description="Deterministic Google search demo")
    parser.add_argument("query", nargs="*", default=["play relaxing piano music"], help="Search query to run")
    args = parser.parse_args()
    query_text = " ".join(args.query)

    root = Path(__file__).resolve().parent.parent
    settings = load_settings(root / "app/config/providers.yaml")
    app = Application(root, settings)
    await app.browser.start()

    # Create a permissive root with necessary permissions to grant children
    parent = app.agent_manager.create_root("LocalRoot", "operator", "Delegate", {
        Permission.SCREEN_READ.value,
        Permission.BROWSER_NAVIGATE.value,
        Permission.BROWSER_TYPE.value,
        Permission.MOUSE_CLICK.value,
        Permission.KEYBOARD_WRITE.value,
    })

    # Create a child agent explicitly authorized to type and click
    child = app.agent_manager.create_agent(parent.agent_id, "Searcher", "BrowserAgent",
                                           "Browser searcher",
                                           task="Search Google for music",
                                           permissions={
                                               Permission.SCREEN_READ.value,
                                               Permission.BROWSER_NAVIGATE.value,
                                               Permission.BROWSER_TYPE.value,
                                               Permission.MOUSE_CLICK.value,
                                               Permission.KEYBOARD_WRITE.value,
                                           },
                                           tools={"browser.navigate", "browser.type", "mouse.click", "keyboard.write", "screen.capture"})

    # Deterministic proposals: navigate to Google, then navigate to the search results URL
    search_url = f"https://www.google.com/search?q={quote_plus(query_text)}"
    # Use empty expected_state so verification is permissive (observing the
    # browser page can vary due to redirects and dynamic params).
    proposals = (
        ActionProposal("browser.navigate", {"url": "https://www.google.com"}, "Go to Google", {}),
        ActionProposal("browser.navigate", {"url": search_url}, "Open search results", {}),
    )

    # Direct execution debug: try calling the manager tool directly to ensure
    # permissions and tool invocation work outside the autonomous loop.
    try:
        child.status = AgentStatus.RUNNING
        print("Direct execute: navigating to search URL via manager.execute_tool()")
        direct_result = await app.agent_manager.execute_tool(child.agent_id, "browser.navigate", {"url": search_url})
        print("Direct execute result:", direct_result)
    except Exception as e:
        print("Direct execute failed:", e)
    finally:
        child.status = AgentStatus.READY

    provider = FixedDecisionProvider(proposals)

    print("Starting deterministic search demo — browser will be opened if not already.")
    try:
        print("Proposals:")
        for p in proposals:
            print(f" - {p.action_type}: {p.arguments} -- {p.reason}")
        # Start the specific child agent so we use the agent we created with
        # keyboard/mouse/browser permissions instead of letting AutonomousRuntime
        # create a new agent without these tools.
        async def executor(child, manager):
            run_task_id = child.current_task_id or child.context.get("task_id")
            results = await app.autonomous_actions.run_loop(child.agent_id, run_task_id,
                                                            "Search Google for music", provider)
            if not results or not results[-1].success:
                raise RuntimeError("Autonomous task did not produce a verified action")
            successful = sum(result.success and result.verified for result in results)
            recovered = len(results) - successful
            suffix = f" after {recovered} recovered failure(s)" if recovered else ""
            return f"Completed {successful} verified action(s){suffix}"

        print("Child current_task_id before start:", child.current_task_id)
        result = await app.agent_manager.start_agent(parent.agent_id, child.agent_id, executor)
        print("Demo result:", result)
        # Logging: show agent events and execution history
        print("Agent events:")
        for ev in app.agent_manager.events[-20:]:
            print(" ", ev)
        # Verification: inspect browser pages for search results
        try:
            context = app.browser._context
            found = False
            for page in context.pages:
                try:
                    url = page.url
                    # Check for typical search-result markers
                    if "google" in url:
                        count = await page.locator("h3").count()
                        print(f"Page {url} has {count} h3 elements")
                        if count > 0:
                            found = True
                            break
                except Exception:
                    continue
            print("Search results detected:" , found)
        except Exception as e:
            print("Verification failed:", e)
    except Exception as e:
        print("Demo failed:", e)
        print("Agent events (last 20):")
        for ev in app.agent_manager.events[-20:]:
            print(" ", ev)
        try:
            child_hist = app.agent_manager.get_agent(child.agent_id).execution_history
            print("Agent execution history:")
            for h in child_hist:
                print(" ", h)
        except Exception as ee:
            print("Failed reading execution history:", ee)
    finally:
        try:
            await app.browser.close()
            print("Browser closed cleanly")
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
