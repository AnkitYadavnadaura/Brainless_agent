import asyncio
import hashlib
import json
import sys
from pathlib import Path

from app.agents.cli import run_agent_cli
from app.agents.planning import AgentPlanningWorkflow
from app.bootstrap import Application
from app.config.settings import load_settings
from app.main import CLI_ADVISORY_NOTICE
from app.safety.permissions import Permission
from app.autonomy.blender_capability import blender_candidate
from app.autonomy.blender_planner import (
    plan_execution_arguments,
    parse_plan_response,
    plan_operations,
    planning_prompt,
    split_plan,
)
from app.autonomy.models import AgentSpec
from app.autonomy.capability_lifecycle import CapabilityStatus


async def restore_saved_conversations(app: Application, root: Path) -> list[str]:
    conversation_file = root / "data" / "conversation-urls.json"
    try:
        data = json.loads(conversation_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}

    urls = [url for url in data.values() if isinstance(url, str)]
    if not urls:
        print("No saved chat URLs found. Prompt flow will start fresh.")
        return []

    # Try to reattach any matching pages already present in the persistent
    # browser context. This avoids creating duplicate tabs when Chrome has
    # already restored provider-owned conversations.
    try:
        restored = await app.browser.restore_conversations()
    except Exception:
        restored = []
    if restored:
        print(f"Reattached {len(restored)} saved chat URLs from persistent session.")
        return restored
    # Fallback: attempt to open each saved URL if no matching open pages found.
    valid_urls: list[str] = []
    print(f"Opening {len(urls)} saved chat URLs...")
    for url in urls:
        try:
            await app.browser.page_for(url)
            valid_urls.append(url)
        except Exception as exc:  # stale or inaccessible saved URLs should not kill startup
            print(f"Skipping invalid saved URL: {url} ({type(exc).__name__}: {exc})")
    return valid_urls


async def process_prompt_files(app: Application, root: Path) -> None:
    prompt_root = root / "prompts"
    if not prompt_root.exists():
        print("No prompts folder found; skipping prompt processing.")
        return

    prompt_files = sorted(prompt_root.rglob("*.txt"))
    if not prompt_files:
        print("No prompt files found.")
        return

    print(f"Processing {len(prompt_files)} prompt files...")
    for prompt_file in prompt_files:
        prompt_text = prompt_file.read_text(encoding="utf-8")
        for provider_name in app.providers.names:
            provider = app.providers.get(provider_name)
            provider.prepare_conversation(prompt_text)
            await provider.open()
            await provider.verify_page()
            await provider.start_conversation()
            await provider.send_prompt(prompt_text)
            await provider.wait_for_response()
            result = await provider.extract_response()
            provider.remember_conversation()
            print(f"{provider_name}: {prompt_file.name} -> {provider.page.url}")
            print(f"Result preview: {result[:200]}...")


async def ensure_root_agent(app: Application):
    for agent in app.agent_manager.list_agents():
        if agent.parent_agent_id is None:
            return agent
    return app.agent_manager.create_root(
        "Root Operator",
        "orchestrator",
        "Handle user tasks through capability-aware agent planning",
        {permission.value for permission in Permission},
    )


def print_catalog(app: Application) -> None:
    for number, automation in enumerate(app.automation_catalog.all(), 1):
        dependency = automation.external_dependency or "none"
        print(f"{number:03d}. {automation.automation_id} | {automation.category} | "
              f"{automation.name} | {next(iter(automation.tools))} | dependency={dependency}")


async def run_catalog(app: Application, arguments_file: str | None) -> None:
    arguments: dict[str, dict[str, object]] = {}
    if arguments_file:
        path = Path(arguments_file).resolve()
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Unable to read catalog arguments: {path}: {error}") from error
        if not isinstance(loaded, dict) or not all(isinstance(value, dict) for value in loaded.values()):
            raise ValueError("Catalog arguments must be a JSON object keyed by automation id")
        arguments = loaded

    root_agent = await ensure_root_agent(app)
    results = await app.automation_runner.run_all(root_agent.agent_id, arguments)
    for number, result in enumerate(results, 1):
        detail = result.error or repr(result.output)
        print(f"{number:03d}. {result.automation_id}: {result.status} - {detail}")


async def ask_chatgpt_for_blender_plan(app: Application, objective: str):
    provider = app.providers.get("chatgpt")
    prompt = planning_prompt(objective)
    provider.prepare_conversation(prompt)
    await provider.open()
    await provider.verify_page()
    await provider.start_conversation()
    await provider.send_prompt(prompt)
    await provider.wait_for_response()
    response = await provider.extract_response()
    provider.remember_conversation()
    return parse_plan_response(response)


def _is_generic_youtube_request(objective: str) -> bool:
    """Return whether a YouTube request names no song, artist, or search term."""
    words = {
        "a", "an", "and", "from", "go", "goto", "in", "music", "on", "open",
        "play", "please", "song", "some", "tab", "the", "to", "youtube",
    }
    remaining = [
        word for word in objective.casefold().replace("-", " ").split()
        if word.strip(".,!?") not in words
    ]
    return not remaining


async def prepare_youtube_request(app: Application, objective: str) -> str:
    """Open YouTube Music and collect a concrete playback request from the user."""
    if "youtube" not in objective.casefold():
        return objective
    if not _is_generic_youtube_request(objective):
        return objective

    browser = getattr(app, "browser", None)
    if browser is not None:
        await browser.start()
        await browser.page_for("https://music.youtube.com/")
        print("Opened YouTube Music. You can choose a recommendation or specify a song.")
    answer = (await asyncio.to_thread(
        input,
        "What song should I play? Press Enter to play a recommendation from YouTube Music:\n> ",
    )).strip()
    if answer:
        return f"Play {answer} on YouTube Music"
    return "Play a song from the YouTube Music recommendations"


async def run_agent_session(app: Application, objective: str | None = None, followups: bool = True,
                            *, raise_on_error: bool = False) -> None:
    print(f"Brainless Agent starting...\n\nBrowser: READY\nChatGPT: READY\n\n{CLI_ADVISORY_NOTICE}\n")
    interactive_request=objective is None
    objective = objective if objective is not None else input("Enter task:\n> ").strip()
    if not objective:
        return

    from app.autonomy.task_relation import local_relation, classify_task, parse_task_control
    from app.autonomy.model_workflow import ModelProjectWorkflow, model_requested
    from app.autonomy.village_project_store import VillageProjectStore
    workspace = Path(__file__).resolve().parent / 'data' / 'village-workspace'
    store=VillageProjectStore(workspace/'village-projects.sqlite3')
    forced,objective=parse_task_control(objective)
    objective = await prepare_youtube_request(app, objective)
    previous=store.selected_project()
    if not objective:
        print('Provide the task after /new or /update.')
        return
    if forced=='related' and previous is None:
        print('There is no previous 3D project. Start a new modelling task first.')
        return
    relation=forced
    if interactive_request and previous and relation is None:
        relation=local_relation(objective,previous['objective'])
        if relation=='uncertain' and model_requested(objective):
            from app.autonomy.connected_village import ConnectedVillageWorkflow
            provider=app.providers.get('chatgpt')
            if hasattr(provider,'use_conversation_session'):
                provider.use_conversation_session(previous['id'])
            reasoner=ConnectedVillageWorkflow(provider,None,workspace)
            relation=await classify_task(reasoner.request,objective,previous['objective'])
            if relation=='uncertain':
                print('Project intent is unclear. Use /update TEXT for the previous model or /new TEXT for a separate model.')
                return
    if interactive_request and previous and relation=='related':
        if objective.strip().casefold()!=previous['objective'].strip().casefold():
            store.enqueue(previous['id'],objective)
        objective=previous['objective']
        print('Continuing previous 3D project:',previous['id'])
    elif forced=='new' and store.get_project(store.project_id(objective)) is not None:
        import uuid
        objective+='\n[New project '+uuid.uuid4().hex[:8]+']'
    root_agent = await ensure_root_agent(app)
    from app.autonomy.village_workflow import village_requested
    from app.autonomy.village_projects import VillageProjectWorkflow
    from app.autonomy.task_analysis import analyse_task
    task_analysis = analyse_task(objective)
    is_3d_task=forced in ('new','related') or task_analysis['workflow'] == 'blender'
    if is_3d_task:
        from dataclasses import replace
        from app.autonomy.blender_capability import build_blender_tool, health_check_blender
        workspace = Path(__file__).resolve().parent / 'data' / 'village-workspace'
        workspace.mkdir(parents=True, exist_ok=True)
        app.capability_lifecycle.register_builder('village-blender',
            lambda candidate, sandbox: build_blender_tool(candidate, workspace), health_check_blender)
        candidate = blender_candidate()
        candidate = replace(candidate, builder_key='village-blender', health_check_key='village-blender')
        record = await app.capability_lifecycle.acquire(candidate)
        if record.status is not CapabilityStatus.VALIDATED:
            raise RuntimeError(f'Blender capability unavailable: {record.failure}')
        await app.capability_lifecycle.promote(candidate)
        agent = app.autonomous.factory.create(root_agent.agent_id, AgentSpec(
            name='3D Artist', role='BlenderAgent', objective=objective, task=objective,
            required_capabilities=frozenset({'blender.scene'}), tools=frozenset({'blender.scene'}),
            task_id='3d-' + hashlib.sha256(objective.encode()).hexdigest()[:16],
            constraints={'least_privilege': True}))

        async def model_executor(child, manager):
            async def execute(arguments):
                return await manager.execute_tool(child.agent_id, 'blender.scene', arguments)
            # Both builders use a stable root and a single live worker across revisions.
            active_objective=objective
            while True:
                workflow_class=VillageProjectWorkflow if village_requested(active_objective) else ModelProjectWorkflow
                workflow = workflow_class(app.providers.get('chatgpt'), execute, workspace)
                child.current_task=active_objective
                result = await workflow.run(active_objective)
                print('3D revision output:', result)
                if not followups:
                    return result
                while True:
                    try:
                        update = (await asyncio.to_thread(input, 'Update this model or enter a new 3D task (/new, /update); Enter finishes:\n> ')).strip()
                    except EOFError:
                        return result
                    if not update:
                        return result
                    forced,cleaned=parse_task_control(update)
                    if not cleaned:
                        print('Provide the task after /new or /update.')
                        continue
                    project=workflow.store.ensure_project(active_objective)
                    revision=workflow.store.revisions(project['id'])[-1]
                    state=workflow.store.load_checkpoint(project['id'],revision['id']) or {}
                    evidence=state.get('completed',[{}])[-1].get('evidence',{})
                    objects=evidence.get('objects',[]) if isinstance(evidence.get('objects'),list) else [
                        dict(name=area+'/'+obj['id']) for area,plan in state.get('plans',{}).items() for obj in plan['objects']]
                    from app.autonomy.connected_village import ConnectedVillageWorkflow
                    reasoner=getattr(workflow,'planner',None) or ConnectedVillageWorkflow(app.providers.get('chatgpt'),execute,workspace)
                    relation=forced or await classify_task(reasoner.request,cleaned,active_objective,objects)
                    if relation=='uncertain':
                        print('I could not determine the target project. Use /update TEXT for this scene or /new TEXT for a separate scene.')
                        continue
                    if relation=='new':
                        active_objective=cleaned
                        if forced=='new' and store.get_project(store.project_id(cleaned)) is not None:
                            import uuid
                            active_objective+='\n[New project '+uuid.uuid4().hex[:8]+']'
                        print('Starting a separate 3D project; the previous scenes are retained.')
                    else:
                        request=workflow.store.enqueue(project['id'],cleaned)
                        print(f'Queued related update {request["id"]}.')
                    break

        print('Building in one visible Blender window using the configured reasoning provider. Each action has a checkpoint.')
        try:
            result = await app.agent_manager.start_agent(root_agent.agent_id, agent.agent_id, model_executor)
            print('3D project:', result)
        except Exception as error:
            print('3D task paused with resumable state:', error)
            if raise_on_error:
                raise
        return
    requirements = app.autonomous.analyzer.analyze(objective)
    provider = app.providers.get(app.providers.names[0])
    planner = AgentPlanningWorkflow(
        provider, app.agent_manager, app.autonomous.registry,
        Path(__file__).resolve().parent,
    )
    try:
        agent, created = await planner.select_or_create(
            root_agent.agent_id, "task-user", objective, requirements,
        )
    except Exception as error:
        print(f"Website planning failed: {error}")
        print("No Blender or other task execution was started.")
        if raise_on_error:
            raise
        return

    print(f"\nSelected agent: {agent.name} ({agent.role})")
    print(f"Created new agent: {created}")
    print(f"Permissions: {sorted(agent.permissions)}")
    print(f"Tools: {sorted(agent.available_tools)}")
    print("\nThe task was routed through the agent-selection planner prompt and creation flow.")

    if "youtube.play" in agent.available_tools:
        async def executor(child, manager):
            url = child.context.get("url")
            try:
                result = await manager.execute_tool(
                    child.agent_id,
                    "youtube.play",
                    {"url": url or None, "query": objective if not url else None},
                )
                return str(result)
            except Exception as error:
                return f"tool-failed: {error}"

        print("Starting agent to perform playback...")
        try:
            result = await app.agent_manager.start_agent(root_agent.agent_id, agent.agent_id, executor)
            print("Agent execution result:", result)
        except Exception as error:
            print("Agent execution failed:", error)
            if raise_on_error:
                raise


async def main() -> None:
    root = Path(__file__).resolve().parent

    # Compatibility aliases for service-style deployments. ``--once`` keeps
    # the existing one-shot CLI behavior; no startup settings are modified.
    if len(sys.argv) > 1 and sys.argv[1] == '--service':
        sys.argv[1:2] = ['runtime', 'start']
    elif len(sys.argv) > 1 and sys.argv[1] == '--once':
        sys.argv[1:2] = ['cli']

    if len(sys.argv) > 1 and sys.argv[1] == 'runtime':
        from app.runtime.persistent_service import run_runtime_cli
        await run_runtime_cli(root, sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'supervisor':
        from app.browser.supervisor import run_supervisor_cli
        await run_supervisor_cli(root, sys.argv[2:])
        return

    if len(sys.argv) == 1 or sys.argv[1] in ('browser-team', 'cli'):
        from app.browser.team_cli import run_browser_team
        from app.providers.registry import ProviderRegistry

        async def execute_with_team(team, objective):
            # Existing workflows request the chatgpt slot; the entire website
            # team now supplies that reasoning through the same provider contract.
            app = Application(root, load_settings(), providers=ProviderRegistry({'chatgpt': team}))
            try:
                # ChatGPT in the leader browser is the mandatory planner and
                # execution gateway. It decides whether/how a local capability
                # may be used; no local adapter is invoked before this call.
                await run_agent_session(app, objective, followups=False, raise_on_error=True)
            finally:
                await app.close()

        async def execute_desktop_with_team(team, objective, *, max_actions, max_minutes):
            from app.autonomy.desktop_team_workflow import run_desktop_team
            from app.browser.team_approval import confirm_desktop_action
            app = Application(root, load_settings(), providers=ProviderRegistry({'chatgpt': team}))
            try:
                return await run_desktop_team(team, app, objective, root,
                    max_actions=max_actions, max_minutes=max_minutes, approval_handler=confirm_desktop_action)
            finally:
                await app.close()

        async def execute_local_mission(objective):
            from app.autonomy.universal_mission import (
                MissionIntent, YouTubeBrowserAdapter,
            )
            app = Application(root, load_settings())
            try:
                async def ask_youtube(question):
                    await app.browser.start()
                    await app.browser.page_for("https://music.youtube.com/")
                    print("Opened YouTube Music. Choose a song or press Enter for a recommendation.")
                    return (await asyncio.to_thread(input, question + "\n> ")).strip()

                app.missions.ask = ask_youtube
                app.missions.register_adapter(
                    MissionIntent.YOUTUBE_PLAY, YouTubeBrowserAdapter(app.browser))
                mission = await app.universal_agent.run(objective)
                print(f"Mission {mission.mission_id}: {mission.status.value}")
                if mission.current_state.get("error"):
                    print("Mission error:", mission.current_state["error"])
                return 0 if mission.status.value == "completed" else 1
            finally:
                await app.close()

        arguments = sys.argv[2:] if len(sys.argv) > 1 and sys.argv[1] == 'browser-team' else ['run', *sys.argv[2:]]
        if len(sys.argv) == 1 or sys.argv[1] == 'cli':
            print('Interactive mode: start with the leader profile; use browser-team explicitly for the full fleet.')
        callbacks = {"execute_task": execute_with_team, "execute_desktop": execute_desktop_with_team}
        if len(sys.argv) == 1 or sys.argv[1] == "cli":
            callbacks["execute_local"] = execute_local_mission
        code = await run_browser_team(arguments, root, **callbacks)
        if code:
            raise SystemExit(code)
        return

    if len(sys.argv)>1 and sys.argv[1] in ('village','3d'):
        from app.autonomy.village_project_store import VillageProjectStore
        store=VillageProjectStore(root/'data'/'village-workspace'/'village-projects.sqlite3')
        if len(sys.argv)<4 or sys.argv[2] not in ('status','update','resume'):
            raise SystemExit('Usage: python run.py 3d status|resume PROJECT_ID; 3d update PROJECT_ID "request"')
        project=store.get_project(sys.argv[3])
        if project is None:
            raise SystemExit('Unknown 3D project ID')
        if sys.argv[2]=='status':
            print(json.dumps(dict(project=project,revisions=store.revisions(project['id']),
                                  requests=store.requests(project['id'])),indent=2))
            return
        if sys.argv[2]=='update':
            if len(sys.argv)<5:
                raise SystemExit('Provide the update request text')
            request=store.enqueue(project['id'],' '.join(sys.argv[4:]))
            print(f'Queued update {request["id"]}; it will run after the current revision, or on 3d resume.')
            return
        app=Application(root,load_settings())
        try:
            await app.browser.start()
            await run_agent_session(app,project['objective'],followups=False)
        finally:
            await app.close()
        return

    if len(sys.argv) >= 3 and sys.argv[1] == "catalog" and sys.argv[2] == "list":
        app = Application(root, load_settings())
        print_catalog(app)
        await app.close()
        return

    if len(sys.argv) >= 3 and sys.argv[1] == "catalog" and sys.argv[2] == "execute":
        arguments_file = None
        if len(sys.argv) == 5 and sys.argv[3] == "--arguments":
            arguments_file = sys.argv[4]
        elif len(sys.argv) != 3:
            raise SystemExit("Usage: python run.py catalog execute [--arguments arguments.json]")
        app = Application(root, load_settings())
        try:
            await app.browser.start()
            await run_catalog(app, arguments_file)
        finally:
            await app.close()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "agent":
        run_agent_cli(sys.argv[2:], root / "data/memory.db")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "single-browser":
        app = Application(root, load_settings())
        try:
            await app.browser.start()
            # Startup no longer restores or opens saved provider URLs or prompt files.
            # This prevents creating or reattaching provider tabs until explicitly requested.
            print("\nSession ready. Type a task when prompted.")
            await run_agent_session(app)
        finally:
            await app.close()
        return

    raise SystemExit('Unknown command. Use browser-team --help, cli, single-browser, agent, catalog, or 3d.')


if __name__ == "__main__":
    # Playwright launches its driver and browser through asyncio subprocesses.
    # Windows therefore must retain the default Proactor event loop; the
    # Selector policy does not implement subprocess support.
    asyncio.run(main())
