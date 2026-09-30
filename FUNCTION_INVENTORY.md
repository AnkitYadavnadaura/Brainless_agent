# Function inventory

This index covers maintained Python application/CLI source (`app/`, `scripts/`, root entry points, and `tests/`) plus named dashboard JavaScript functions. Generated/runtime files under `data/` and `runtime_data/` are excluded. Python docstrings are used where present; otherwise the one-line descriptions are inferred from the function name and enclosing class, so check the linked source for exact behavior.

**2538 Python functions/methods** (including tests) and **31 dashboard JavaScript functions**. Private helpers and dunder methods are included.


## `app/agents/building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `_bounded_text()` | Implements the bounded text operation. |
| 19 | `_string_set()` | Implements the string set operation. |
| 46 | `AgentDefinition.from_mapping()` | Validate an untrusted dashboard/CLI mapping into a definition. |
| 79 | `AgentDefinition.create()` | Create a child while preserving the manager's parent/tool authority checks. |
| 99 | `create_agent()` | Functional building block for Python callers. |

## `app/agents/cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `run_agent_cli()` | Runs agent cli. |
| 80 | `_record()` | Records the current object. |
| 87 | `_tree()` | Implements the tree operation. |

## `app/agents/manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `AgentManager.__init__()` | Initializes a AgentManager instance. |
| 30 | `AgentManager.create_root()` | Creates root. |
| 38 | `AgentManager.create_agent()` | Creates agent. |
| 68 | `AgentManager.get_agent()` | Retrieves agent. |
| 74 | `AgentManager.list_agents()` | Lists agents. |
| 77 | `AgentManager.available_tools()` | Return only tools currently granted and permitted for an agent. |
| 86 | `AgentManager.set_event_subscriptions()` | Implements the set event subscriptions operation for AgentManager. |
| 93 | `AgentManager.get_children()` | Retrieves children. |
| 96 | `AgentManager.get_agent_tree()` | Retrieves agent tree. |
| 101 | `AgentManager.assign_task()` | Implements the assign task operation for AgentManager. |
| 112 | `AgentManager.grant_permission()` | Grant a direct child a parent-owned capability; self-escalation is impossible. |
| 121 | `AgentManager.revoke_permission()` | Implements the revoke permission operation for AgentManager. |
| 126 | `AgentManager.lease_permission()` | Implements the lease permission operation for AgentManager. |
| 138 | `AgentManager.grant_tool()` | Authorize a registered tool for a direct child after its permissions exist. |
| 150 | `AgentManager.report_progress()` | Reports progress. |
| 154 | `AgentManager.start_agent()` | Starts agent. |
| 169 | `AgentManager.start_parallel()` | Starts parallel. |
| 172 | `AgentManager.retry_agent()` | Retries agent. |
| 181 | `AgentManager.pause_agent()` | Pauses agent. |
| 187 | `AgentManager.resume_agent()` | Resumes agent. |
| 193 | `AgentManager.terminate_agent()` | Terminates agent. |
| 201 | `AgentManager.monitor_agent()` | Implements the monitor agent operation for AgentManager. |
| 204 | `AgentManager.collect_result()` | Implements the collect result operation for AgentManager. |
| 210 | `AgentManager.execute_tool()` | Executes tool. |
| 238 | `AgentManager._run()` | Runs the current object. |
| 255 | `AgentManager._owned_child()` | Implements the owned child operation for AgentManager. |
| 261 | `AgentManager._event()` | Implements the event operation for AgentManager. |
| 269 | `AgentManager._deny()` | Denies the current object. |

## `app/agents/planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `AgentPlanningWorkflow.__init__()` | Initializes a AgentPlanningWorkflow instance. |
| 47 | `AgentPlanningWorkflow.select_or_create()` | Selects or create. |
| 67 | `AgentPlanningWorkflow._select()` | Selects the current object. |
| 89 | `AgentPlanningWorkflow._define()` | Implements the define operation for AgentPlanningWorkflow. |
| 131 | `AgentPlanningWorkflow._ask()` | Implements the ask operation for AgentPlanningWorkflow. |
| 153 | `AgentPlanningWorkflow._capabilities_for()` | Implements the capabilities for operation for AgentPlanningWorkflow. |
| 159 | `AgentPlanningWorkflow._run_definition_artifact()` | Runs definition artifact. |
| 178 | `AgentPlanningWorkflow._object()` | Implements the object operation for AgentPlanningWorkflow. |

## `app/agents/runtime_tools.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `register_capability_skilling_tool()` | Registers capability skilling tool. |
| 21 | `register_capability_skilling_tool.skill_develop()` | Implements the skill develop operation. |
| 35 | `register_runtime_tools()` | Registers runtime tools. |
| 40 | `register_runtime_tools.browser_title()` | Implements the browser title operation. |
| 44 | `register_runtime_tools.browser_navigate()` | Implements the browser navigate operation. |
| 49 | `register_runtime_tools.browser_type()` | Implements the browser type operation. |
| 54 | `register_runtime_tools.type_keys()` | Implements the type keys operation. |
| 58 | `register_runtime_tools.click_mouse()` | Implements the click mouse operation. |
| 62 | `register_runtime_tools.write_file()` | Writes file. |
| 70 | `register_runtime_tools.execute_process()` | Executes process. |
| 79 | `register_runtime_tools.screenshot()` | Implements the screenshot operation. |
| 85 | `register_runtime_tools.youtube_play()` | Play a YouTube video by URL or search query. |
| 125 | `register_runtime_tools.youtube_play.dismiss_overlays()` | Implements the dismiss overlays operation. |
| 170 | `register_runtime_tools.youtube_play.try_play_strategies()` | Implements the try play strategies operation. |
| 222 | `register_runtime_tools.vscode_discover()` | Implements the vscode discover operation. |
| 225 | `register_runtime_tools.vscode_open()` | Implements the vscode open operation. |
| 228 | `register_runtime_tools.vscode_open_file()` | Implements the vscode open file operation. |
| 231 | `register_runtime_tools.vscode_list_extensions()` | Implements the vscode list extensions operation. |
| 234 | `register_runtime_tools.vscode_install_extension()` | Implements the vscode install extension operation. |
| 237 | `register_runtime_tools.vscode_uninstall_extension()` | Implements the vscode uninstall extension operation. |
| 240 | `register_runtime_tools.vscode_validate()` | Implements the vscode validate operation. |
| 243 | `register_runtime_tools.vscode_delegate()` | Implements the vscode delegate operation. |
| 247 | `register_runtime_tools.skill_develop()` | Implements the skill develop operation. |
| 253 | `register_runtime_tools.vscode_coordinate()` | Implements the vscode coordinate operation. |

## `app/agents/tools.py`

| Line | Function / method | Description |
|---:|---|---|
| 37 | `ToolRegistry.__init__()` | Initializes a ToolRegistry instance. |
| 40 | `ToolRegistry.register()` | Registers the current object. |
| 45 | `ToolRegistry.get()` | Retrieves the current object. |
| 51 | `ToolRegistry.contains()` | Implements the contains operation for ToolRegistry. |
| 54 | `ToolRegistry.unregister()` | Implements the unregister operation for ToolRegistry. |
| 61 | `ToolRegistry.tool_ids()` | Implements the tool ids operation for ToolRegistry. |
| 64 | `ToolRegistry.invoke()` | Implements the invoke operation for ToolRegistry. |

## `app/autonomy/__init__.py`

| Line | Function / method | Description |
|---:|---|---|
| 150 | `__getattr__()` | Implements the getattr operation. |

## `app/autonomy/approvals.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `ApprovalStore.__init__()` | Initializes a ApprovalStore instance. |
| 44 | `ApprovalStore.put()` | Implements the put operation for ApprovalStore. |
| 51 | `ApprovalStore.get()` | Retrieves the current object. |
| 55 | `ApprovalStore.all()` | Implements the all operation for ApprovalStore. |
| 58 | `ApprovalStore._read()` | Reads the current object. |
| 65 | `ApprovalSystem.__init__()` | Initializes a ApprovalSystem instance. |
| 68 | `ApprovalSystem.request()` | Implements the request operation for ApprovalSystem. |
| 84 | `ApprovalSystem.decide()` | Implements the decide operation for ApprovalSystem. |
| 95 | `_request()` | Implements the request operation. |

## `app/autonomy/architectural_scene.py`

| Line | Function / method | Description |
|---:|---|---|
| 5 | `build_architectural_primitive()` | Builds architectural primitive. |

## `app/autonomy/automation_catalog.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `_definitions()` | Implements the definitions operation. |
| 151 | `AutomationCatalog.__init__()` | Initializes a AutomationCatalog instance. |
| 154 | `AutomationCatalog.get()` | Retrieves the current object. |
| 157 | `AutomationCatalog.all()` | Implements the all operation for AutomationCatalog. |
| 160 | `AutomationCatalog.matching()` | Implements the matching operation for AutomationCatalog. |
| 167 | `AutomationCatalog.reasoning_prompt()` | Implements the reasoning prompt operation for AutomationCatalog. |

## `app/autonomy/automation_runner.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `AutomationRunner.__init__()` | Initializes a AutomationRunner instance. |
| 33 | `AutomationRunner.run_one()` | Runs one. |
| 67 | `AutomationRunner.run_one.execute()` | Executes the current object. |
| 84 | `AutomationRunner.run_all()` | Runs all. |
| 96 | `all_permissions()` | Permissions suitable for the catalog parent agent. |

## `app/autonomy/benchmark.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `BenchmarkHarness.run()` | Runs the current object. |

## `app/autonomy/blender_capability.py`

| Line | Function / method | Description |
|---:|---|---|
| 27 | `find_blender()` | Finds blender. |
| 46 | `build_blender_tool()` | Builds blender tool. |
| 53 | `build_blender_tool.operate()` | Implements the operate operation. |
| 165 | `_operate_district()` | Implements the operate district operation. |
| 222 | `_operate_model_step()` | Implements the operate model step operation. |
| 269 | `_operate_village()` | Implements the operate village operation. |
| 308 | `health_check_blender()` | Implements the health check blender operation. |
| 312 | `blender_candidate()` | Implements the blender candidate operation. |
| 323 | `_safe_path()` | Implements the safe path operation. |
| 330 | `_script()` | Implements the script operation. |
| 407 | `_live_plan_script()` | Implements the live plan script operation. |
| 454 | `_plan_body()` | Plans body. |
| 475 | `_plan_outputs()` | Plans outputs. |
| 487 | `_wait_for_file()` | Waits for for file. |
| 518 | `_wait_for_live_completion()` | Waits for for live completion. |
| 544 | `_number()` | Implements the number operation. |
| 551 | `_primitive_script()` | Implements the primitive script operation. |
| 563 | `_object_transform_script()` | Implements the object transform script operation. |
| 572 | `_transform_script()` | Implements the transform script operation. |
| 589 | `_material_script()` | Implements the material script operation. |
| 612 | `_car_body_script()` | Implements the car body script operation. |
| 614 | `mat()` | Implements the mat operation. |
| 638 | `_car_wheels_script()` | Implements the car wheels script operation. |
| 652 | `_car_windows_script()` | Implements the car windows script operation. |
| 666 | `_car_lights_script()` | Implements the car lights script operation. |
| 679 | `_car_materials_script()` | Implements the car materials script operation. |
| 690 | `_car_camera_script()` | Implements the car camera script operation. |
| 699 | `_car_lighting_script()` | Implements the car lighting script operation. |

## `app/autonomy/blender_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `BlenderMissionAdapter.__init__()` | Initializes a BlenderMissionAdapter instance. |
| 34 | `BlenderMissionAdapter._invoke()` | Implements the invoke operation for BlenderMissionAdapter. |
| 46 | `BlenderMissionAdapter.execute()` | Executes the current object. |
| 62 | `BlenderMissionAdapter.verify()` | Verifies the current object. |
| 71 | `BlenderMissionAdapter._arguments()` | Implements the arguments operation for BlenderMissionAdapter. |
| 93 | `BlenderMissionAdapter._simple_operations()` | Implements the simple operations operation for BlenderMissionAdapter. |

## `app/autonomy/blender_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `planning_prompt()` | Implements the planning prompt operation. |
| 44 | `parse_plan_response()` | Parses plan response. |
| 69 | `execution_arguments()` | Implements the execution arguments operation. |
| 86 | `plan_execution_arguments()` | Plans execution arguments. |
| 105 | `split_plan()` | Splits plan. |
| 129 | `_json_object()` | Implements the json object operation. |
| 143 | `plan_operations()` | Plans operations. |
| 152 | `_validate_step_arguments()` | Validates step arguments. |
| 173 | `_require_name_and_vectors()` | Requires name and vectors. |

## `app/autonomy/blender_workflows.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `car_workflow_arguments()` | Implements the car workflow arguments operation. |

## `app/autonomy/capability_broker.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `CapabilityAssessment.snapshot()` | Implements the snapshot operation for CapabilityAssessment. |
| 43 | `CapabilityBroker.__init__()` | Initializes a CapabilityBroker instance. |
| 46 | `CapabilityBroker.assess()` | Assesses the current object. |
| 80 | `CapabilityBroker.discovery_mission()` | Create research work only; discovery never installs or invokes an external agent. |

## `app/autonomy/capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 37 | `WebsiteCapabilityDiscovery.__init__()` | Initializes a WebsiteCapabilityDiscovery instance. |
| 40 | `WebsiteCapabilityDiscovery.discover()` | Discovers the current object. |
| 52 | `WebsiteCapabilityDiscovery.discover_and_acquire()` | Discovers and acquire. |
| 57 | `WebsiteCapabilityDiscovery._prompt()` | Implements the prompt operation for WebsiteCapabilityDiscovery. |
| 76 | `WebsiteCapabilityDiscovery._parse()` | Parses the current object. |
| 115 | `AutomaticCapabilityService.__init__()` | Initializes a AutomaticCapabilityService instance. |
| 118 | `AutomaticCapabilityService.ensure()` | Ensures the current object. |

## `app/autonomy/capability_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 78 | `CapabilityStore.__init__()` | Initializes a CapabilityStore instance. |
| 90 | `CapabilityStore.save()` | Saves the current object. |
| 99 | `CapabilityStore.latest()` | Implements the latest operation for CapabilityStore. |
| 106 | `CapabilityStore.history()` | Implements the history operation for CapabilityStore. |
| 114 | `CapabilityStore._record()` | Records the current object. |
| 121 | `CapabilityStore.close()` | Closes the current object. |
| 128 | `CapabilityLifecycle.__init__()` | Initializes a CapabilityLifecycle instance. |
| 139 | `CapabilityLifecycle.register_builder()` | Registers builder. |
| 145 | `CapabilityLifecycle.acquire()` | Implements the acquire operation for CapabilityLifecycle. |
| 179 | `CapabilityLifecycle.promote()` | Implements the promote operation for CapabilityLifecycle. |
| 198 | `CapabilityLifecycle.health_check()` | Implements the health check operation for CapabilityLifecycle. |
| 205 | `CapabilityLifecycle.rollback()` | Implements the rollback operation for CapabilityLifecycle. |
| 213 | `CapabilityLifecycle._validate_candidate()` | Validates candidate. |
| 223 | `CapabilityLifecycle._health()` | Implements the health operation for CapabilityLifecycle. |
| 230 | `CapabilityLifecycle._save()` | Saves the current object. |
| 239 | `CapabilityLifecycle._now()` | Implements the now operation for CapabilityLifecycle. |

## `app/autonomy/capability_skilling.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `SkillPlanResult.snapshot()` | Implements the snapshot operation for SkillPlanResult. |
| 45 | `CapabilityGapCoordinator.__init__()` | Initializes a CapabilityGapCoordinator instance. |
| 48 | `CapabilityGapCoordinator.develop()` | Implements the develop operation for CapabilityGapCoordinator. |
| 92 | `CapabilityGapCoordinator.run()` | Compatibility entry point for runtime command routers. |
| 96 | `CapabilityGapCoordinator.coordinate()` | Implements the coordinate operation for CapabilityGapCoordinator. |
| 99 | `CapabilityGapCoordinator._record_validated()` | Records validated. |
| 131 | `CapabilityGapCoordinator._validate_plan()` | Validates plan. |

## `app/autonomy/checkpoints.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `ExecutionCheckpoint.to_dict()` | Implements the to dict operation for ExecutionCheckpoint. |
| 30 | `CheckpointStore.__init__()` | Initializes a CheckpointStore instance. |
| 33 | `CheckpointStore.save()` | Saves the current object. |
| 39 | `CheckpointStore.load()` | Loads the current object. |
| 49 | `CheckpointStore.resume()` | Load state and force a fresh observation before a caller resumes scheduling. |

## `app/autonomy/cognitive.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `IntentEngine.interpret()` | Implements the interpret operation for IntentEngine. |
| 40 | `DecisionEngine.choose()` | Chooses the current object. |
| 58 | `PerceptionPlanner.choose()` | Chooses the current object. |
| 77 | `CounterfactualPlanner.choose()` | Chooses the current object. |
| 85 | `CognitiveEngine.__init__()` | Initializes a CognitiveEngine instance. |
| 87 | `CognitiveEngine.propose()` | Implements the propose operation for CognitiveEngine. |

## `app/autonomy/connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `validate_review()` | Validates review. |
| 20 | `ConnectedVillageWorkflow.__init__()` | Initializes a ConnectedVillageWorkflow instance. |
| 26 | `ConnectedVillageWorkflow.request()` | Implements the request operation for ConnectedVillageWorkflow. |
| 47 | `ConnectedVillageWorkflow.run()` | Runs the current object. |
| 53 | `ConnectedVillageWorkflow.run.save()` | Saves the current object. |
| 114 | `ConnectedVillageWorkflow.run.perform()` | Implements the perform operation for ConnectedVillageWorkflow. |

## `app/autonomy/contracts.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `ActionContract.validate()` | Validates the current object. |

## `app/autonomy/controllers.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `ComputerController.observe()` | Observes the current object. |
| 12 | `ComputerController.execute()` | Executes the current object. |
| 16 | `BrowserController.navigate()` | Implements the navigate operation for BrowserController. |
| 20 | `FilesystemController.read()` | Reads the current object. |
| 21 | `FilesystemController.write()` | Writes the current object. |
| 22 | `FilesystemController.exists()` | Implements the exists operation for FilesystemController. |
| 27 | `FilesystemComputerController.__init__()` | Initializes a FilesystemComputerController instance. |
| 30 | `FilesystemComputerController._path()` | Implements the path operation for FilesystemComputerController. |
| 36 | `FilesystemComputerController.observe()` | Observes the current object. |
| 40 | `FilesystemComputerController.execute()` | Executes the current object. |
| 56 | `PlaywrightComputerController.__init__()` | Initializes a PlaywrightComputerController instance. |
| 60 | `PlaywrightComputerController.observe()` | Observes the current object. |
| 68 | `PlaywrightComputerController.execute()` | Executes the current object. |

## `app/autonomy/desktop_team_controller.py`

| Line | Function / method | Description |
|---:|---|---|
| 81 | `WindowsDesktopTeamController.__init__()` | Initializes a WindowsDesktopTeamController instance. |
| 92 | `WindowsDesktopTeamController.backend()` | Implements the backend operation for WindowsDesktopTeamController. |
| 99 | `WindowsDesktopTeamController._read_accessibility()` | Reads accessibility. |
| 111 | `WindowsDesktopTeamController._serialized()` | Implements the serialized operation for WindowsDesktopTeamController. |
| 113 | `WindowsDesktopTeamController._serialized.work()` | Implements the work operation for WindowsDesktopTeamController. |
| 127 | `WindowsDesktopTeamController.observe()` | Observes the current object. |
| 130 | `WindowsDesktopTeamController._observe()` | Observes the current object. |
| 154 | `WindowsDesktopTeamController.register_tools()` | Registers tools. |
| 158 | `WindowsDesktopTeamController.register_tools.handler()` | Implements the handler operation for WindowsDesktopTeamController. |
| 166 | `WindowsDesktopTeamController.execute()` | Executes the current object. |
| 169 | `WindowsDesktopTeamController.bind_decision()` | Freeze the planning observation before runtime/approval observations. |
| 179 | `WindowsDesktopTeamController._signature()` | Implements the signature operation for WindowsDesktopTeamController. |
| 182 | `WindowsDesktopTeamController._execute()` | Executes the current object. |

## `app/autonomy/desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `_decode()` | Implements the decode operation. |
| 27 | `_decode.unique_keys()` | Implements the unique keys operation. |
| 40 | `_strings()` | Implements the strings operation. |
| 45 | `_observed_text()` | Implements the observed text operation. |
| 58 | `_supported_evidence()` | Implements the supported evidence operation. |
| 63 | `_observation()` | Implements the observation operation. |
| 82 | `_prior_context()` | Implements the prior context operation. |
| 90 | `_validate_decision()` | Validates decision. |
| 135 | `run_desktop_team()` | Runs desktop team. |
| 163 | `run_desktop_team.save()` | Saves the current object. |
| 168 | `run_desktop_team.finish()` | Implements the finish operation. |
| 180 | `run_desktop_team.remaining()` | Implements the remaining operation. |
| 182 | `run_desktop_team.bounded()` | Implements the bounded operation. |
| 185 | `run_desktop_team.ask()` | Implements the ask operation. |
| 203 | `run_desktop_team.ask.reviewed_approval()` | Implements the reviewed approval operation. |

## `app/autonomy/district_scene.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `district_step()` | Implements the district step operation. |
| 24 | `district_step.mat()` | Implements the mat operation. |
| 33 | `district_step.mesh()` | Implements the mesh operation. |
| 46 | `district_step.box()` | Implements the box operation. |
| 66 | `district_step.cylinder()` | Implements the cylinder operation. |
| 83 | `district_step.foliage()` | Implements the foliage operation. |

## `app/autonomy/environment.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `EnvironmentExplorer.__init__()` | Initializes a EnvironmentExplorer instance. |
| 45 | `EnvironmentExplorer.explore()` | Implements the explore operation for EnvironmentExplorer. |
| 74 | `BoundaryMemory.__init__()` | Initializes a BoundaryMemory instance. |
| 86 | `BoundaryMemory.record()` | Records the current object. |
| 96 | `BoundaryMemory.known()` | Implements the known operation for BoundaryMemory. |
| 105 | `BoundaryMemory.close()` | Closes the current object. |

## `app/autonomy/event_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `EventStore.__init__()` | Initializes a EventStore instance. |
| 14 | `EventStore.store_event()` | Implements the store event operation for EventStore. |
| 18 | `EventStore.recent()` | Implements the recent operation for EventStore. |
| 22 | `EventStore.close()` | Closes the current object. |

## `app/autonomy/events.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `AutonomousEventBus.__init__()` | Initializes a AutonomousEventBus instance. |
| 47 | `AutonomousEventBus.publish()` | Implements the publish operation for AutonomousEventBus. |
| 58 | `AutonomousEventBus.replay()` | Implements the replay operation for AutonomousEventBus. |
| 62 | `AutonomousEventBus.queue_depth()` | Implements the queue depth operation for AutonomousEventBus. |
| 64 | `AutonomousEventBus.next()` | Implements the next operation for AutonomousEventBus. |

## `app/autonomy/executor.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `DecisionProvider.next_action()` | Implements the next action operation for DecisionProvider. |
| 38 | `ActionRuntime.__init__()` | Initializes a ActionRuntime instance. |
| 64 | `ActionRuntime._register_controller_tools()` | Registers controller tools. |
| 78 | `ActionRuntime._register_controller_tools.handler()` | Implements the handler operation for ActionRuntime. |
| 83 | `ActionRuntime.perform_proposal()` | Implements the perform proposal operation for ActionRuntime. |
| 92 | `ActionRuntime.perform()` | Implements the perform operation for ActionRuntime. |
| 199 | `ActionRuntime.run_loop()` | Runs loop. |
| 230 | `ActionRuntime._result()` | Implements the result operation for ActionRuntime. |
| 249 | `ActionRuntime._journal()` | Implements the journal operation for ActionRuntime. |
| 254 | `_verify()` | Verifies the current object. |
| 258 | `_redact_arguments()` | Audit capability references, never secret material supplied by a tool caller. |

## `app/autonomy/factory.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `AgentFactory.__init__()` | Initializes a AgentFactory instance. |
| 14 | `AgentFactory.create()` | Creates the current object. |

## `app/autonomy/governor.py`

| Line | Function / method | Description |
|---:|---|---|
| 44 | `AutonomyGovernor.__init__()` | Initializes a AutonomyGovernor instance. |
| 50 | `AutonomyGovernor.register()` | Registers the current object. |
| 61 | `AutonomyGovernor.evaluate()` | Evaluates the current object. |
| 81 | `AutonomyGovernor.record()` | Records the current object. |
| 91 | `AutonomyGovernor.snapshot()` | Implements the snapshot operation for AutonomyGovernor. |

## `app/autonomy/health.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `AgentHealthMonitor.__init__()` | Initializes a AgentHealthMonitor instance. |
| 13 | `AgentHealthMonitor.heartbeat()` | Implements the heartbeat operation for AgentHealthMonitor. |
| 14 | `AgentHealthMonitor.inspect()` | Implements the inspect operation for AgentHealthMonitor. |
| 20 | `AgentHealthMonitor.replace()` | Replacement preserves only parent-approved permissions/tools; never escalates. |

## `app/autonomy/landmark_plans.py`

| Line | Function / method | Description |
|---:|---|---|
| 5 | `landmark_starter()` | Return an explicitly approximate Taj Mahal assembly, or no fallback. |
| 12 | `landmark_starter.add()` | Adds the current object. |

## `app/autonomy/live_blender.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `LiveBlenderSession.__init__()` | Initializes a LiveBlenderSession instance. |
| 21 | `LiveBlenderSession.ensure_started()` | Ensures started. |
| 53 | `LiveBlenderSession.run()` | Runs the current object. |

## `app/autonomy/live_blender_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `write()` | Writes the current object. |
| 27 | `inside()` | Implements the inside operation. |
| 34 | `finish()` | Implements the finish operation. |
| 41 | `redraw()` | Implements the redraw operation. |
| 47 | `visible_geometry()` | Do not reveal hidden objects or move the view to a light/camera. |
| 53 | `world_bounds()` | Frame evaluated geometry, including modifiers, parents and local offsets. |
| 70 | `follow_view()` | Move viewport navigation only; never move or keyframe the scene camera. |
| 106 | `tick()` | Implements the tick operation. |

## `app/autonomy/mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `Mission.touch()` | Implements the touch operation for Mission. |
| 41 | `Mission.refresh_progress()` | Refreshes progress. |
| 52 | `MissionStore.__init__()` | Initializes a MissionStore instance. |
| 56 | `MissionStore.save()` | Saves the current object. |
| 65 | `MissionStore.load()` | Loads the current object. |
| 69 | `MissionStore.active()` | Implements the active operation for MissionStore. |
| 73 | `MissionStore.all()` | Return persisted history, including terminal missions, for observability. |
| 77 | `MissionStore._read()` | Reads the current object. |
| 82 | `_mission()` | Implements the mission operation. |

## `app/autonomy/mode_policy.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `ModePolicy.__init__()` | Initializes a ModePolicy instance. |
| 7 | `ModePolicy.decision()` | Implements the decision operation for ModePolicy. |

## `app/autonomy/model_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `model_requested()` | Implements the model requested operation. |
| 28 | `validate_model_step()` | Validates model step. |
| 84 | `validate_model_plan()` | Validates model plan. |
| 109 | `compact_scene()` | Implements the compact scene operation. |
| 120 | `verify_model_evidence()` | Verifies model evidence. |
| 142 | `ModelProjectWorkflow.__init__()` | Initializes a ModelProjectWorkflow instance. |
| 147 | `ModelProjectWorkflow._revision()` | Implements the revision operation for ModelProjectWorkflow. |
| 153 | `ModelProjectWorkflow._revision.save()` | Saves the current object. |
| 167 | `ModelProjectWorkflow._revision.save.validate_proposal()` | Validates proposal. |
| 292 | `ModelProjectWorkflow.run()` | Runs the current object. |

## `app/autonomy/models.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `RuntimeErrorDetail.__init__()` | Initializes a RuntimeErrorDetail instance. |
| 48 | `ComputerState.compact()` | Return only a decision provider's requested context fields. |
| 52 | `ComputerState.diff()` | Return the observable fields changed by an action; timestamps are not state changes. |

## `app/autonomy/monitoring.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `InterruptionManager.classify()` | Classifies the current object. |
| 23 | `UserPresenceDetector.__init__()` | Initializes a UserPresenceDetector instance. |
| 24 | `UserPresenceDetector.present()` | Implements the present operation for UserPresenceDetector. |
| 32 | `AutonomyMetrics.autonomy_score()` | Implements the autonomy score operation for AutonomyMetrics. |

## `app/autonomy/observation.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `ScreenUnderstandingProvider.observe_screen()` | Observes screen. |

## `app/autonomy/operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `MissionRunner.__call__()` | Makes the object callable. |
| 23 | `UserTakeoverManager.__init__()` | Initializes a UserTakeoverManager instance. |
| 24 | `UserTakeoverManager.begin()` | Implements the begin operation for UserTakeoverManager. |
| 25 | `UserTakeoverManager.resume()` | Resumes the current object. |
| 27 | `UserTakeoverManager.actions_allowed()` | Implements the actions allowed operation for UserTakeoverManager. |
| 30 | `BlockerDetector.classify()` | Classifies the current object. |
| 39 | `AutonomousOperator.__init__()` | Initializes a AutonomousOperator instance. |
| 47 | `AutonomousOperator.create()` | Creates the current object. |
| 52 | `AutonomousOperator.run_once()` | Runs once. |
| 76 | `AutonomousOperator.process_event()` | Processes event. |
| 87 | `AutonomousOperator.run_background()` | Event-driven loop: no model calls or busy polling while idle. |
| 95 | `AutonomousOperator.resume_active()` | Restart recovery always observes before resuming; no stored action is replayed. |

## `app/autonomy/orchestrator.py`

| Line | Function / method | Description |
|---:|---|---|
| 27 | `CapabilityAnalyzer.analyze()` | Implements the analyze operation for CapabilityAnalyzer. |
| 83 | `AutonomousRuntime.__init__()` | Initializes a AutonomousRuntime instance. |
| 92 | `AutonomousRuntime.execute()` | Executes the current object. |
| 116 | `AutonomousRuntime.execute.work()` | Implements the work operation for AutonomousRuntime. |

## `app/autonomy/perception_service.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `PerceptionService.__init__()` | Initializes a PerceptionService instance. |
| 9 | `PerceptionService.observe()` | Observes the current object. |

## `app/autonomy/planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 37 | `TaskContextManager.build()` | Builds the current object. |
| 46 | `PlanValidator.validate()` | Validates the current object. |

## `app/autonomy/production_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `VerifiedMissionCriterion.__init__()` | Initializes a VerifiedMissionCriterion instance. |
| 15 | `VerifiedMissionCriterion.verify()` | Verifies the current object. |
| 23 | `RuntimeMissionComposer.__init__()` | Initializes a RuntimeMissionComposer instance. |
| 28 | `RuntimeMissionComposer.graph_for()` | Implements the graph for operation for RuntimeMissionComposer. |
| 58 | `RuntimeMissionComposer.criteria_for()` | Implements the criteria for operation for RuntimeMissionComposer. |
| 61 | `RuntimeMissionComposer.__call__()` | Makes the object callable. |

## `app/autonomy/proposals.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `ReasoningProvider.propose()` | Implements the propose operation for ReasoningProvider. |
| 79 | `ActionRequest.to_computer_action()` | Implements the to computer action operation for ActionRequest. |
| 91 | `ProposalValidator.__init__()` | Initializes a ProposalValidator instance. |
| 94 | `ProposalValidator.validate_action()` | Validates action. |
| 128 | `ProposalValidator.validate()` | Validates the current object. |

## `app/autonomy/reasoning_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `ChatbotReasoningProvider.__init__()` | Initializes a ChatbotReasoningProvider instance. |
| 26 | `ChatbotReasoningProvider.propose()` | Implements the propose operation for ChatbotReasoningProvider. |
| 36 | `ChatbotReasoningProvider._prompt()` | Implements the prompt operation for ChatbotReasoningProvider. |
| 53 | `ChatbotReasoningProvider.parse()` | Parses the current object. |
| 68 | `_redact()` | Keep secret material out of provider context, including nested structures. |
| 79 | `ReasoningDecisionProvider.__init__()` | Initializes a ReasoningDecisionProvider instance. |
| 82 | `ReasoningDecisionProvider.next_action()` | Implements the next action operation for ReasoningDecisionProvider. |

## `app/autonomy/recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `RecoveryEngine.choose()` | Chooses the current object. |

## `app/autonomy/registry.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `ReliabilityMetrics.success_rate()` | Implements the success rate operation for ReliabilityMetrics. |
| 25 | `ReliabilityMetrics.average_duration_ms()` | Implements the average duration ms operation for ReliabilityMetrics. |
| 31 | `AgentRegistry.__init__()` | Initializes a AgentRegistry instance. |
| 36 | `AgentRegistry.register()` | Registers the current object. |
| 41 | `AgentRegistry.retire()` | Implements the retire operation for AgentRegistry. |
| 45 | `AgentRegistry.find()` | Finds the current object. |
| 53 | `AgentRegistry.record_result()` | Records result. |
| 65 | `AgentRegistry.metrics_for()` | Implements the metrics for operation for AgentRegistry. |
| 68 | `AgentRegistry.capabilities_for()` | Implements the capabilities for operation for AgentRegistry. |
| 69 | `AgentRegistry.search_by_role()` | Searches by role. |
| 70 | `AgentRegistry.available()` | Implements the available operation for AgentRegistry. |
| 71 | `AgentRegistry.agents()` | Implements the agents operation for AgentRegistry. |

## `app/autonomy/resources.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `ResourceLockManager.__init__()` | Initializes a ResourceLockManager instance. |
| 19 | `ResourceLockManager.acquire()` | Implements the acquire operation for ResourceLockManager. |
| 35 | `ResourceLockManager.release_agent()` | Best-effort cleanup for an agent that died outside its context manager. |
| 44 | `ResourceLockManager.owners()` | Implements the owners operation for ResourceLockManager. |

## `app/autonomy/runtime_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `RuntimeUpgradeManager.__init__()` | Initializes a RuntimeUpgradeManager instance. |
| 34 | `RuntimeUpgradeManager.stage()` | Implements the stage operation for RuntimeUpgradeManager. |
| 48 | `RuntimeUpgradeManager.activate()` | Implements the activate operation for RuntimeUpgradeManager. |
| 59 | `RuntimeUpgradeManager.rollback()` | Implements the rollback operation for RuntimeUpgradeManager. |
| 66 | `RuntimeUpgradeManager.active_version()` | Implements the active version operation for RuntimeUpgradeManager. |
| 70 | `RuntimeUpgradeManager._validate_manifest()` | Validates manifest. |
| 79 | `RuntimeUpgradeManager._read_active()` | Reads active. |

## `app/autonomy/target.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `ResolvedTarget.__post_init__()` | Validates or derives dataclass fields after initialization. |
| 26 | `TargetProvider.resolve()` | Resolves the current object. |
| 30 | `TargetResolver.__init__()` | Initializes a TargetResolver instance. |
| 33 | `TargetResolver.resolve()` | Resolves the current object. |
| 48 | `TargetResolver.resolve_environment()` | Resolve normalized UI semantically; kept separate from legacy ComputerState callers. |

## `app/autonomy/task_analysis.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `analyse_task()` | Implements the analyse task operation. |

## `app/autonomy/task_engine.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `GoalCriterion.verify()` | Verifies the current object. |
| 43 | `GoalCompletionVerifier.verify()` | Verifies the current object. |
| 65 | `AutonomousTaskEngine.__init__()` | Initializes a AutonomousTaskEngine instance. |
| 73 | `AutonomousTaskEngine.run()` | Backward-compatible single-node goal execution and journal vocabulary. |
| 90 | `AutonomousTaskEngine.run_graph()` | Runs graph. |
| 108 | `AutonomousTaskEngine.run_graph.execute_node()` | Executes node. |
| 139 | `AutonomousTaskEngine.run_with_learning()` | Runs with learning. |
| 193 | `AutonomousTaskEngine._checkpoint()` | Implements the checkpoint operation for AutonomousTaskEngine. |
| 206 | `AutonomousTaskEngine._journal()` | Implements the journal operation for AutonomousTaskEngine. |

## `app/autonomy/task_graph.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `TaskGraph.__init__()` | Initializes a TaskGraph instance. |
| 44 | `TaskGraph.add()` | Adds the current object. |
| 51 | `TaskGraph.validate()` | Validates the current object. |
| 58 | `TaskGraph.validate.visit()` | Implements the visit operation for TaskGraph. |
| 70 | `TaskGraph.runnable()` | Implements the runnable operation for TaskGraph. |
| 74 | `TaskGraph.complete()` | Implements the complete operation for TaskGraph. |
| 77 | `TaskGraph.fail()` | Implements the fail operation for TaskGraph. |
| 87 | `TaskGraph._block_dependents()` | Implements the block dependents operation for TaskGraph. |
| 93 | `TaskGraph.pause()` | Pauses the current object. |
| 97 | `TaskGraph.resume()` | Resumes the current object. |
| 101 | `TaskGraph.cancel()` | Cancels the current object. |
| 105 | `TaskGraph.replan()` | Implements the replan operation for TaskGraph. |
| 117 | `TaskScheduler.next_tasks()` | Implements the next tasks operation for TaskScheduler. |

## `app/autonomy/task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `_normalise()` | Implements the normalise operation. |
| 62 | `parse_task_control()` | Strip an explicit routing command, preserving the user's actual task. |
| 70 | `_subject()` | Implements the subject operation. |
| 74 | `_object_names()` | Implements the object names operation. |
| 85 | `local_relation()` | Implements the local relation operation. |
| 149 | `_validate_relation()` | Validates relation. |
| 157 | `classify_task()` | Classifies task. |

## `app/autonomy/task_runner.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `TaskEngineMissionRunner.__init__()` | Initializes a TaskEngineMissionRunner instance. |
| 16 | `TaskEngineMissionRunner.__call__()` | Makes the object callable. |
| 28 | `TaskEngineMissionRunner._restore()` | Restores the current object. |
| 36 | `TaskEngineMissionRunner._serialize()` | Serializes the current object. |

## `app/autonomy/team.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `AgentTeamBuilder.build()` | Builds the current object. |

## `app/autonomy/tool_builder.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `ToolBuilder.__init__()` | Initializes a ToolBuilder instance. |
| 33 | `ToolBuilder.stage()` | Implements the stage operation for ToolBuilder. |
| 47 | `ToolBuilder.promote()` | Implements the promote operation for ToolBuilder. |

## `app/autonomy/triggers.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `TriggerStore.__init__()` | Initializes a TriggerStore instance. |
| 18 | `TriggerStore.save()` | Saves the current object. |
| 21 | `TriggerStore.all()` | Implements the all operation for TriggerStore. |
| 22 | `TriggerStore._read()` | Reads the current object. |
| 24 | `TriggerEngine.__init__()` | Initializes a TriggerEngine instance. |
| 27 | `TriggerEngine._fire()` | Implements the fire operation for TriggerEngine. |
| 33 | `TriggerEngine.tick()` | Implements the tick operation for TriggerEngine. |
| 41 | `TriggerEngine.handle()` | Handles the current object. |
| 50 | `FilesystemWatcher.__init__()` | Initializes a FilesystemWatcher instance. |
| 53 | `FilesystemWatcher.poll()` | Polls the current object. |
| 58 | `ProcessWatcher.__init__()` | Initializes a ProcessWatcher instance. |
| 59 | `ProcessWatcher.poll()` | Polls the current object. |

## `app/autonomy/universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `StepAdapter.execute()` | Executes the current object. |
| 69 | `StepAdapter.verify()` | Verifies the current object. |
| 72 | `understand_request()` | Classify obvious capabilities locally before opening any provider. |
| 127 | `plan_request()` | Create a bounded default plan; complex plans can be supplied by a leader. |
| 169 | `UniversalMissionCoordinator.__init__()` | Initializes a UniversalMissionCoordinator instance. |
| 173 | `UniversalMissionCoordinator.register_adapter()` | Register a trusted domain adapter at the composition boundary. |
| 179 | `UniversalMissionCoordinator.create()` | Creates the current object. |
| 206 | `UniversalMissionCoordinator.execute()` | Executes the current object. |
| 258 | `UniversalAgent.__init__()` | Initializes a UniversalAgent instance. |
| 263 | `UniversalAgent.run()` | Runs the current object. |
| 290 | `GeneralCliMissionAdapter.__init__()` | Initializes a GeneralCliMissionAdapter instance. |
| 296 | `GeneralCliMissionAdapter._paths()` | Implements the paths operation for GeneralCliMissionAdapter. |
| 310 | `GeneralCliMissionAdapter._tool()` | Implements the tool operation for GeneralCliMissionAdapter. |
| 316 | `GeneralCliMissionAdapter.execute()` | Executes the current object. |
| 354 | `GeneralCliMissionAdapter.verify()` | Verifies the current object. |
| 365 | `_parse_checksum()` | Parses checksum. |
| 376 | `YouTubeBrowserAdapter.__init__()` | Initializes a YouTubeBrowserAdapter instance. |
| 379 | `YouTubeBrowserAdapter.execute()` | Executes the current object. |
| 423 | `YouTubeBrowserAdapter.verify()` | Verifies the current object. |
| 434 | `_quote()` | Implements the quote operation. |
| 442 | `BrowserTeamMissionAdapter.__init__()` | Initializes a BrowserTeamMissionAdapter instance. |
| 445 | `BrowserTeamMissionAdapter.execute()` | Executes the current object. |
| 454 | `BrowserTeamMissionAdapter.verify()` | Verifies the current object. |

## `app/autonomy/universal_router.py`

| Line | Function / method | Description |
|---:|---|---|
| 27 | `UniversalTaskRouter.__init__()` | Initializes a UniversalTaskRouter instance. |
| 36 | `UniversalTaskRouter.run()` | Runs the current object. |

## `app/autonomy/unreal_capability.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `find_unreal_editor()` | Finds unreal editor. |
| 25 | `build_unreal_tool()` | Builds unreal tool. |
| 31 | `build_unreal_tool.operate()` | Implements the operate operation. |
| 54 | `health_check_unreal()` | Implements the health check unreal operation. |
| 58 | `unreal_candidate()` | Implements the unreal candidate operation. |
| 68 | `_safe_project()` | Implements the safe project operation. |
| 75 | `_script()` | Implements the script operation. |

## `app/autonomy/video_capability.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `build_ffmpeg_video_tool()` | Build a repository-scoped video adapter; no shell string is ever parsed. |
| 20 | `build_ffmpeg_video_tool.edit()` | Implements the edit operation. |
| 45 | `health_check_ffmpeg()` | Implements the health check ffmpeg operation. |
| 49 | `video_candidate()` | Implements the video candidate operation. |
| 66 | `_safe_path()` | Implements the safe path operation. |

## `app/autonomy/village_districts.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `validate_component()` | Validates component. |
| 23 | `master_plan()` | Implements the master plan operation. |
| 57 | `area_context()` | Implements the area context operation. |
| 65 | `number()` | Implements the number operation. |
| 71 | `starter_area_plan()` | A sparse, validated layout that fits even the minimum 24m district. |
| 91 | `validate_area()` | Validates area. |
| 158 | `validate_polish()` | Validates polish. |

## `app/autonomy/village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `project_id()` | Retain the existing village directory identity, including its exact text. |
| 19 | `_text()` | Implements the text operation. |
| 25 | `_now()` | Implements the now operation. |
| 34 | `VillageProjectStore.__init__()` | Initializes a VillageProjectStore instance. |
| 94 | `VillageProjectStore._connection()` | Implements the connection operation for VillageProjectStore. |
| 107 | `VillageProjectStore._project()` | Implements the project operation for VillageProjectStore. |
| 114 | `VillageProjectStore._revision()` | Implements the revision operation for VillageProjectStore. |
| 121 | `VillageProjectStore._revision_dict()` | Implements the revision dict operation for VillageProjectStore. |
| 128 | `VillageProjectStore._request()` | Implements the request operation for VillageProjectStore. |
| 134 | `VillageProjectStore.ensure_project()` | Ensures project. |
| 144 | `VillageProjectStore.get_project()` | Retrieves project. |
| 149 | `VillageProjectStore.select_project()` | Selects project. |
| 155 | `VillageProjectStore.selected_project()` | Implements the selected project operation for VillageProjectStore. |
| 160 | `VillageProjectStore.enqueue()` | Implements the enqueue operation for VillageProjectStore. |
| 170 | `VillageProjectStore.requests()` | Implements the requests operation for VillageProjectStore. |
| 180 | `VillageProjectStore.update_request()` | Updates request. |
| 191 | `VillageProjectStore.create_revision()` | Creates revision. |
| 210 | `VillageProjectStore.revisions()` | Implements the revisions operation for VillageProjectStore. |
| 216 | `VillageProjectStore.update_revision()` | Updates revision. |
| 228 | `VillageProjectStore.append_event()` | Implements the append event operation for VillageProjectStore. |
| 241 | `VillageProjectStore.events()` | Implements the events operation for VillageProjectStore. |
| 251 | `VillageProjectStore.save_checkpoint()` | Saves checkpoint. |
| 261 | `VillageProjectStore.load_checkpoint()` | Loads checkpoint. |

## `app/autonomy/village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `checkpoint_path()` | Implements the checkpoint path operation. |
| 24 | `project_lock()` | A process-owned lock; an interrupted process cannot leave a stale lease. |
| 52 | `validate_revision()` | Validates revision. |
| 84 | `fork_revision()` | Copy the verified prefix into a new revision; keep all parent files intact. |
| 129 | `VillageProjectWorkflow.__init__()` | Initializes a VillageProjectWorkflow instance. |
| 133 | `VillageProjectWorkflow._execute_revision()` | Executes revision. |
| 155 | `VillageProjectWorkflow._execute_revision.saved()` | Implements the saved operation for VillageProjectWorkflow. |
| 180 | `VillageProjectWorkflow.run()` | Runs the current object. |

## `app/autonomy/village_scene.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `_village_material()` | Use metre-scaled surface detail, independent of a mesh's dimensions. |
| 93 | `build_stage()` | Builds stage. |
| 101 | `build_stage.material()` | Implements the material operation. |
| 104 | `build_stage.box()` | Implements the box operation. |
| 122 | `build_stage.layout()` | Implements the layout operation. |

## `app/autonomy/village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `validate_config()` | Validates config. |
| 25 | `village_requested()` | Implements the village requested operation. |
| 30 | `digest()` | Implements the digest operation. |
| 38 | `ask()` | Implements the ask operation. |
| 65 | `VillageWorkflow.__init__()` | Initializes a VillageWorkflow instance. |
| 69 | `VillageWorkflow.run()` | Runs the current object. |
| 75 | `VillageWorkflow.run.save()` | Saves the current object. |

## `app/autonomy/vscode_worker.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `VscodeWorker.__init__()` | Initializes a VscodeWorker instance. |
| 38 | `VscodeWorker.discover()` | Discovers the current object. |
| 47 | `VscodeWorker.open_workspace()` | Implements the open workspace operation for VscodeWorker. |
| 56 | `VscodeWorker.open_file()` | Implements the open file operation for VscodeWorker. |
| 66 | `VscodeWorker.list_extensions()` | Lists extensions. |
| 73 | `VscodeWorker.install_extension()` | Implements the install extension operation for VscodeWorker. |
| 78 | `VscodeWorker.uninstall_extension()` | Implements the uninstall extension operation for VscodeWorker. |
| 83 | `VscodeWorker.validate()` | Validates the current object. |
| 99 | `VscodeWorker.delegate()` | Invoke an installed coding-agent CLI with a single explicit prompt. |
| 118 | `VscodeWorker._require_vscode()` | Requires vscode. |
| 124 | `VscodeWorker._workspace_path()` | Implements the workspace path operation for VscodeWorker. |
| 133 | `VscodeWorker._validate_extension_id()` | Validates extension id. |
| 137 | `VscodeWorker.write_coordination_packet()` | Writes coordination packet. |
| 155 | `VscodeWorker._run()` | Runs the current object. |
| 174 | `VscodeWorker._which()` | Implements the which operation for VscodeWorker. |

## `app/autonomy/world_model.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `CausalEvidence.confidence()` | Implements the confidence operation for CausalEvidence. |
| 40 | `CausalModel.__init__()` | Initializes a CausalModel instance. |
| 42 | `CausalModel.observe()` | Observes the current object. |
| 49 | `CausalModel.evidence()` | Implements the evidence operation for CausalModel. |
| 54 | `WorldModel.__init__()` | Initializes a WorldModel instance. |
| 58 | `WorldModel.predict()` | Implements the predict operation for WorldModel. |
| 63 | `WorldModel.compare()` | Compares the current object. |
| 73 | `WorldModel.export_state()` | Serializable runtime evidence for journals and crash checkpoints. |
| 83 | `WorldModel.simulate()` | Return a copy of a predicted state only; does not call tools or mutate reality. |

## `app/autonomy/world_state.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `WorldSnapshot.values()` | Implements the values operation for WorldSnapshot. |
| 46 | `WorldStateManager.__init__()` | Initializes a WorldStateManager instance. |
| 51 | `WorldStateManager.version()` | Implements the version operation for WorldStateManager. |
| 54 | `WorldStateManager.capture()` | Captures the current object. |
| 66 | `WorldStateManager.record()` | Records the current object. |
| 74 | `WorldStateManager.invalidate_stale()` | Implements the invalidate stale operation for WorldStateManager. |
| 85 | `WorldStateManager.get()` | Retrieves the current object. |
| 90 | `WorldStateManager.snapshot()` | Implements the snapshot operation for WorldStateManager. |
| 95 | `WorldStateManager.diff()` | Implements the diff operation for WorldStateManager. |

## `app/bootstrap.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `Application.__init__()` | Initializes a Application instance. |
| 124 | `Application.close()` | Closes the current object. |

## `app/browser/browser_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `BrowserManager.__init__()` | Initializes a BrowserManager instance. |
| 29 | `BrowserManager.start()` | Starts the current object. |
| 50 | `BrowserManager.page_for()` | Implements the page for operation for BrowserManager. |
| 61 | `BrowserManager.conversation_page()` | Return the dedicated, persistent tab for one provider/prompt pair. |
| 107 | `BrowserManager.rotate_conversation()` | Replace only this project's owned tab with a fresh, empty chat. |
| 137 | `BrowserManager.reopen_conversation()` | Reload this owned chat for response recovery; never start a new chat. |
| 153 | `BrowserManager.remember_conversation()` | Persist a provider-owned chat URL without retaining the prompt text. |
| 166 | `BrowserManager._conversation_key()` | Implements the conversation key operation for BrowserManager. |
| 170 | `BrowserManager._load_conversation_urls()` | Loads conversation urls. |
| 177 | `BrowserManager.restore_conversations()` | Reattach in-memory conversation pages to any matching restored URLs. |
| 202 | `BrowserManager._same_origin()` | Implements the same origin operation for BrowserManager. |
| 206 | `BrowserManager.close()` | Closes the current object. |

## `app/browser/chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `ChromiumTransport.__init__()` | Initializes a ChromiumTransport instance. |
| 25 | `ChromiumTransport._page()` | Implements the page operation for ChromiumTransport. |
| 34 | `ChromiumTransport._host()` | Implements the host operation for ChromiumTransport. |
| 37 | `ChromiumTransport.navigate()` | Implements the navigate operation for ChromiumTransport. |
| 48 | `ChromiumTransport.evaluate()` | Evaluates the current object. |
| 69 | `ChromiumLeader.__init__()` | Initializes a ChromiumLeader instance. |
| 89 | `ChromiumLeader.start()` | Starts the current object. |
| 145 | `ChromiumLeader._close()` | Closes the current object. |
| 156 | `ChromiumLeader.close()` | Closes the current object. |

## `app/browser/fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `_finish_owned_operation()` | Drain desktop work despite repeated cancellation, then let callers commit. |
| 36 | `BrowserFleet.__init__()` | Initializes a BrowserFleet instance. |
| 82 | `BrowserFleet._inventory_entries()` | Defend injected/stale inventories against aliases and missing browsers. |
| 101 | `BrowserFleet.status()` | Return JSON-ready lifecycle state; ready means tabs opened, not signed in. |
| 131 | `BrowserFleet._start_leader()` | Starts leader. |
| 169 | `BrowserFleet.close_leader()` | Closes leader. |
| 188 | `BrowserFleet._record_recovery()` | Records recovery. |
| 192 | `BrowserFleet._publish_clients()` | Implements the publish clients operation for BrowserFleet. |
| 211 | `BrowserFleet._discard_participants()` | Implements the discard participants operation for BrowserFleet. |
| 218 | `BrowserFleet._cleanup_window()` | Keep failed closes tracked so a retry cannot create duplicate windows. |
| 245 | `BrowserFleet._claim_window()` | Implements the claim window operation for BrowserFleet. |
| 265 | `BrowserFleet._recover_window()` | Implements the recover window operation for BrowserFleet. |
| 281 | `BrowserFleet._launch_window()` | Launches window. |
| 297 | `BrowserFleet._check_ready_window()` | Return True to keep/hold this profile, False to rebuild a lost window. |
| 325 | `BrowserFleet.start()` | Open each unique profile once and retry only after confirmed cleanup. |
| 429 | `BrowserFleet._close_locked()` | Closes locked. |
| 437 | `BrowserFleet.close()` | Close only owned windows, retaining failed cleanup for a later retry. |

## `app/browser/fleet_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 99 | `_path_key()` | Implements the path key operation. |
| 103 | `_identifier()` | Implements the identifier operation. |
| 107 | `_registry_executables()` | Implements the registry executables operation. |
| 126 | `_metadata_text()` | Implements the metadata text operation. |
| 142 | `_safe_component()` | Implements the safe component operation. |
| 147 | `_display_name()` | Implements the display name operation. |
| 155 | `_profile()` | Implements the profile operation. |
| 161 | `_chromium_profiles()` | Implements the chromium profiles operation. |
| 210 | `_firefox_profiles()` | Implements the firefox profiles operation. |
| 250 | `discover_browsers()` | Discovers browsers. |
| 328 | `managed_leader_profile()` | Select the profile Chrome opens for the app's --user-data-dir command. |
| 343 | `profile_launch_arguments()` | Implements the profile launch arguments operation. |

## `app/browser/native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 163 | `_accessible_page()` | Extract only explicit chat controls/assistant groups from a bounded tree. |
| 230 | `_accessible_page.belongs()` | Implements the belongs operation. |
| 305 | `NativeTransportError.__init__()` | Initializes a NativeTransportError instance. |
| 313 | `NativeLaunchError.__init__()` | Initializes a NativeLaunchError instance. |
| 321 | `NativeConsoleIntervention.__init__()` | Initializes a NativeConsoleIntervention instance. |
| 326 | `_marker_title()` | Implements the marker title operation. |
| 347 | `_console_accessible()` | Require the focused console input, not merely a page mentioning it. |
| 371 | `WindowsDesktopBackend.__init__()` | Initializes a WindowsDesktopBackend instance. |
| 403 | `WindowsDesktopBackend.windows()` | Implements the windows operation for WindowsDesktopBackend. |
| 408 | `WindowsDesktopBackend.windows.collect()` | Implements the collect operation for WindowsDesktopBackend. |
| 423 | `WindowsDesktopBackend.spawn()` | Implements the spawn operation for WindowsDesktopBackend. |
| 426 | `WindowsDesktopBackend.identity()` | Implements the identity operation for WindowsDesktopBackend. |
| 436 | `WindowsDesktopBackend.focus()` | Implements the focus operation for WindowsDesktopBackend. |
| 467 | `WindowsDesktopBackend._focus_caption()` | Click only a freshly hit-tested, uncovered, inert owned title bar. |
| 489 | `WindowsDesktopBackend.foreground()` | Implements the foreground operation for WindowsDesktopBackend. |
| 492 | `WindowsDesktopBackend.hotkey()` | Implements the hotkey operation for WindowsDesktopBackend. |
| 495 | `WindowsDesktopBackend.click()` | Implements the click operation for WindowsDesktopBackend. |
| 498 | `WindowsDesktopBackend.point_in_window()` | Implements the point in window operation for WindowsDesktopBackend. |
| 508 | `WindowsDesktopBackend.clipboard_read()` | Implements the clipboard read operation for WindowsDesktopBackend. |
| 511 | `WindowsDesktopBackend.clipboard_write()` | Implements the clipboard write operation for WindowsDesktopBackend. |
| 514 | `WindowsDesktopBackend.console_ready()` | Implements the console ready operation for WindowsDesktopBackend. |
| 527 | `WindowsDesktopBackend._accessibility()` | Implements the accessibility operation for WindowsDesktopBackend. |
| 550 | `WindowsDesktopBackend.accessibility_snapshot()` | Implements the accessibility snapshot operation for WindowsDesktopBackend. |
| 553 | `WindowsDesktopBackend.control_at()` | Implements the control at operation for WindowsDesktopBackend. |
| 557 | `WindowsDesktopBackend.focused_control()` | Implements the focused control operation for WindowsDesktopBackend. |
| 561 | `WindowsDesktopBackend.address_bar()` | Implements the address bar operation for WindowsDesktopBackend. |
| 564 | `WindowsDesktopBackend.focus_composer()` | Implements the focus composer operation for WindowsDesktopBackend. |
| 567 | `WindowsDesktopBackend.invoke_send()` | Implements the invoke send operation for WindowsDesktopBackend. |
| 570 | `WindowsDesktopBackend.copy_response()` | Implements the copy response operation for WindowsDesktopBackend. |
| 573 | `WindowsDesktopBackend.copy_message()` | Implements the copy message operation for WindowsDesktopBackend. |
| 576 | `WindowsDesktopBackend.close()` | Closes the current object. |
| 588 | `NativeConsoleTransport.__init__()` | Initializes a NativeConsoleTransport instance. |
| 611 | `NativeConsoleTransport._serialized()` | Implements the serialized operation for NativeConsoleTransport. |
| 612 | `NativeConsoleTransport._serialized.run()` | Runs the current object. |
| 636 | `NativeConsoleTransport._check_owned()` | Checks owned. |
| 640 | `NativeConsoleTransport._is_uncertain()` | Returns whether uncertain. |
| 644 | `NativeConsoleTransport._mark_uncertain()` | Implements the mark uncertain operation for NativeConsoleTransport. |
| 650 | `NativeConsoleTransport._forget_window()` | Removes window. |
| 656 | `NativeConsoleTransport._check_focus()` | Checks focus. |
| 661 | `NativeConsoleTransport._input()` | Implements the input operation for NativeConsoleTransport. |
| 665 | `NativeConsoleTransport._focus()` | Implements the focus operation for NativeConsoleTransport. |
| 676 | `NativeConsoleTransport._restore_clipboard()` | Restores clipboard. |
| 684 | `NativeConsoleTransport.launch()` | Launches the current object. |
| 691 | `NativeConsoleTransport._launch()` | Launches the current object. |
| 721 | `NativeConsoleTransport.recover_launch()` | Adopt a late window using its original launch evidence, without input. |
| 729 | `NativeConsoleTransport._recover_launch()` | Implements the recover launch operation for NativeConsoleTransport. |
| 751 | `NativeConsoleTransport.window_alive()` | Check recorded ownership without focusing or discarding cleanup state. |
| 757 | `NativeConsoleTransport.window_alive.inspect()` | Implements the inspect operation for NativeConsoleTransport. |
| 761 | `NativeConsoleTransport.navigate()` | Implements the navigate operation for NativeConsoleTransport. |
| 768 | `NativeConsoleTransport._navigate()` | Implements the navigate operation for NativeConsoleTransport. |
| 802 | `NativeConsoleTransport.evaluate()` | Evaluates the current object. |
| 810 | `NativeConsoleTransport._evaluate()` | Evaluates the current object. |
| 883 | `NativeConsoleTransport.native_action()` | Implements the native action operation for NativeConsoleTransport. |
| 904 | `NativeConsoleTransport._native_snapshot()` | Implements the native snapshot operation for NativeConsoleTransport. |
| 922 | `NativeConsoleTransport._native_click()` | Implements the native click operation for NativeConsoleTransport. |
| 935 | `NativeConsoleTransport._copy_observed_text()` | Implements the copy observed text operation for NativeConsoleTransport. |
| 959 | `NativeConsoleTransport._native_action()` | Implements the native action operation for NativeConsoleTransport. |
| 1109 | `NativeConsoleTransport.hotkey()` | Implements the hotkey operation for NativeConsoleTransport. |
| 1114 | `NativeConsoleTransport.hotkey.apply()` | Implements the apply operation for NativeConsoleTransport. |
| 1119 | `NativeConsoleTransport.click()` | Implements the click operation for NativeConsoleTransport. |
| 1122 | `NativeConsoleTransport.click.apply()` | Implements the apply operation for NativeConsoleTransport. |
| 1130 | `NativeConsoleTransport.close()` | Closes the current object. |
| 1131 | `NativeConsoleTransport.close.apply()` | Implements the apply operation for NativeConsoleTransport. |

## `app/browser/page_observer.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `observe_page()` | Observes page. |

## `app/browser/supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `_now()` | Implements the now operation. |
| 43 | `SupervisorStore.__init__()` | Initializes a SupervisorStore instance. |
| 55 | `SupervisorStore.close()` | Closes the current object. |
| 58 | `SupervisorStore.enqueue()` | Implements the enqueue operation for SupervisorStore. |
| 68 | `SupervisorStore.get()` | Retrieves the current object. |
| 72 | `SupervisorStore.ready()` | Implements the ready operation for SupervisorStore. |
| 79 | `SupervisorStore.update()` | Updates the current object. |
| 93 | `SupervisorStore.all()` | Implements the all operation for SupervisorStore. |
| 98 | `SupervisorStore._task()` | Implements the task operation for SupervisorStore. |
| 105 | `BrowserSupervisor.__init__()` | Initializes a BrowserSupervisor instance. |
| 120 | `BrowserSupervisor.enqueue()` | Implements the enqueue operation for BrowserSupervisor. |
| 127 | `BrowserSupervisor.stop()` | Stops the current object. |
| 131 | `BrowserSupervisor.run_once()` | Runs once. |
| 195 | `BrowserSupervisor._failed()` | Implements the failed operation for BrowserSupervisor. |
| 207 | `BrowserSupervisor.run_forever()` | Runs forever. |
| 217 | `supervisor_parser()` | Implements the supervisor parser operation. |
| 233 | `run_supervisor_cli()` | Runs supervisor cli. |

## `app/browser/team_approval.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `confirm_desktop_action()` | No terminal, no approval; timeout and cancellation never authorize an action. |

## `app/browser/team_board.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `TeamBoard.__init__()` | Initializes a TeamBoard instance. |
| 33 | `TeamBoard.path()` | Implements the path operation for TeamBoard. |
| 36 | `TeamBoard.begin()` | Implements the begin operation for TeamBoard. |
| 42 | `TeamBoard.latest()` | Implements the latest operation for TeamBoard. |
| 47 | `TeamBoard.plan()` | Plans the current object. |
| 56 | `TeamBoard.task()` | Implements the task operation for TeamBoard. |
| 63 | `TeamBoard.post()` | Implements the post operation for TeamBoard. |
| 82 | `TeamBoard.inbox()` | Implements the inbox operation for TeamBoard. |
| 89 | `TeamBoard.acknowledge()` | Acknowledges the current object. |
| 98 | `TeamBoard.finish()` | Implements the finish operation for TeamBoard. |
| 107 | `TeamBoard.snapshot()` | Implements the snapshot operation for TeamBoard. |
| 125 | `TeamBoard.publish()` | Implements the publish operation for TeamBoard. |

## `app/browser/team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `_wait_seconds()` | Waits for seconds. |
| 25 | `_timeout()` | Implements the timeout operation. |
| 32 | `parser()` | Implements the parser operation. |
| 99 | `inventory_snapshot()` | Implements the inventory snapshot operation. |
| 106 | `saved_status()` | Read checkpoints without creating a store or disclosing complete task text. |
| 141 | `_save_fleet_report()` | Saves fleet report. |
| 152 | `run_browser_team()` | Runs browser team. |

## `app/browser/team_diagnostics.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `write_report()` | Writes report. |
| 19 | `matches_challenge()` | Implements the matches challenge operation. |
| 27 | `run_live_smoke()` | Exercise actual configured clients; mocks are labelled by their driver. |

## `app/computer/clipboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 4 | `read_text()` | Reads text. |

## `app/computer/desktop.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `ApplicationLauncher.launch()` | Launches the current object. |
| 27 | `WindowsApplicationLauncher.launch()` | Launches the current object. |
| 37 | `register_desktop_tools()` | Registers desktop tools. |
| 43 | `register_desktop_tools.launch()` | Launches the current object. |
| 48 | `register_desktop_tools.type_visible()` | Implements the type visible operation. |
| 53 | `register_desktop_tools.calculator()` | Implements the calculator operation. |

## `app/computer/keyboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `KeyboardBackend.write()` | Writes the current object. |
| 9 | `KeyboardBackend.hotkey()` | Implements the hotkey operation for KeyboardBackend. |
| 13 | `Keyboard.__init__()` | Initializes a Keyboard instance. |
| 16 | `Keyboard.type_text()` | Implements the type text operation for Keyboard. |
| 21 | `Keyboard.press_hotkey()` | Implements the press hotkey operation for Keyboard. |
| 27 | `_pyautogui()` | Implements the pyautogui operation. |

## `app/computer/mouse.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `MouseBackend.click()` | Implements the click operation for MouseBackend. |
| 12 | `Mouse.__init__()` | Initializes a Mouse instance. |
| 15 | `Mouse.click()` | Implements the click operation for Mouse. |
| 21 | `_pyautogui()` | Implements the pyautogui operation. |

## `app/computer/ocr.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `OcrReader.read()` | Reads the current object. |

## `app/computer/screenshot.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `ScreenshotRecorder.__init__()` | Initializes a ScreenshotRecorder instance. |
| 15 | `ScreenshotRecorder.capture()` | Captures the current object. |

## `app/config/settings.py`

| Line | Function / method | Description |
|---:|---|---|
| 47 | `load_settings()` | Load settings relative to the repository root unless a path is supplied. |

## `app/dashboard/runtime_bridge.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `RuntimeEventBridge.__init__()` | Initializes a RuntimeEventBridge instance. |
| 14 | `RuntimeEventBridge.pump_once()` | Implements the pump once operation for RuntimeEventBridge. |

## `app/dashboard/server.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `DashboardServer.__init__()` | Initializes a DashboardServer instance. |
| 28 | `DashboardServer.address()` | Implements the address operation for DashboardServer. |
| 30 | `DashboardServer.start()` | Starts the current object. |
| 33 | `DashboardServer.close()` | Closes the current object. |
| 37 | `DashboardServer._handler()` | Implements the handler operation for DashboardServer. |
| 40 | `DashboardServer.Handler._handler.log_message()` | Implements the log message operation for Handler. |
| 41 | `DashboardServer.Handler._handler.do_GET()` | Implements the do GET operation for Handler. |
| 73 | `DashboardServer.Handler._handler.do_POST()` | Implements the do POST operation for Handler. |
| 95 | `DashboardServer.Handler._handler._authorized()` | Implements the authorized operation for Handler. |
| 98 | `DashboardServer.Handler._handler._file()` | Implements the file operation for Handler. |
| 101 | `DashboardServer.Handler._handler._json()` | Implements the json operation for Handler. |
| 104 | `DashboardServer.Handler._handler._screenshot()` | Implements the screenshot operation for Handler. |
| 119 | `DashboardServer.Handler._handler._security_headers()` | Implements the security headers operation for Handler. |

## `app/dashboard/service.py`

| Line | Function / method | Description |
|---:|---|---|
| 64 | `RuntimeCommandGateway.__init__()` | Initializes a RuntimeCommandGateway instance. |
| 69 | `RuntimeCommandGateway.authorized()` | Implements the authorized operation for RuntimeCommandGateway. |
| 72 | `RuntimeCommandGateway.execute()` | Executes the current object. |
| 188 | `DashboardService.__init__()` | Initializes a DashboardService instance. |
| 191 | `DashboardService.snapshot()` | Implements the snapshot operation for DashboardService. |
| 248 | `DashboardService.health()` | Implements the health operation for DashboardService. |
| 263 | `DashboardService.events()` | Implements the events operation for DashboardService. |
| 268 | `DashboardService.search()` | Searches the current object. |
| 280 | `DashboardService.inventory()` | Implements the inventory operation for DashboardService. |
| 289 | `DashboardService.memory()` | Implements the memory operation for DashboardService. |
| 293 | `DashboardService.skills()` | Implements the skills operation for DashboardService. |
| 302 | `DashboardService.notifications()` | Implements the notifications operation for DashboardService. |
| 306 | `DashboardService.analytics()` | Implements the analytics operation for DashboardService. |
| 331 | `DashboardService._mission()` | Implements the mission operation for DashboardService. |
| 343 | `DashboardService._agent()` | Implements the agent operation for DashboardService. |
| 355 | `DashboardService._action()` | Implements the action operation for DashboardService. |
| 361 | `DashboardService._event()` | Implements the event operation for DashboardService. |
| 370 | `DashboardService._trigger()` | Implements the trigger operation for DashboardService. |
| 375 | `DashboardService._world()` | Implements the world operation for DashboardService. |
| 380 | `DashboardService._approvals()` | Implements the approvals operation for DashboardService. |
| 389 | `DashboardService._perception()` | Implements the perception operation for DashboardService. |
| 394 | `DashboardService._voice_health()` | Implements the voice health operation for DashboardService. |
| 399 | `DashboardService._perception_health()` | Implements the perception health operation for DashboardService. |
| 404 | `DashboardService._task_mission_index()` | Implements the task mission index operation for DashboardService. |
| 409 | `_redact()` | Redacts the current object. |
| 413 | `_ratio()` | Implements the ratio operation. |

## `app/event_system/actions.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `ActionRegistry.__init__()` | Initializes a ActionRegistry instance. |
| 20 | `ActionRegistry.register()` | Registers the current object. |
| 23 | `ActionRegistry.available()` | Implements the available operation for ActionRegistry. |
| 25 | `ActionRegistry.get()` | Retrieves the current object. |
| 26 | `ActionRegistry.emergency_stop()` | Implements the emergency stop operation for ActionRegistry. |
| 29 | `ActionRegistry.resume()` | Resumes the current object. |
| 30 | `ActionRegistry.execute()` | Executes the current object. |
| 46 | `ActionRegistry.execute.invoke_sync()` | Implements the invoke sync operation for ActionRegistry. |
| 65 | `ActionRegistry._record_failure()` | Records failure. |

## `app/event_system/agents.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `AgentEventDispatcher.__init__()` | Initializes a AgentEventDispatcher instance. |
| 7 | `AgentEventDispatcher.dispatch()` | Dispatches the current object. |

## `app/event_system/audit.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `sanitize()` | Implements the sanitize operation. |
| 25 | `StructuredEventLogger.__init__()` | Initializes a StructuredEventLogger instance. |
| 32 | `StructuredEventLogger.write()` | Writes the current object. |
| 37 | `StructuredEventLogger.event()` | Implements the event operation for StructuredEventLogger. |
| 41 | `StructuredEventLogger.action()` | Implements the action operation for StructuredEventLogger. |
| 45 | `StructuredEventLogger.security()` | Implements the security operation for StructuredEventLogger. |

## `app/event_system/autowindow.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `AutoWindow.__init__()` | Initializes a AutoWindow instance. |
| 20 | `AutoWindow.call_action()` | Implements the call action operation for AutoWindow. |
| 21 | `AutoWindow.call_action_sync()` | Implements the call action sync operation for AutoWindow. |
| 22 | `AutoWindow.set_variable()` | Implements the set variable operation for AutoWindow. |
| 23 | `AutoWindow.get_variable()` | Retrieves variable. |
| 24 | `AutoWindow.poll_events()` | Polls events. |
| 25 | `AutoWindow.emergency_stop()` | Implements the emergency stop operation for AutoWindow. |
| 26 | `AutoWindow.resume_agent_system()` | Resumes agent system. |
| 27 | `AutoWindow.get_data()` | Retrieves data. |

## `app/event_system/building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `AgentBlueprint.create()` | Creates the current object. |
| 53 | `create_event_agent()` | Creates event agent. |
| 64 | `discover_agent_actions()` | Return serializable action metadata filtered to an agent's current authority. |
| 75 | `AgentResourceLimiter.__init__()` | Initializes a AgentResourceLimiter instance. |
| 81 | `AgentResourceLimiter._within()` | Implements the within operation for AgentResourceLimiter. |
| 88 | `AgentResourceLimiter.allow_event()` | Implements the allow event operation for AgentResourceLimiter. |
| 92 | `AgentResourceLimiter.begin_action()` | Implements the begin action operation for AgentResourceLimiter. |
| 102 | `AgentResourceLimiter.end_action()` | Implements the end action operation for AgentResourceLimiter. |
| 109 | `AgentActionExecutor.__init__()` | Initializes a AgentActionExecutor instance. |
| 112 | `AgentActionExecutor.execute()` | Executes the current object. |
| 137 | `EventAgentRuntime.__init__()` | Initializes a EventAgentRuntime instance. |
| 142 | `EventAgentRuntime.handle()` | Handles the current object. |
| 152 | `EventChain.__init__()` | Initializes a EventChain instance. |
| 155 | `EventChain.then()` | Implements the then operation for EventChain. |
| 157 | `EventChain.delay()` | Implements the delay operation for EventChain. |
| 158 | `EventChain.delay.pause()` | Pauses the current object. |
| 161 | `EventChain.action()` | Implements the action operation for EventChain. |
| 166 | `EventChain.branch()` | Implements the branch operation for EventChain. |
| 169 | `EventChain.parallel()` | Implements the parallel operation for EventChain. |
| 170 | `EventChain.parallel.run()` | Runs the current object. |
| 173 | `EventChain.repeat()` | Implements the repeat operation for EventChain. |
| 174 | `EventChain.repeat.run()` | Runs the current object. |
| 177 | `EventChain.retry()` | Retries the current object. |
| 178 | `EventChain.retry.run()` | Runs the current object. |
| 187 | `EventChain._invoke()` | Implements the invoke operation for EventChain. |
| 191 | `EventChain.run()` | Runs the current object. |
| 195 | `EventChain.run.execute()` | Executes the current object. |

## `app/event_system/bus.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `EventHistory.__init__()` | Initializes a EventHistory instance. |
| 15 | `EventHistory.append()` | Implements the append operation for EventHistory. |
| 16 | `EventHistory.replay()` | Implements the replay operation for EventHistory. |
| 18 | `EventHistory.clear()` | Clears the current object. |
| 21 | `EventBus.__init__()` | Initializes a EventBus instance. |
| 27 | `EventBus.subscribe()` | Subscribes to the current object. |
| 29 | `EventBus.unsubscribe()` | Unsubscribes from the current object. |
| 30 | `EventBus.publish()` | Implements the publish operation for EventBus. |
| 41 | `EventBus.route_pending()` | Implements the route pending operation for EventBus. |
| 53 | `EventBus.replay()` | Route retained events without duplicating them in history. |
| 60 | `EventBus.pause()` | Pauses the current object. |
| 61 | `EventBus.resume()` | Resumes the current object. |
| 64 | `EventRouter.__init__()` | Initializes a EventRouter instance. |
| 65 | `EventRouter.route()` | Implements the route operation for EventRouter. |
| 69 | `EventDetector.poll()` | Polls the current object. |
| 72 | `EventManager.__init__()` | Initializes a EventManager instance. |
| 74 | `EventManager.poll_once()` | Polls once. |
| 82 | `EventManager.run()` | Runs the current object. |
| 88 | `EventManager.stop()` | Stops the current object. |

## `app/event_system/config.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `_boolean()` | Implements the boolean operation. |
| 38 | `EventSystemConfig.from_mapping()` | Implements the from mapping operation for EventSystemConfig. |

## `app/event_system/detectors.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `FilesystemDetector.__init__()` | Initializes a FilesystemDetector instance. |
| 11 | `FilesystemDetector.poll()` | Polls the current object. |
| 42 | `ResourceDetector.__init__()` | Initializes a ResourceDetector instance. |
| 43 | `ResourceDetector.poll()` | Polls the current object. |
| 55 | `WindowsCapabilityReport.detect()` | Detects the current object. |
| 75 | `MousePositionDetector.__init__()` | Initializes a MousePositionDetector instance. |
| 76 | `MousePositionDetector.poll()` | Polls the current object. |
| 88 | `ClipboardDetector.__init__()` | Initializes a ClipboardDetector instance. |
| 89 | `ClipboardDetector.poll()` | Polls the current object. |
| 101 | `DisplayDetector.__init__()` | Initializes a DisplayDetector instance. |
| 102 | `DisplayDetector.poll()` | Polls the current object. |
| 114 | `ProcessDetector.__init__()` | Initializes a ProcessDetector instance. |
| 115 | `ProcessDetector._read_windows()` | Reads windows. |
| 119 | `ProcessDetector.poll()` | Polls the current object. |
| 138 | `SnapshotDetector.__init__()` | Initializes a SnapshotDetector instance. |
| 141 | `SnapshotDetector.poll()` | Polls the current object. |
| 149 | `SnapshotDetector._event()` | Implements the event operation for SnapshotDetector. |
| 156 | `NetworkDetector.read_interfaces()` | Reads interfaces. |
| 163 | `NetworkDetector.__init__()` | Initializes a NetworkDetector instance. |
| 170 | `WindowDetector.read_windows()` | Reads windows. |
| 176 | `WindowDetector.__init__()` | Initializes a WindowDetector instance. |
| 179 | `WindowDetector.poll()` | Polls the current object. |
| 202 | `PowerDetector.__init__()` | Initializes a PowerDetector instance. |
| 204 | `PowerDetector._read_windows()` | Reads windows. |
| 215 | `PowerDetector.poll()` | Polls the current object. |
| 231 | `SchedulerDetector.__init__()` | Initializes a SchedulerDetector instance. |
| 232 | `SchedulerDetector.schedule()` | Implements the schedule operation for SchedulerDetector. |
| 236 | `SchedulerDetector.cancel()` | Cancels the current object. |
| 237 | `SchedulerDetector.poll()` | Polls the current object. |

## `app/event_system/factory.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `EventPlatform.emergency_stop()` | Implements the emergency stop operation for EventPlatform. |
| 29 | `EventPlatform.resume()` | Resumes the current object. |
| 33 | `create_event_platform()` | Creates event platform. |

## `app/event_system/models.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `Event.__post_init__()` | Validates or derives dataclass fields after initialization. |
| 42 | `EventFilter.matches()` | Implements the matches operation for EventFilter. |
| 54 | `ConditionEngine.matches()` | Implements the matches operation for ConditionEngine. |
| 93 | `ActionResult.success()` | Implements the success operation for ActionResult. |

## `app/event_system/native_actions.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `register_desktop_actions()` | Registers desktop actions. |
| 12 | `register_desktop_actions.pyauto()` | Implements the pyauto operation. |
| 15 | `register_desktop_actions.clipboard()` | Implements the clipboard operation. |
| 18 | `register_desktop_actions.path()` | Implements the path operation. |
| 19 | `register_desktop_actions.copy_file()` | Implements the copy file operation. |
| 20 | `register_desktop_actions.move_file()` | Implements the move file operation. |
| 21 | `register_desktop_actions.delete_file()` | Deletes file. |
| 22 | `register_desktop_actions.delete_folder()` | Deletes folder. |
| 23 | `register_desktop_actions.start_process()` | Starts process. |
| 24 | `register_desktop_actions.stop_process()` | Stops process. |
| 28 | `register_desktop_actions.get_screen_size()` | Retrieves screen size. |
| 30 | `register_desktop_actions.get_monitors()` | Retrieves monitors. |
| 37 | `register_desktop_actions.get_monitors.callback()` | Implements the callback operation. |
| 43 | `register_desktop_actions.focus_application()` | Implements the focus application operation. |
| 49 | `register_desktop_actions.request_power()` | Implements the request power operation. |
| 53 | `register_desktop_actions.open_path()` | Implements the open path operation. |
| 58 | `register_desktop_actions.window()` | Implements the window operation. |

## `app/event_system/permissions.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `permission_for_event()` | Resolve the least observation permission for an event category. |

## `app/event_system/testing.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `MockEventGenerator.__init__()` | Initializes a MockEventGenerator instance. |
| 14 | `MockEventGenerator.emit()` | Emits the current object. |
| 19 | `MockEventGenerator.poll()` | Polls the current object. |

## `app/event_system/windows_detectors.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `_windows_only()` | Implements the windows only operation. |
| 29 | `_powershell_json()` | Run a fixed, non-interactive PowerShell inventory query. |
| 49 | `KeyboardPrivacyFilter.protect()` | Implements the protect operation for KeyboardPrivacyFilter. |
| 72 | `KeyboardDetector.__init__()` | Initializes a KeyboardDetector instance. |
| 81 | `KeyboardDetector._read_windows()` | Reads windows. |
| 86 | `KeyboardDetector.poll()` | Polls the current object. |
| 111 | `KeyboardDetector._event()` | Implements the event operation for KeyboardDetector. |
| 122 | `MouseDetector.__init__()` | Initializes a MouseDetector instance. |
| 132 | `MouseDetector._read_windows()` | Reads windows. |
| 143 | `MouseDetector.poll()` | Polls the current object. |
| 174 | `MouseDetector._event()` | Implements the event operation for MouseDetector. |
| 190 | `DeviceDetector.__init__()` | Initializes a DeviceDetector instance. |
| 194 | `DeviceDetector._read_windows()` | Reads windows. |
| 200 | `DeviceDetector.poll()` | Polls the current object. |
| 209 | `DeviceDetector._events()` | Implements the events operation for DeviceDetector. |
| 225 | `AudioDetector._read_windows()` | Reads windows. |
| 231 | `AudioDetector._events()` | Implements the events operation for AudioDetector. |
| 246 | `SessionDetector.__init__()` | Initializes a SessionDetector instance. |
| 250 | `SessionDetector._read_windows()` | Reads windows. |
| 256 | `SessionDetector.poll()` | Polls the current object. |
| 266 | `SessionDetector._event()` | Implements the event operation for SessionDetector. |
| 276 | `NotificationDetector.__init__()` | Initializes a NotificationDetector instance. |
| 280 | `NotificationDetector._read_windows()` | Reads windows. |
| 290 | `NotificationDetector.poll()` | Polls the current object. |
| 305 | `create_windows_detectors()` | Creates windows detectors. |

## `app/extraction/clipboard_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `ClipboardExtractor.__init__()` | Initializes a ClipboardExtractor instance. |
| 14 | `ClipboardExtractor.extract()` | Extracts the current object. |

## `app/extraction/fallback_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `OcrReader.read()` | Reads the current object. |
| 16 | `ResponseFallbackExtractor.__init__()` | Initializes a ResponseFallbackExtractor instance. |
| 20 | `ResponseFallbackExtractor.extract_from_clipboard()` | Extracts from clipboard. |
| 24 | `ResponseFallbackExtractor.extract_from_ocr()` | Extracts from ocr. |

## `app/extraction/response_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `validate_response()` | Validates response. |

## `app/gui.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `BrainlessWindow.__init__()` | Initializes a BrainlessWindow instance. |
| 33 | `BrainlessWindow._build()` | Builds the current object. |
| 85 | `BrainlessWindow.start()` | Starts the current object. |
| 112 | `BrainlessWindow._run_team()` | Runs team. |
| 114 | `BrainlessWindow._run_team.execute()` | Executes the current object. |
| 131 | `BrainlessWindow._run_task()` | Runs task. |
| 132 | `BrainlessWindow._run_task.execute()` | Executes the current object. |
| 145 | `BrainlessWindow.toggle_pause()` | Implements the toggle pause operation for BrainlessWindow. |
| 156 | `BrainlessWindow.stop()` | Stops the current object. |
| 164 | `BrainlessWindow.continue_after_intervention()` | Implements the continue after intervention operation for BrainlessWindow. |
| 169 | `BrainlessWindow._poll_events()` | Polls events. |
| 192 | `BrainlessWindow._append()` | Implements the append operation for BrainlessWindow. |
| 198 | `BrainlessWindow.refresh_history()` | Refreshes history. |
| 205 | `BrainlessWindow.close()` | Closes the current object. |
| 209 | `BrainlessWindow.run()` | Runs the current object. |
| 213 | `main()` | Implements the main operation. |

## `app/learning/core.py`

| Line | Function / method | Description |
|---:|---|---|
| 83 | `ExperienceMemory.__init__()` | Initializes a ExperienceMemory instance. |
| 94 | `ExperienceMemory.store()` | Implements the store operation for ExperienceMemory. |
| 104 | `ExperienceMemory.retrieve()` | Implements the retrieve operation for ExperienceMemory. |
| 123 | `ExperienceMemory.for_task_type()` | Return recent runtime evidence for continuous skill evaluation. |
| 137 | `ExperienceMemory.add_feedback()` | Adds feedback. |
| 146 | `ExperienceMemory.feedback_score()` | Implements the feedback score operation for ExperienceMemory. |
| 150 | `ExperienceMemory.purge_expired()` | Remove non-critical stale records and return the number removed. |
| 157 | `ExperienceMemory.close()` | Closes the current object. |
| 160 | `SkillRegistry.__init__()` | Initializes a SkillRegistry instance. |
| 170 | `SkillRegistry._audit()` | Implements the audit operation for SkillRegistry. |
| 174 | `SkillRegistry.audit_trail()` | Implements the audit trail operation for SkillRegistry. |
| 178 | `SkillRegistry.register()` | Registers the current object. |
| 187 | `SkillRegistry.versions()` | Implements the versions operation for SkillRegistry. |
| 189 | `SkillRegistry.search()` | Searches the current object. |
| 191 | `SkillRegistry.list_skills()` | Lists skills. |
| 192 | `SkillRegistry.get()` | Retrieves the current object. |
| 194 | `SkillRegistry.set_status()` | Implements the set status operation for SkillRegistry. |
| 213 | `SkillRegistry.approve()` | Human approval is explicit and never grants runtime permissions. |
| 219 | `SkillRegistry.reject()` | Implements the reject operation for SkillRegistry. |
| 221 | `SkillRegistry.deprecate()` | Implements the deprecate operation for SkillRegistry. |
| 222 | `SkillRegistry.update_evaluation()` | Updates evaluation. |
| 236 | `SkillRegistry.candidates()` | Implements the candidates operation for SkillRegistry. |
| 237 | `SkillRegistry._all()` | Implements the all operation for SkillRegistry. |
| 239 | `SkillRegistry.close()` | Closes the current object. |
| 244 | `WorkflowSynthesizer.synthesize()` | Implements the synthesize operation for WorkflowSynthesizer. |
| 256 | `_terms()` | Implements the terms operation. |
| 257 | `_experience()` | Implements the experience operation. |
| 259 | `_skill_dict()` | Implements the skill dict operation. |
| 261 | `_skill()` | Implements the skill operation. |

## `app/learning/engine.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `SkillSandbox.validate()` | Validates the current object. |
| 40 | `SkillSandbox.execute_restricted()` | Executes restricted. |
| 54 | `SkillSandbox.test()` | Implements the test operation for SkillSandbox. |
| 67 | `LearningCoordinator.__init__()` | Initializes a LearningCoordinator instance. |
| 72 | `LearningCoordinator.advise()` | Implements the advise operation for LearningCoordinator. |
| 89 | `LearningCoordinator.strategy_notes()` | Return contextual failure warnings as data for a planner, never commands. |
| 95 | `LearningCoordinator.select_strategy()` | Reliability-first ordering; speed only breaks otherwise equal candidates. |
| 102 | `LearningCoordinator.record()` | Records the current object. |
| 136 | `_risk_value()` | Implements the risk value operation. |

## `app/learning/evaluator.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `ExecutionEvaluator.review()` | Implements the review operation for ExecutionEvaluator. |
| 28 | `ExecutionEvaluator.metrics()` | Implements the metrics operation for ExecutionEvaluator. |
| 41 | `ExecutionEvaluator.evaluate()` | Evaluates the current object. |
| 46 | `ExecutionEvaluator.candidate()` | Implements the candidate operation for ExecutionEvaluator. |

## `app/learning/evidence.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `EvidenceStore.__init__()` | Initializes a EvidenceStore instance. |
| 24 | `EvidenceStore._load()` | Loads the current object. |
| 27 | `EvidenceStore.add()` | Adds the current object. |
| 32 | `EvidenceStore.get()` | Retrieves the current object. |
| 33 | `EvidenceStore.for_claim()` | Implements the for claim operation for EvidenceStore. |
| 34 | `EvidenceStore.close()` | Closes the current object. |
| 41 | `ConflictResolver.resolve()` | Resolves the current object. |

## `app/learning/explain.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `explain()` | Implements the explain operation. |

## `app/learning/performance.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `AgentPerformance.success_rate()` | Implements the success rate operation for AgentPerformance. |
| 14 | `AgentPerformanceMemory.__init__()` | Initializes a AgentPerformanceMemory instance. |
| 17 | `AgentPerformanceMemory.record()` | Records the current object. |
| 21 | `AgentPerformanceMemory.best()` | Implements the best operation for AgentPerformanceMemory. |
| 23 | `AgentPerformanceMemory.close()` | Closes the current object. |

## `app/learning/policy.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `PolicyEngine.__init__()` | Initializes a PolicyEngine instance. |
| 24 | `PolicyEngine.evaluate()` | Evaluates the current object. |
| 55 | `_risk()` | Implements the risk operation. |

## `app/learning/sandbox_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `DisposableFilesystemSandbox.root()` | Implements the root operation for DisposableFilesystemSandbox. |
| 18 | `DisposableFilesystemSandbox.close()` | Closes the current object. |
| 19 | `DisposableFilesystemSandbox.__enter__()` | Enters a managed context. |
| 20 | `DisposableFilesystemSandbox.__exit__()` | Cleans up a managed context. |
| 22 | `create_filesystem_sandbox()` | Creates filesystem sandbox. |

## `app/main.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `format_cli_result()` | Label provider text so it cannot be mistaken for an executed action. |
| 26 | `main()` | Implements the main operation. |

## `app/memory/memory_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `MemoryManager.__init__()` | Initializes a MemoryManager instance. |
| 13 | `MemoryManager.relevant_context()` | Implements the relevant context operation for MemoryManager. |

## `app/memory/sqlite_memory.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `SQLiteMemory.__init__()` | Initializes a SQLiteMemory instance. |
| 46 | `SQLiteMemory.store()` | Implements the store operation for SQLiteMemory. |
| 55 | `SQLiteMemory.search()` | Searches the current object. |
| 67 | `SQLiteMemory.recent_metadata()` | Dashboard-safe task history without prompt, response, or screenshot content. |
| 74 | `SQLiteMemory.close()` | Closes the current object. |
| 78 | `SQLiteMemory.store_agent()` | Persist an agent snapshot without coupling memory to the orchestration package. |
| 92 | `SQLiteMemory.store_agent_event()` | Implements the store agent event operation for SQLiteMemory. |
| 100 | `SQLiteMemory.agent_events()` | Implements the agent events operation for SQLiteMemory. |
| 107 | `SQLiteMemory.agent_records()` | Implements the agent records operation for SQLiteMemory. |
| 113 | `SQLiteMemory.store_action_audit()` | Persist runtime-owned computer action audit records without an autonomy import. |
| 123 | `SQLiteMemory.computer_action_audit()` | Implements the computer action audit operation for SQLiteMemory. |
| 130 | `SQLiteMemory.store_task_journal()` | Implements the store task journal operation for SQLiteMemory. |
| 137 | `SQLiteMemory.task_journal()` | Implements the task journal operation for SQLiteMemory. |

## `app/perception/change.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `VisualChangeDetector.compare()` | Compares the current object. |
| 49 | `HumanBlockerDetector.detect()` | Detects the current object. |

## `app/perception/context.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `MultimodalCommand.__post_init__()` | Validates or derives dataclass fields after initialization. |
| 47 | `ContextBuilder.__init__()` | Initializes a ContextBuilder instance. |
| 50 | `ContextBuilder.build()` | Builds the current object. |

## `app/perception/engine.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `MultimodalPerceptionEngine.__init__()` | Initializes a MultimodalPerceptionEngine instance. |
| 49 | `MultimodalPerceptionEngine.observe()` | Observes the current object. |
| 65 | `MultimodalPerceptionEngine._observe_serialized()` | Observes serialized. |
| 160 | `MultimodalPerceptionEngine.snapshot()` | Implements the snapshot operation for MultimodalPerceptionEngine. |
| 212 | `MultimodalPerceptionEngine._scope()` | Implements the scope operation for MultimodalPerceptionEngine. |

## `app/perception/fusion.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `PerceptionFusionEngine.fuse()` | Implements the fuse operation for PerceptionFusionEngine. |
| 16 | `PerceptionFusionEngine.fuse.pick()` | Implements the pick operation for PerceptionFusionEngine. |

## `app/perception/grounding.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `ScreenGroundingEngine.resolve()` | Resolves the current object. |
| 55 | `ScreenGroundingEngine.parse()` | Parses the current object. |
| 69 | `ScreenGroundingEngine._score()` | Implements the score operation for ScreenGroundingEngine. |
| 80 | `ScreenGroundingEngine._terms()` | Implements the terms operation for ScreenGroundingEngine. |
| 86 | `ScreenGroundingEngine._find_anchor()` | Finds anchor. |
| 92 | `ScreenGroundingEngine._reading_order()` | Implements the reading order operation for ScreenGroundingEngine. |
| 96 | `ScreenGroundingEngine._related()` | Implements the related operation for ScreenGroundingEngine. |

## `app/perception/models.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `WindowInfo.__post_init__()` | Validates or derives dataclass fields after initialization. |
| 55 | `UIElement.__post_init__()` | Validates or derives dataclass fields after initialization. |
| 82 | `PerceptionObservation.__post_init__()` | Validates or derives dataclass fields after initialization. |

## `app/perception/providers.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `VisualUnderstandingProvider.understand()` | Implements the understand operation for VisualUnderstandingProvider. |
| 16 | `SpeechRecognitionProvider.connect()` | Connects the current object. |
| 17 | `SpeechRecognitionProvider.stream_microphone()` | Implements the stream microphone operation for SpeechRecognitionProvider. |
| 18 | `SpeechRecognitionProvider.disconnect()` | Disconnects the current object. |
| 19 | `SpeechRecognitionProvider.health_check()` | Implements the health check operation for SpeechRecognitionProvider. |
| 24 | `SpeechOutputProvider.speak()` | Implements the speak operation for SpeechOutputProvider. |

## `app/perception/sources.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `PerceptionSource.observe()` | Observes the current object. |
| 28 | `ComputerControllerSource.__init__()` | Initializes a ComputerControllerSource instance. |
| 31 | `ComputerControllerSource.observe()` | Observes the current object. |
| 54 | `BrowserDOMSource.__init__()` | Initializes a BrowserDOMSource instance. |
| 57 | `BrowserDOMSource.observe()` | Observes the current object. |
| 84 | `FilesystemPerceptionSource.__init__()` | Initializes a FilesystemPerceptionSource instance. |
| 87 | `FilesystemPerceptionSource.observe()` | Observes the current object. |
| 106 | `DesktopWindowPerceptionSource.__init__()` | Initializes a DesktopWindowPerceptionSource instance. |
| 113 | `DesktopWindowPerceptionSource.available()` | Implements the available operation for DesktopWindowPerceptionSource. |
| 117 | `DesktopWindowPerceptionSource.observe()` | Observes the current object. |
| 120 | `DesktopWindowPerceptionSource._observe_sync()` | Observes sync. |

## `app/perception/user_guidance.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `RegionSelector.select()` | Selects the current object. |
| 32 | `DesktopRegionSelector.select()` | Selects the current object. |
| 51 | `DesktopRegionSelector.select.cancel()` | Cancels the current object. |
| 54 | `DesktopRegionSelector.select.pressed()` | Implements the pressed operation for DesktopRegionSelector. |
| 59 | `DesktopRegionSelector.select.dragged()` | Implements the dragged operation for DesktopRegionSelector. |
| 63 | `DesktopRegionSelector.select.released()` | Implements the released operation for DesktopRegionSelector. |
| 98 | `UserGuidancePerceptionSource.__init__()` | Initializes a UserGuidancePerceptionSource instance. |
| 107 | `UserGuidancePerceptionSource.available()` | Do not degrade unrelated observations before the owner provides a hint. |
| 112 | `UserGuidancePerceptionSource.select()` | Selects the current object. |
| 133 | `UserGuidancePerceptionSource.observe()` | Observes the current object. |

## `app/prompts/prompt_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `PromptManager.__init__()` | Initializes a PromptManager instance. |
| 10 | `PromptManager.render()` | Renders the current object. |

## `app/prompts/template_engine.py`

| Line | Function / method | Description |
|---:|---|---|
| 5 | `render_template()` | Renders template. |

## `app/providers/base_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `ChatbotProvider.__init__()` | Initializes a ChatbotProvider instance. |
| 54 | `ChatbotProvider.use_conversation_session()` | Pin reasoning to one project tab, with bounded chat-history rollover. |
| 70 | `ChatbotProvider.set_checkpoint_context()` | Keep bounded factual continuity for the next fresh conversation. |
| 79 | `ChatbotProvider.set_checkpoint_context.compact()` | Implements the compact operation for ChatbotProvider. |
| 107 | `ChatbotProvider.prepare_conversation()` | Use the pinned project conversation, or the exact prompt's tab. |
| 111 | `ChatbotProvider.open()` | Implements the open operation for ChatbotProvider. |
| 121 | `ChatbotProvider._maybe_rollover()` | Implements the maybe rollover operation for ChatbotProvider. |
| 140 | `ChatbotProvider.verify_page()` | Verifies page. |
| 153 | `ChatbotProvider.start_conversation()` | Focus the verified composer before the runtime sends a prompt. |
| 165 | `ChatbotProvider.send_prompt()` | Sends prompt. |
| 195 | `ChatbotProvider.remember_conversation()` | Save the canonical chat URL after the SPA has created a conversation. |
| 201 | `ChatbotProvider.wait_for_response()` | Waits for for response. |
| 214 | `ChatbotProvider.extract_response()` | Extracts response. |
| 237 | `ChatbotProvider.is_response_complete()` | Returns whether response complete. |
| 245 | `ChatbotProvider.recover()` | Implements the recover operation for ChatbotProvider. |
| 250 | `ChatbotProvider.recover_conversation()` | Recover an already submitted response without repeating the prompt. |
| 273 | `ChatbotProvider.copy_latest_response()` | Click a provider-declared response Copy control for clipboard fallback. |
| 280 | `ChatbotProvider._require_page()` | Requires page. |
| 285 | `ChatbotProvider._first_visible()` | Implements the first visible operation for ChatbotProvider. |
| 299 | `ChatbotProvider._wait_for_input()` | Wait for a client-rendered prompt composer without waiting forever. |
| 311 | `ChatbotProvider._input_not_found_message()` | Return actionable, credential-safe diagnostics for changed provider UIs. |
| 324 | `ChatbotProvider._response_count()` | Implements the response count operation for ChatbotProvider. |
| 327 | `ChatbotProvider._response_counts()` | Return per-selector counts so extraction can identify a newly added response. |
| 332 | `ChatbotProvider._latest_response()` | Return the response added after the current prompt, not prior chat history. |

## `app/providers/chatgpt.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `ChatGPTProvider.__init__()` | Initializes a ChatGPTProvider instance. |

## `app/providers/claude.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `ClaudeProvider.__init__()` | Initializes a ClaudeProvider instance. |

## `app/providers/collaborative.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `TeamStore.__init__()` | Initializes a TeamStore instance. |
| 55 | `TeamStore.close()` | Closes the current object. |
| 58 | `TeamStore.session()` | Implements the session operation for TeamStore. |
| 64 | `TeamStore.checkpoint()` | Implements the checkpoint operation for TeamStore. |
| 70 | `TeamStore.event()` | Implements the event operation for TeamStore. |
| 75 | `TeamStore.begin()` | Implements the begin operation for TeamStore. |
| 85 | `TeamStore.request()` | Implements the request operation for TeamStore. |
| 89 | `TeamStore.finish()` | Implements the finish operation for TeamStore. |
| 94 | `TeamStore.submission()` | Implements the submission operation for TeamStore. |
| 102 | `TeamStore.result()` | Implements the result operation for TeamStore. |
| 109 | `TeamStore.unresolved()` | An interrupted ask could have been submitted; restarting is not consent to replay. |
| 113 | `TeamStore.unresolved_rows()` | Implements the unresolved rows operation for TeamStore. |
| 121 | `TeamStore.latest()` | Implements the latest operation for TeamStore. |
| 126 | `TeamStore.member_states()` | Implements the member states operation for TeamStore. |
| 129 | `TeamStore.member_state()` | Implements the member state operation for TeamStore. |
| 135 | `_bounded_context()` | Implements the bounded context operation. |
| 139 | `_bounded_context.compact()` | Implements the compact operation. |
| 175 | `CollaborativeProvider.__init__()` | Initializes a CollaborativeProvider instance. |
| 236 | `CollaborativeProvider.use_conversation_session()` | Implements the use conversation session operation for CollaborativeProvider. |
| 268 | `CollaborativeProvider.set_checkpoint_context()` | Implements the set checkpoint context operation for CollaborativeProvider. |
| 278 | `CollaborativeProvider.prepare_conversation()` | Prepares conversation. |
| 281 | `CollaborativeProvider.open()` | Implements the open operation for CollaborativeProvider. |
| 291 | `CollaborativeProvider.verify_page()` | Verifies page. |
| 302 | `CollaborativeProvider.start_conversation()` | Starts conversation. |
| 305 | `CollaborativeProvider.send_prompt()` | Sends prompt. |
| 345 | `CollaborativeProvider.wait_for_response()` | Waits for for response. |
| 358 | `CollaborativeProvider.extract_response()` | Extracts response. |
| 372 | `CollaborativeProvider.remember_conversation()` | Stores conversation. |
| 375 | `CollaborativeProvider.recover_conversation()` | Implements the recover conversation operation for CollaborativeProvider. |
| 389 | `CollaborativeProvider.is_response_complete()` | Returns whether response complete. |
| 392 | `CollaborativeProvider._set_member_status()` | Implements the set member status operation for CollaborativeProvider. |
| 403 | `CollaborativeProvider._failure_reason()` | Implements the failure reason operation for CollaborativeProvider. |
| 416 | `CollaborativeProvider._probe_member()` | Implements the probe member operation for CollaborativeProvider. |
| 477 | `CollaborativeProvider.preflight()` | Implements the preflight operation for CollaborativeProvider. |
| 498 | `CollaborativeProvider.preflight.inspect()` | Implements the inspect operation for CollaborativeProvider. |
| 499 | `CollaborativeProvider.preflight.inspect.check()` | Checks the current object. |
| 529 | `CollaborativeProvider._recover_startup_member()` | Read one exact saved turn, even when it belongs to an earlier session. |
| 556 | `CollaborativeProvider._recover_round()` | Implements the recover round operation for CollaborativeProvider. |
| 593 | `CollaborativeProvider.recover_members()` | Observe a uniquely identified pending turn without submitting input. |
| 621 | `CollaborativeProvider.status_snapshot()` | Small read-only diagnostics suitable for CLI status and peer context. |
| 640 | `CollaborativeProvider._next_action()` | Implements the next action operation for CollaborativeProvider. |
| 658 | `CollaborativeProvider._bind_request()` | Implements the bind request operation for CollaborativeProvider. |
| 663 | `CollaborativeProvider._failure_summary()` | Implements the failure summary operation for CollaborativeProvider. |
| 667 | `CollaborativeProvider._peer_data()` | Implements the peer data operation for CollaborativeProvider. |
| 674 | `CollaborativeProvider._peer_data.size()` | Implements the size operation for CollaborativeProvider. |
| 712 | `CollaborativeProvider._prompt()` | Implements the prompt operation for CollaborativeProvider. |
| 735 | `CollaborativeProvider._ask_member()` | Implements the ask member operation for CollaborativeProvider. |
| 807 | `CollaborativeProvider._batch()` | Implements the batch operation for CollaborativeProvider. |
| 819 | `CollaborativeProvider._elect_leader()` | Implements the elect leader operation for CollaborativeProvider. |
| 833 | `CollaborativeProvider._repair_members()` | Website advice selects a finite runtime repair; it grants no authority. |
| 909 | `CollaborativeProvider._run()` | Runs the current object. |
| 992 | `CollaborativeProvider.close()` | Closes the current object. |

## `app/providers/gemini.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `GeminiProvider.__init__()` | Initializes a GeminiProvider instance. |

## `app/providers/json_response.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `unwrap_json_code_block()` | Remove only a complete valid JSON presentation block, never prose/code. |
| 23 | `decode_json_response()` | Implements the decode json response operation. |

## `app/providers/native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `NativeClientError.__init__()` | Initializes a NativeClientError instance. |
| 33 | `NativeSessionStore.__init__()` | Initializes a NativeSessionStore instance. |
| 42 | `NativeSessionStore.connect()` | Connects the current object. |
| 45 | `NativeSessionStore.get()` | Retrieves the current object. |
| 52 | `NativeSessionStore.save()` | Saves the current object. |
| 149 | `NativeWebsiteClient.__init__()` | Initializes a NativeWebsiteClient instance. |
| 190 | `NativeWebsiteClient.active_input_mode()` | Implements the active input mode operation for NativeWebsiteClient. |
| 194 | `NativeWebsiteClient.use_conversation_session()` | Implements the use conversation session operation for NativeWebsiteClient. |
| 208 | `NativeWebsiteClient.set_request_context()` | Correlate one coordinator round with its durable native receipt. |
| 216 | `NativeWebsiteClient.set_checkpoint_context()` | Implements the set checkpoint context operation for NativeWebsiteClient. |
| 222 | `NativeWebsiteClient._safe_url()` | Implements the safe url operation for NativeWebsiteClient. |
| 233 | `NativeWebsiteClient._action()` | Implements the action operation for NativeWebsiteClient. |
| 272 | `NativeWebsiteClient._probe_result()` | Implements the probe result operation for NativeWebsiteClient. |
| 277 | `NativeWebsiteClient._native_action()` | Implements the native action operation for NativeWebsiteClient. |
| 282 | `NativeWebsiteClient.probe()` | Inspect readiness without posting a prompt or clearing durable intent. |
| 310 | `NativeWebsiteClient._open()` | Implements the open operation for NativeWebsiteClient. |
| 331 | `NativeWebsiteClient._bind()` | Implements the bind operation for NativeWebsiteClient. |
| 344 | `NativeWebsiteClient.repair()` | Allowlisted recovery operations; peer text never becomes executable. |
| 370 | `NativeWebsiteClient._fresh_response()` | Implements the fresh response operation for NativeWebsiteClient. |
| 383 | `NativeWebsiteClient._wait_for_answer()` | Waits for for answer. |
| 431 | `NativeWebsiteClient.recover_response()` | Observe an unresolved submission without preparing or sending input. |
| 471 | `NativeWebsiteClient._prompt_with_checkpoint()` | Implements the prompt with checkpoint operation for NativeWebsiteClient. |
| 484 | `NativeWebsiteClient.ask()` | Implements the ask operation for NativeWebsiteClient. |
| 493 | `NativeWebsiteClient._ask_locked()` | Implements the ask locked operation for NativeWebsiteClient. |

## `app/providers/registry.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `ProviderRegistry.__init__()` | Initializes a ProviderRegistry instance. |
| 20 | `ProviderRegistry.from_settings()` | Implements the from settings operation for ProviderRegistry. |
| 25 | `ProviderRegistry.get()` | Retrieves the current object. |
| 32 | `ProviderRegistry.names()` | Implements the names operation for ProviderRegistry. |

## `app/providers/team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `validate_parts()` | Validates parts. |
| 49 | `validate_part_reply()` | Validates part reply. |
| 68 | `PartsCoordinator._plan_parts()` | Plans parts. |
| 110 | `PartsCoordinator._part_turn()` | Implements the part turn operation for PartsCoordinator. |
| 153 | `PartsCoordinator._parts_wave()` | Implements the parts wave operation for PartsCoordinator. |
| 165 | `PartsCoordinator._run_parts()` | Runs parts. |
| 258 | `PartsCoordinator._saved_completed_parts()` | Reuse exact-request proposals only after all old outcomes are known. |

## `app/runtime/action_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `ActionManager.__init__()` | Initializes a ActionManager instance. |
| 14 | `ActionManager.record()` | Records the current object. |

## `app/runtime/agent_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `AgentRuntime.__init__()` | Initializes a AgentRuntime instance. |
| 59 | `AgentRuntime.run()` | Runs the current object. |
| 102 | `AgentRuntime._run_provider()` | Runs provider. |
| 148 | `AgentRuntime._act()` | Implements the act operation for AgentRuntime. |
| 169 | `AgentRuntime._cancel_operation()` | Cancels operation. |
| 174 | `AgentRuntime._extract_response()` | Extracts response. |
| 197 | `AgentRuntime._recover_response()` | Reload, observe, and return to extraction after a bounded DOM retry. |
| 205 | `AgentRuntime._verify_provider()` | Verifies provider. |
| 215 | `AgentRuntime._observe()` | Refresh a page snapshot after navigation; observation failure never drives a blind action. |
| 222 | `AgentRuntime._capture()` | Best-effort evidence capture that does not replace the original provider error. |

## `app/runtime/guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `UserPrompt.ask()` | Implements the ask operation for UserPrompt. |
| 16 | `UserPrompt.confirm()` | Implements the confirm operation for UserPrompt. |
| 21 | `PopupUserPrompt.ask()` | Implements the ask operation for PopupUserPrompt. |
| 33 | `PopupUserPrompt.confirm()` | Implements the confirm operation for PopupUserPrompt. |
| 63 | `WorkflowStore.__init__()` | Initializes a WorkflowStore instance. |
| 66 | `WorkflowStore.recent()` | Implements the recent operation for WorkflowStore. |
| 72 | `WorkflowStore.save()` | Saves the current object. |
| 87 | `GuidedBrowserWorkflow.__init__()` | Initializes a GuidedBrowserWorkflow instance. |
| 93 | `GuidedBrowserWorkflow.supports()` | Implements the supports operation for GuidedBrowserWorkflow. |
| 97 | `GuidedBrowserWorkflow.run()` | Runs the current object. |
| 128 | `GuidedBrowserWorkflow._plan()` | Plans the current object. |
| 141 | `GuidedBrowserWorkflow.parse()` | Parses the current object. |
| 156 | `GuidedBrowserWorkflow._validate_url()` | Validates url. |

## `app/runtime/persistent_service.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `_now()` | Implements the now operation. |
| 27 | `_iso()` | Implements the iso operation. |
| 46 | `ServiceTask.snapshot()` | Implements the snapshot operation for ServiceTask. |
| 56 | `PersistentRuntimeStore.__init__()` | Initializes a PersistentRuntimeStore instance. |
| 114 | `PersistentRuntimeStore.close()` | Closes the current object. |
| 117 | `PersistentRuntimeStore.set_meta()` | Implements the set meta operation for PersistentRuntimeStore. |
| 125 | `PersistentRuntimeStore.meta()` | Implements the meta operation for PersistentRuntimeStore. |
| 131 | `PersistentRuntimeStore.request_stop()` | Implements the request stop operation for PersistentRuntimeStore. |
| 134 | `PersistentRuntimeStore.clear_stop()` | Clears stop. |
| 137 | `PersistentRuntimeStore.claim_runtime()` | Implements the claim runtime operation for PersistentRuntimeStore. |
| 147 | `PersistentRuntimeStore.submit()` | Submits the current object. |
| 174 | `PersistentRuntimeStore.claim()` | Implements the claim operation for PersistentRuntimeStore. |
| 191 | `PersistentRuntimeStore.get()` | Retrieves the current object. |
| 195 | `PersistentRuntimeStore.tasks()` | Implements the tasks operation for PersistentRuntimeStore. |
| 200 | `PersistentRuntimeStore.finish()` | Implements the finish operation for PersistentRuntimeStore. |
| 208 | `PersistentRuntimeStore.fail()` | Implements the fail operation for PersistentRuntimeStore. |
| 226 | `PersistentRuntimeStore.recover_interrupted()` | Implements the recover interrupted operation for PersistentRuntimeStore. |
| 235 | `PersistentRuntimeStore.upsert_agent()` | Implements the upsert agent operation for PersistentRuntimeStore. |
| 243 | `PersistentRuntimeStore.agents()` | Implements the agents operation for PersistentRuntimeStore. |
| 248 | `PersistentRuntimeStore.event()` | Implements the event operation for PersistentRuntimeStore. |
| 257 | `PersistentRuntimeStore.events()` | Implements the events operation for PersistentRuntimeStore. |
| 263 | `PersistentRuntimeStore._task()` | Implements the task operation for PersistentRuntimeStore. |
| 275 | `PersistentAgentRuntime.__init__()` | Initializes a PersistentAgentRuntime instance. |
| 300 | `PersistentAgentRuntime.submit()` | Submits the current object. |
| 310 | `PersistentAgentRuntime.stop()` | Stops the current object. |
| 315 | `PersistentAgentRuntime.snapshot()` | Implements the snapshot operation for PersistentAgentRuntime. |
| 336 | `PersistentAgentRuntime.run_forever()` | Runs forever. |
| 383 | `PersistentAgentRuntime.run_once()` | Process at most one task, preserving the same safety transitions. |
| 410 | `PersistentAgentRuntime._wait_for_work()` | Waits for for work. |
| 417 | `PersistentAgentRuntime._heartbeat_loop()` | Implements the heartbeat loop operation for PersistentAgentRuntime. |
| 424 | `service_health()` | Implements the service health operation. |
| 444 | `run_persistent_service()` | Runs persistent service. |
| 455 | `runtime_parser()` | Implements the runtime parser operation. |
| 468 | `run_runtime_cli()` | Runs runtime cli. |
| 507 | `run_runtime_cli.execute()` | Executes the current object. |
| 529 | `_status_snapshot()` | Implements the status snapshot operation. |

## `app/runtime/recovery_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `RecoveryManager.__init__()` | Initializes a RecoveryManager instance. |
| 14 | `RecoveryManager.run()` | Runs the current object. |

## `app/runtime/state_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `StateManager.__init__()` | Initializes a StateManager instance. |
| 21 | `StateManager.transition()` | Implements the transition operation for StateManager. |

## `app/runtime/task_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `TaskManager.__init__()` | Initializes a TaskManager instance. |
| 12 | `TaskManager.create()` | Creates the current object. |

## `app/safety/emergency_stop.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `EmergencyStop.__init__()` | Initializes a EmergencyStop instance. |
| 13 | `EmergencyStop.trigger()` | Implements the trigger operation for EmergencyStop. |
| 16 | `EmergencyStop.clear()` | Clears the current object. |
| 20 | `EmergencyStop.triggered()` | Implements the triggered operation for EmergencyStop. |
| 23 | `EmergencyStop.raise_if_triggered()` | Implements the raise if triggered operation for EmergencyStop. |

## `app/safety/intervention.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `UserInterventionGate.__init__()` | Initializes a UserInterventionGate instance. |
| 18 | `UserInterventionGate.continue_run()` | Implements the continue run operation for UserInterventionGate. |
| 21 | `UserInterventionGate.wait()` | Waits for the current object. |
| 32 | `ConsoleInterventionGate.wait()` | Waits for the current object. |

## `app/safety/leases.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `CapabilityLease.active()` | Implements the active operation for CapabilityLease. |
| 26 | `CapabilityLeaseRegistry.__init__()` | Initializes a CapabilityLeaseRegistry instance. |
| 30 | `CapabilityLeaseRegistry.grant()` | Implements the grant operation for CapabilityLeaseRegistry. |
| 39 | `CapabilityLeaseRegistry.permits()` | Implements the permits operation for CapabilityLeaseRegistry. |
| 45 | `CapabilityLeaseRegistry.active()` | Implements the active operation for CapabilityLeaseRegistry. |
| 50 | `CapabilityLeaseRegistry.revoke()` | Implements the revoke operation for CapabilityLeaseRegistry. |
| 54 | `CapabilityLeaseRegistry._prune()` | Implements the prune operation for CapabilityLeaseRegistry. |

## `app/safety/pause.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `PauseController.__init__()` | Initializes a PauseController instance. |
| 13 | `PauseController.pause()` | Pauses the current object. |
| 16 | `PauseController.resume()` | Resumes the current object. |
| 20 | `PauseController.paused()` | Implements the paused operation for PauseController. |
| 23 | `PauseController.wait_until_resumed()` | Waits for until resumed. |

## `app/safety/permissions.py`

| Line | Function / method | Description |
|---:|---|---|
| 44 | `PermissionDenied.__init__()` | Initializes a PermissionDenied instance. |
| 55 | `PermissionPolicy.__init__()` | Initializes a PermissionPolicy instance. |
| 59 | `PermissionPolicy.approve_once()` | Runtime-only one-shot approval consumed by the next policy check. |
| 63 | `PermissionPolicy.check()` | Checks the current object. |

## `app/safety/redaction.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `redact()` | Redacts the current object. |

## `app/tasks/task_parser.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `parse_task()` | Parses task. |
| 27 | `_classify_category()` | Choose a prompt profile using explicit, stable keyword groups. |

## `app/voice/config.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `VoiceConfig.from_env()` | Implements the from env operation for VoiceConfig. |
| 35 | `VoiceConfig.from_env.value()` | Implements the value operation for VoiceConfig. |
| 56 | `VoiceConfig.validate()` | Validates the current object. |

## `app/voice/controller.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `VoiceControlPlane.__init__()` | Initializes a VoiceControlPlane instance. |
| 21 | `VoiceControlPlane.configure()` | Implements the configure operation for VoiceControlPlane. |
| 59 | `VoiceControlPlane.configure_config()` | Install validated trusted startup configuration without exposing its key. |
| 66 | `VoiceControlPlane.start()` | Starts the current object. |
| 84 | `VoiceControlPlane.stop()` | Stops the current object. |
| 94 | `VoiceControlPlane._listener_finished()` | Implements the listener finished operation for VoiceControlPlane. |
| 98 | `VoiceControlPlane.health_check()` | Implements the health check operation for VoiceControlPlane. |
| 101 | `VoiceControlPlane.snapshot()` | Implements the snapshot operation for VoiceControlPlane. |

## `app/voice/intent.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `VoiceIntentEngine.parse()` | Parses the current object. |

## `app/voice/service.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `StreamingTransport.connect()` | Connects the current object. |
| 22 | `StreamingTransport.stream_microphone()` | Implements the stream microphone operation for StreamingTransport. |
| 23 | `StreamingTransport.disconnect()` | Disconnects the current object. |
| 24 | `StreamingTransport.health_check()` | Implements the health check operation for StreamingTransport. |
| 29 | `AssemblyAIStreamingTransport.__init__()` | Initializes a AssemblyAIStreamingTransport instance. |
| 32 | `AssemblyAIStreamingTransport.connect()` | Connects the current object. |
| 36 | `AssemblyAIStreamingTransport.connect.receive_turn()` | Implements the receive turn operation for AssemblyAIStreamingTransport. |
| 52 | `AssemblyAIStreamingTransport.stream_microphone()` | Implements the stream microphone operation for AssemblyAIStreamingTransport. |
| 58 | `AssemblyAIStreamingTransport.disconnect()` | Disconnects the current object. |
| 66 | `AssemblyAIStreamingTransport.health_check()` | Implements the health check operation for AssemblyAIStreamingTransport. |
| 75 | `VoiceRuntimeRouter.__init__()` | Initializes a VoiceRuntimeRouter instance. |
| 81 | `VoiceRuntimeRouter.route()` | Implements the route operation for VoiceRuntimeRouter. |
| 133 | `VoiceService.__init__()` | Initializes a VoiceService instance. |
| 145 | `VoiceService.start()` | Starts the current object. |
| 161 | `VoiceService.listen()` | Implements the listen operation for VoiceService. |
| 182 | `VoiceService.stop()` | Stops the current object. |
| 196 | `VoiceService.pause()` | Pauses the current object. |
| 200 | `VoiceService.resume()` | Resumes the current object. |
| 205 | `VoiceService.health_check()` | Implements the health check operation for VoiceService. |
| 209 | `VoiceService._on_turn()` | Implements the on turn operation for VoiceService. |
| 212 | `VoiceService._on_error()` | Implements the on error operation for VoiceService. |
| 215 | `VoiceService.process_turn()` | Processes turn. |
| 247 | `VoiceService._connect_with_backoff()` | Connects with backoff. |
| 258 | `VoiceService.snapshot()` | Implements the snapshot operation for VoiceService. |

## `app/voice/store.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `VoiceMetadataStore.__init__()` | Initializes a VoiceMetadataStore instance. |
| 14 | `VoiceMetadataStore.append()` | Implements the append operation for VoiceMetadataStore. |
| 24 | `VoiceMetadataStore.all()` | Implements the all operation for VoiceMetadataStore. |

## `executor.py`

| Line | Function / method | Description |
|---:|---|---|
| 94 | `timestamp()` | Implements the timestamp operation. |
| 98 | `screenshot_name()` | Implements the screenshot name operation. |
| 104 | `save_screenshot()` | Saves screenshot. |
| 111 | `normalize_url()` | Handles accidental Markdown links such as: |
| 158 | `ComputerController.__init__()` | Initializes a ComputerController instance. |
| 165 | `ComputerController.open_application()` | Implements the open application operation for ComputerController. |
| 199 | `ComputerController.close_application()` | Closes application. |
| 218 | `ComputerController.is_application_running()` | Returns whether application running. |
| 244 | `ComputerController.navigate()` | Implements the navigate operation for ComputerController. |
| 257 | `ComputerController.get_current_url()` | Retrieves current url. |
| 260 | `ComputerController.wait_for_page()` | Waits for for page. |
| 267 | `ComputerController.click()` | Implements the click operation for ComputerController. |
| 275 | `ComputerController.double_click()` | Implements the double click operation for ComputerController. |
| 278 | `ComputerController.drag()` | Implements the drag operation for ComputerController. |
| 282 | `ComputerController.scroll()` | Implements the scroll operation for ComputerController. |
| 289 | `ComputerController.type_text()` | Implements the type text operation for ComputerController. |
| 292 | `ComputerController.press_key()` | Implements the press key operation for ComputerController. |
| 295 | `ComputerController.hotkey()` | Implements the hotkey operation for ComputerController. |
| 302 | `ComputerController.copy()` | Implements the copy operation for ComputerController. |
| 305 | `ComputerController.paste()` | Implements the paste operation for ComputerController. |
| 312 | `ComputerController.screenshot()` | Implements the screenshot operation for ComputerController. |
| 329 | `TargetResolver.__init__()` | Initializes a TargetResolver instance. |
| 332 | `TargetResolver.resolve()` | Resolves the current object. |
| 399 | `TaskExecutor.__init__()` | Initializes a TaskExecutor instance. |
| 412 | `TaskExecutor.validate_task()` | Validates task. |
| 448 | `TaskExecutor.check_permission()` | Checks permission. |
| 472 | `TaskExecutor.execute()` | Executes the current object. |
| 507 | `TaskExecutor.execute_step()` | Executes step. |
| 597 | `TaskExecutor.execute_action()` | Executes action. |
| 632 | `TaskExecutor.action_open_application()` | Implements the action open application operation for TaskExecutor. |
| 640 | `TaskExecutor.action_close_application()` | Implements the action close application operation for TaskExecutor. |
| 645 | `TaskExecutor.action_navigate()` | Implements the action navigate operation for TaskExecutor. |
| 650 | `TaskExecutor.action_wait()` | Implements the action wait operation for TaskExecutor. |
| 658 | `TaskExecutor.action_click()` | Implements the action click operation for TaskExecutor. |
| 684 | `TaskExecutor.action_double_click()` | Implements the action double click operation for TaskExecutor. |
| 695 | `TaskExecutor.action_type()` | Implements the action type operation for TaskExecutor. |
| 703 | `TaskExecutor.action_press_key()` | Implements the action press key operation for TaskExecutor. |
| 713 | `TaskExecutor.action_hotkey()` | Implements the action hotkey operation for TaskExecutor. |
| 723 | `TaskExecutor.action_scroll()` | Implements the action scroll operation for TaskExecutor. |
| 728 | `TaskExecutor.action_drag()` | Implements the action drag operation for TaskExecutor. |
| 743 | `TaskExecutor.action_select()` | Implements the action select operation for TaskExecutor. |
| 748 | `TaskExecutor.action_inspect()` | Implements the action inspect operation for TaskExecutor. |
| 776 | `TaskExecutor.action_screenshot()` | Implements the action screenshot operation for TaskExecutor. |
| 786 | `TaskExecutor.action_copy()` | Implements the action copy operation for TaskExecutor. |
| 789 | `TaskExecutor.action_paste()` | Implements the action paste operation for TaskExecutor. |
| 796 | `TaskExecutor.verify_step()` | Verifies step. |
| 865 | `TaskExecutor.final_verification()` | Implements the final verification operation for TaskExecutor. |
| 918 | `TaskExecutor.recover()` | Implements the recover operation for TaskExecutor. |
| 944 | `TaskExecutor.log_step()` | Implements the log step operation for TaskExecutor. |
| 973 | `TaskExecutor.generate_result()` | Generates result. |
| 1025 | `load_task()` | Loads task. |
| 1044 | `main()` | Implements the main operation. |

## `run.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `restore_saved_conversations()` | Restores saved conversations. |
| 59 | `process_prompt_files()` | Processes prompt files. |
| 87 | `ensure_root_agent()` | Ensures root agent. |
| 99 | `print_catalog()` | Implements the print catalog operation. |
| 106 | `run_catalog()` | Runs catalog. |
| 125 | `ask_chatgpt_for_blender_plan()` | Implements the ask chatgpt for blender plan operation. |
| 139 | `_is_generic_youtube_request()` | Return whether a YouTube request names no song, artist, or search term. |
| 152 | `prepare_youtube_request()` | Open YouTube Music and collect a concrete playback request from the user. |
| 173 | `run_agent_session()` | Runs agent session. |
| 241 | `run_agent_session.model_executor()` | Implements the model executor operation. |
| 242 | `run_agent_session.model_executor.execute()` | Executes the current object. |
| 321 | `run_agent_session.executor()` | Implements the executor operation. |
| 343 | `main()` | Implements the main operation. |
| 367 | `main.execute_with_team()` | Executes with team. |
| 379 | `main.execute_desktop_with_team()` | Executes desktop with team. |
| 389 | `main.execute_local_mission()` | Executes local mission. |
| 395 | `main.execute_local_mission.ask_youtube()` | Implements the ask youtube operation. |

## `run_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `dashboard_token()` | Return a configured token or a cryptographically random per-run token. |
| 47 | `_pump()` | Implements the pump operation. |
| 54 | `_tick_triggers()` | Implements the tick triggers operation. |
| 60 | `serve()` | Implements the serve operation. |
| 89 | `serve.runner()` | Implements the runner operation. |
| 94 | `serve.create_voice()` | Creates voice. |
| 147 | `main()` | Implements the main operation. |

## `scripts/demo_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `FakeRegistry.__init__()` | Initializes a FakeRegistry instance. |
| 20 | `FakeRegistry.register()` | Registers the current object. |
| 24 | `FakeRegistry.agents()` | Implements the agents operation for FakeRegistry. |
| 25 | `FakeRegistry.capabilities_for()` | Implements the capabilities for operation for FakeRegistry. |
| 26 | `FakeRegistry.available()` | Implements the available operation for FakeRegistry. |
| 28 | `FakeRegistry.find()` | Finds the current object. |
| 36 | `FakeProvider.__init__()` | Initializes a FakeProvider instance. |
| 40 | `FakeProvider.prepare_conversation()` | Prepares conversation. |
| 43 | `FakeProvider.open()` | Implements the open operation for FakeProvider. |
| 46 | `FakeProvider.verify_page()` | Verifies page. |
| 49 | `FakeProvider.start_conversation()` | Starts conversation. |
| 52 | `FakeProvider.send_prompt()` | Sends prompt. |
| 55 | `FakeProvider.wait_for_response()` | Waits for for response. |
| 58 | `FakeProvider.remember_conversation()` | Stores conversation. |
| 61 | `FakeProvider.extract_response()` | Extracts response. |
| 65 | `setup_runtime()` | Implements the setup runtime operation. |
| 77 | `definition()` | Implements the definition operation. |
| 84 | `main()` | Implements the main operation. |

## `scripts/demo_search.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `FixedDecisionProvider.__init__()` | Initializes a FixedDecisionProvider instance. |
| 22 | `FixedDecisionProvider.next_action()` | Implements the next action operation for FixedDecisionProvider. |
| 28 | `main()` | Implements the main operation. |
| 92 | `main.executor()` | Implements the executor operation. |

## `scripts/diagnose_native_input.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `main()` | Implements the main operation. |
| 28 | `main.inspect()` | Implements the inspect operation. |
| 41 | `main.focus()` | Implements the focus operation. |
| 58 | `main.focus.evidence()` | Implements the evidence operation. |

## Tests

These functions are test cases or test helpers; test cases are described by the scenario named in the test function.

## `tests/test_accessibility_scripts.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `test_accessibility_scripts_have_valid_powershell_syntax()` | Tests the accessibility scripts have valid powershell syntax scenario. |

## `tests/test_action_and_safety.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `test_action_manager_enforces_limit()` | Tests the action manager enforces limit scenario. |

## `tests/test_action_and_safety.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `test_emergency_stop_latch_can_be_triggered_and_cleared()` | Tests the emergency stop latch can be triggered and cleared scenario. |

## `tests/test_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `manager_with_tool()` | Implements the manager with tool operation. |

## `tests/test_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `test_definition_creates_a_bounded_auditable_agent()` | Tests the definition creates a bounded auditable agent scenario. |

## `tests/test_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `test_function_and_schema_fail_closed()` | Tests the function and schema fail closed scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `build_manager()` | Builds manager. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `test_end_to_end_child_tool_permissions_and_result_collection()` | Tests the end to end child tool permissions and result collection scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `test_end_to_end_child_tool_permissions_and_result_collection.scenario()` | Implements the scenario operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `test_end_to_end_child_tool_permissions_and_result_collection.scenario.work()` | Implements the work operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 54 | `test_hierarchy_task_assignment_and_permission_escalation_are_controlled()` | Tests the hierarchy task assignment and permission escalation are controlled scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 66 | `test_parent_can_grant_and_revoke_only_its_own_child_permissions()` | Tests the parent can grant and revoke only its own child permissions scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 77 | `test_policy_requires_human_approval_before_high_risk_tool_execution()` | Tests the policy requires human approval before high risk tool execution scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 78 | `test_policy_requires_human_approval_before_high_risk_tool_execution.scenario()` | Implements the scenario operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 84 | `test_policy_requires_human_approval_before_high_risk_tool_execution.scenario.work()` | Implements the work operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 96 | `test_parallel_children_retry_and_termination()` | Tests the parallel children retry and termination scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 97 | `test_parallel_children_retry_and_termination.scenario()` | Implements the scenario operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 102 | `test_parallel_children_retry_and_termination.scenario.parallel_work()` | Implements the parallel work operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 111 | `test_parallel_children_retry_and_termination.scenario.flaky()` | Implements the flaky operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 127 | `test_agent_snapshots_and_permission_denials_are_persisted()` | Tests the agent snapshots and permission denials are persisted scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 140 | `test_runtime_filesystem_tool_is_permission_gated_and_repository_scoped()` | Tests the runtime filesystem tool is permission gated and repository scoped scenario. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 141 | `test_runtime_filesystem_tool_is_permission_gated_and_repository_scoped.scenario()` | Implements the scenario operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 149 | `test_runtime_filesystem_tool_is_permission_gated_and_repository_scoped.scenario.work()` | Implements the work operation. |

## `tests/test_agent_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 155 | `test_runtime_filesystem_tool_is_permission_gated_and_repository_scoped.scenario.unsafe()` | Implements the unsafe operation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `FakeRegistry.__init__()` | Initializes a FakeRegistry instance. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `FakeRegistry.register()` | Registers the current object. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `FakeRegistry.agents()` | Implements the agents operation for FakeRegistry. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `FakeRegistry.capabilities_for()` | Implements the capabilities for operation for FakeRegistry. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `FakeRegistry.available()` | Implements the available operation for FakeRegistry. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `FakeRegistry.find()` | Finds the current object. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `FakeProvider.__init__()` | Initializes a FakeProvider instance. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `FakeProvider.prepare_conversation()` | Prepares conversation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `FakeProvider.open()` | Implements the open operation for FakeProvider. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 37 | `FakeProvider.verify_page()` | Verifies page. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `FakeProvider.start_conversation()` | Starts conversation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `FakeProvider.send_prompt()` | Sends prompt. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `FakeProvider.wait_for_response()` | Waits for for response. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `FakeProvider.remember_conversation()` | Implements the remember conversation operation for FakeProvider. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 42 | `FakeProvider.extract_response()` | Extracts response. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `setup_runtime()` | Implements the setup runtime operation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `definition()` | Implements the definition operation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 64 | `selection()` | Implements the selection operation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 71 | `test_prompt1_reuses_an_authoritatively_eligible_agent()` | Tests the prompt1 reuses an authoritatively eligible agent scenario. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 72 | `test_prompt1_reuses_an_authoritatively_eligible_agent.scenario()` | Implements the scenario operation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `test_prompt2_creates_and_runs_only_a_validated_definition_artifact()` | Tests the prompt2 creates and runs only a validated definition artifact scenario. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 91 | `test_prompt2_creates_and_runs_only_a_validated_definition_artifact.scenario()` | Implements the scenario operation. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 112 | `test_object_extractor_handles_markdown_and_leading_text()` | Tests the object extractor handles markdown and leading text scenario. |

## `tests/test_agent_planning_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 119 | `test_object_extractor_handles_single_quoted_python_dicts()` | Tests the object extractor handles single quoted python dicts scenario. |

## `tests/test_automation_catalog.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `test_catalog_contains_exactly_one_hundred_automations()` | Tests the catalog contains exactly one hundred automations scenario. |

## `tests/test_automation_catalog.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `test_catalog_covers_video_blender_and_unreal()` | Tests the catalog covers video blender and unreal scenario. |

## `tests/test_automation_catalog.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `test_reasoning_prompt_contains_only_catalog_metadata()` | Tests the reasoning prompt contains only catalog metadata scenario. |

## `tests/test_automation_catalog.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `test_catalog_runner_executes_registered_tools_sequentially()` | Tests the catalog runner executes registered tools sequentially scenario. |

## `tests/test_automation_catalog.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `test_catalog_runner_executes_registered_tools_sequentially.handler()` | Implements the handler operation. |

## `tests/test_automation_catalog.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `test_catalog_runner_reports_missing_tools_and_inputs()` | Tests the catalog runner reports missing tools and inputs scenario. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `Controller.__init__()` | Initializes a Controller instance. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `Controller.observe()` | Observes the current object. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `build()` | Builds the current object. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `test_persistent_mission_observes_runs_verifies_and_restores_after_restart()` | Tests the persistent mission observes runs verifies and restores after restart scenario. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `test_persistent_mission_observes_runs_verifies_and_restores_after_restart.runner()` | Implements the runner operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `test_persistent_mission_observes_runs_verifies_and_restores_after_restart.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `test_takeover_pauses_actions_then_resume_reobserves_and_continues()` | Tests the takeover pauses actions then resume reobserves and continues scenario. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `test_takeover_pauses_actions_then_resume_reobserves_and_continues.runner()` | Implements the runner operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `test_takeover_pauses_actions_then_resume_reobserves_and_continues.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 53 | `test_event_bus_and_blockers_update_mission_without_reasoning_calls()` | Tests the event bus and blockers update mission without reasoning calls scenario. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 54 | `test_event_bus_and_blockers_update_mission_without_reasoning_calls.runner()` | Implements the runner operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 55 | `test_event_bus_and_blockers_update_mission_without_reasoning_calls.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 66 | `test_explicitly_paused_mission_never_runs_or_observes_until_resumed()` | Tests the explicitly paused mission never runs or observes until resumed scenario. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `test_explicitly_paused_mission_never_runs_or_observes_until_resumed.runner()` | Implements the runner operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 71 | `test_explicitly_paused_mission_never_runs_or_observes_until_resumed.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 86 | `test_operator_dispatches_events_to_runtime_trigger_handlers()` | Tests the operator dispatches events to runtime trigger handlers scenario. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 88 | `test_operator_dispatches_events_to_runtime_trigger_handlers.runner()` | Implements the runner operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 89 | `test_operator_dispatches_events_to_runtime_trigger_handlers.handler()` | Implements the handler operation. |

## `tests/test_autonomous_operator.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `test_operator_dispatches_events_to_runtime_trigger_handlers.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `LocalComputer.__init__()` | Initializes a LocalComputer instance. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `LocalComputer.observe()` | Observes the current object. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 27 | `LocalComputer.execute()` | Executes the current object. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `BrowserDecision.next_action()` | Implements the next action operation for BrowserDecision. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 46 | `test_end_to_end_dynamic_creation_reuse_and_controlled_permission()` | Tests the end to end dynamic creation reuse and controlled permission scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 47 | `test_end_to_end_dynamic_creation_reuse_and_controlled_permission.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 67 | `test_end_to_end_dynamic_creation_reuse_and_controlled_permission.scenario.forbidden()` | Implements the forbidden operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 76 | `test_end_to_end_dynamic_creation_reuse_and_controlled_permission.scenario.allowed()` | Implements the allowed operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 85 | `test_document_requirements_are_minimal_and_factory_rejects_parent_escalation()` | Tests the document requirements are minimal and factory rejects parent escalation scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 93 | `Noop.test_document_requirements_are_minimal_and_factory_rejects_parent_escalation.next_action()` | Implements the next action operation for Noop. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 98 | `test_document_agent_writes_and_verifies_a_real_file()` | Tests the document agent writes and verifies a real file scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 100 | `DocumentDecision.test_document_agent_writes_and_verifies_a_real_file.__init__()` | Initializes a DocumentDecision instance. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 101 | `DocumentDecision.test_document_agent_writes_and_verifies_a_real_file.next_action()` | Implements the next action operation for DocumentDecision. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 109 | `test_document_agent_writes_and_verifies_a_real_file.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 120 | `test_runtime_requires_registry_and_can_resume_after_explicit_approval()` | Tests the runtime requires registry and can resume after explicit approval scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 121 | `test_runtime_requires_registry_and_can_resume_after_explicit_approval.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 130 | `test_runtime_requires_registry_and_can_resume_after_explicit_approval.scenario.work()` | Implements the work operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 146 | `test_action_audit_is_persisted_with_safe_runtime_metadata()` | Tests the action audit is persisted with safe runtime metadata scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 147 | `test_action_audit_is_persisted_with_safe_runtime_metadata.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 155 | `test_action_audit_is_persisted_with_safe_runtime_metadata.scenario.work()` | Implements the work operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 171 | `test_goal_engine_creates_agent_writes_real_file_checkpoints_and_verifies_outcome()` | Tests the goal engine creates agent writes real file checkpoints and verifies outcome scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 173 | `WriteDecision.test_goal_engine_creates_agent_writes_real_file_checkpoints_and_verifies_outcome.__init__()` | Initializes a WriteDecision instance. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 174 | `WriteDecision.test_goal_engine_creates_agent_writes_real_file_checkpoints_and_verifies_outcome.next_action()` | Implements the next action operation for WriteDecision. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 182 | `FileCriterion.test_goal_engine_creates_agent_writes_real_file_checkpoints_and_verifies_outcome.verify()` | Verifies the current object. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 186 | `test_goal_engine_creates_agent_writes_real_file_checkpoints_and_verifies_outcome.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 203 | `test_closed_loop_recovery_replans_after_a_real_filesystem_failure()` | Tests the closed loop recovery replans after a real filesystem failure scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 205 | `RecoveringDecision.test_closed_loop_recovery_replans_after_a_real_filesystem_failure.__init__()` | Initializes a RecoveringDecision instance. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 206 | `RecoveringDecision.test_closed_loop_recovery_replans_after_a_real_filesystem_failure.next_action()` | Implements the next action operation for RecoveringDecision. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 216 | `test_closed_loop_recovery_replans_after_a_real_filesystem_failure.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 228 | `test_task_engine_learns_then_reuses_a_verified_workflow_through_runtime_gates()` | The second execution uses a persisted skill, not a task-name branch. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 235 | `FileCriterion.test_task_engine_learns_then_reuses_a_verified_workflow_through_runtime_gates.verify()` | Verifies the current object. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 240 | `WriteDecision.test_task_engine_learns_then_reuses_a_verified_workflow_through_runtime_gates.__init__()` | Initializes a WriteDecision instance. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 241 | `WriteDecision.test_task_engine_learns_then_reuses_a_verified_workflow_through_runtime_gates.next_action()` | Implements the next action operation for WriteDecision. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 246 | `test_task_engine_learns_then_reuses_a_verified_workflow_through_runtime_gates.graph()` | Implements the graph operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 253 | `test_task_engine_learns_then_reuses_a_verified_workflow_through_runtime_gates.scenario()` | Implements the scenario operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 274 | `test_task_engine_learns_then_reuses_a_verified_workflow_through_runtime_gates.scenario.reused_decider()` | Implements the reused decider operation. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 289 | `test_action_results_audit_and_events_redact_secret_values()` | Tests the action results audit and events redact secret values scenario. |

## `tests/test_autonomous_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 290 | `test_action_results_audit_and_events_redact_secret_values.scenario()` | Implements the scenario operation. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `MovingUi.__init__()` | Initializes a MovingUi instance. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `MovingUi.observe()` | Observes the current object. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `MovingUi.execute()` | Executes the current object. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `test_world_state_marks_old_facts_stale_and_diffs_observations()` | Tests the world state marks old facts stale and diffs observations scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `test_action_contract_requires_observed_precondition_then_verifies_real_ui_transition()` | Tests the action contract requires observed precondition then verifies real ui transition scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `test_action_contract_requires_observed_precondition_then_verifies_real_ui_transition.scenario()` | Implements the scenario operation. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `test_action_contract_requires_observed_precondition_then_verifies_real_ui_transition.scenario.work()` | Implements the work operation. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `test_task_graph_scheduler_dependencies_conflicts_and_replanning()` | Tests the task graph scheduler dependencies conflicts and replanning scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_recovery_never_blindly_retries_non_idempotent_unverified_action()` | Tests the recovery never blindly retries non idempotent unverified action scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `test_target_resolution_and_atomic_checkpoint_roundtrip()` | Tests the target resolution and atomic checkpoint roundtrip scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 79 | `test_graph_goal_executes_dependencies_and_verifies_real_filesystem_result()` | Tests the graph goal executes dependencies and verifies real filesystem result scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 84 | `Criterion.test_graph_goal_executes_dependencies_and_verifies_real_filesystem_result.verify()` | Verifies the current object. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 89 | `Write.test_graph_goal_executes_dependencies_and_verifies_real_filesystem_result.__init__()` | Initializes a Write instance. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `Write.test_graph_goal_executes_dependencies_and_verifies_real_filesystem_result.next_action()` | Implements the next action operation for Write. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 96 | `test_graph_goal_executes_dependencies_and_verifies_real_filesystem_result.scenario()` | Implements the scenario operation. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 108 | `test_action_audit_redacts_secret_values()` | Tests the action audit redacts secret values scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 109 | `test_action_audit_redacts_secret_values.scenario()` | Implements the scenario operation. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 114 | `test_action_audit_redacts_secret_values.scenario.work()` | Implements the work operation. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 122 | `test_graph_checkpoint_is_updated_and_resume_forces_new_observation()` | Tests the graph checkpoint is updated and resume forces new observation scenario. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 129 | `Criterion.test_graph_checkpoint_is_updated_and_resume_forces_new_observation.verify()` | Verifies the current object. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 131 | `Decision.test_graph_checkpoint_is_updated_and_resume_forces_new_observation.__init__()` | Initializes a Decision instance. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 132 | `Decision.test_graph_checkpoint_is_updated_and_resume_forces_new_observation.next_action()` | Implements the next action operation for Decision. |

## `tests/test_autonomy_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 137 | `test_graph_checkpoint_is_updated_and_resume_forces_new_observation.scenario()` | Implements the scenario operation. |

## `tests/test_blender_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `test_blender_adapter_executes_structured_operations_and_verifies_output()` | Tests the blender adapter executes structured operations and verifies output scenario. |

## `tests/test_blender_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `test_blender_adapter_executes_structured_operations_and_verifies_output.invoke()` | Implements the invoke operation. |

## `tests/test_blender_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `test_blender_adapter_rejects_code_and_reports_missing_output()` | Tests the blender adapter rejects code and reports missing output scenario. |

## `tests/test_blender_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 44 | `test_blender_adapter_rejects_code_and_reports_missing_output.invoke()` | Implements the invoke operation. |

## `tests/test_blender_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `test_generic_plan_accepts_structured_steps_and_preserves_arguments()` | Tests the generic plan accepts structured steps and preserves arguments scenario. |

## `tests/test_blender_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `test_plan_rejects_code_unknown_operations_and_bad_start()` | Tests the plan rejects code unknown operations and bad start scenario. |

## `tests/test_blender_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `test_camera_and_light_do_not_require_scale()` | Tests the camera and light do not require scale scenario. |

## `tests/test_blender_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `test_large_scene_plan_is_supported_within_safe_limit()` | Tests the large scene plan is supported within safe limit scenario. |

## `tests/test_blender_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `test_large_plan_is_split_without_repeating_scene_creation()` | Tests the large plan is split without repeating scene creation scenario. |

## `tests/test_blender_planner.py`

| Line | Function / method | Description |
|---:|---|---|
| 88 | `test_plan_batches_keep_material_with_its_created_object()` | Tests the plan batches keep material with its created object scenario. |

## `tests/test_blender_workflows.py`

| Line | Function / method | Description |
|---:|---|---|
| 5 | `test_car_workflow_contains_complete_consecutive_operations()` | Tests the car workflow contains complete consecutive operations scenario. |

## `tests/test_blender_workflows.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `test_car_workflow_arguments_are_structured_not_shell_commands()` | Tests the car workflow arguments are structured not shell commands scenario. |

## `tests/test_blender_workflows.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `test_car_scripts_include_expected_scene_parts()` | Tests the car scripts include expected scene parts scenario. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `FakePage.__init__()` | Initializes a FakePage instance. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `FakePage.goto()` | Implements the goto operation for FakePage. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `FakePage.bring_to_front()` | Implements the bring to front operation for FakePage. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `FakePage.is_closed()` | Returns whether closed. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `FakeContext.__init__()` | Initializes a FakeContext instance. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `FakeContext.pages()` | Implements the pages operation for FakeContext. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `FakeContext.new_page()` | Implements the new page operation for FakeContext. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `manager()` | Implements the manager operation. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 46 | `test_each_prompt_gets_a_dedicated_tab_and_is_reused_in_process()` | Tests the each prompt gets a dedicated tab and is reused in process scenario. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `test_saved_chat_url_is_restored_without_storing_prompt()` | Tests the saved chat url is restored without storing prompt scenario. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 75 | `test_off_origin_saved_url_is_ignored()` | Tests the off origin saved url is ignored scenario. |

## `tests/test_browser_conversations.py`

| Line | Function / method | Description |
|---:|---|---|
| 86 | `test_project_reasoning_and_retries_use_one_tab()` | Tests the project reasoning and retries use one tab scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `FakeTransport.__init__()` | Initializes a FakeTransport instance. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `FakeTransport.launch()` | Implements the launch operation for FakeTransport. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `FakeTransport.navigate()` | Implements the navigate operation for FakeTransport. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 51 | `FakeTransport.close()` | Closes the current object. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 59 | `inventory()` | Implements the inventory operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `fleet()` | Implements the fleet operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 74 | `test_known_signed_out_profiles_never_launch_and_partial_profile_keeps_eligible_provider()` | Tests the known signed out profiles never launch and partial profile keeps eligible provider scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `test_managed_chromium_leads_without_native_profiles_and_is_closed()` | Tests the managed chromium leads without native profiles and is closed scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 94 | `Leader.test_managed_chromium_leads_without_native_profiles_and_is_closed.__init__()` | Initializes a Leader instance. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 96 | `Leader.test_managed_chromium_leads_without_native_profiles_and_is_closed.start()` | Starts the current object. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 99 | `Leader.test_managed_chromium_leads_without_native_profiles_and_is_closed.close()` | Closes the current object. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 112 | `test_signed_in_app_chrome_profile_is_leader_without_duplicate_or_isolated_launch()` | Tests the signed in app chrome profile is leader without duplicate or isolated launch scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 120 | `test_signed_in_app_chrome_profile_is_leader_without_duplicate_or_isolated_launch.forbidden()` | Implements the forbidden operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 142 | `test_chrome_profile_leader_uses_its_own_signin_cache()` | Tests the chrome profile leader uses its own signin cache scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 157 | `test_failed_leader_does_not_prevent_native_peers_starting()` | Tests the failed leader does not prevent native peers starting scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 159 | `Leader.test_failed_leader_does_not_prevent_native_peers_starting.__init__()` | Initializes a Leader instance. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 161 | `Leader.test_failed_leader_does_not_prevent_native_peers_starting.start()` | Starts the current object. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 163 | `Leader.test_failed_leader_does_not_prevent_native_peers_starting.close()` | Closes the current object. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 176 | `test_opens_both_providers_once_for_each_unique_profile()` | Tests the opens both providers once for each unique profile scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 197 | `test_partial_window_is_closed_before_retry_and_success_clears_failure()` | Tests the partial window is closed before retry and success clears failure scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 212 | `test_later_start_retries_failed_profile_while_preserving_healthy_clients()` | Tests the later start retries failed profile while preserving healthy clients scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 228 | `test_failed_cleanup_blocks_duplicate_launch_until_close_succeeds()` | Tests the failed cleanup blocks duplicate launch until close succeeds scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 248 | `test_uncertain_launch_is_not_repeated_and_other_profiles_continue()` | Tests the uncertain launch is not repeated and other profiles continue scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 263 | `test_close_retains_failed_window_for_cleanup_and_can_restart_afterwards()` | Tests the close retains failed window for cleanup and can restart afterwards scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 283 | `test_cancelled_launch_waits_for_owned_handle_and_closes_window()` | Tests the cancelled launch waits for owned handle and closes window scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 301 | `test_cancelled_navigation_cleans_partial_window()` | Tests the cancelled navigation cleans partial window scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 314 | `test_client_construction_failure_does_not_publish_half_profile()` | Tests the client construction failure does not publish half profile scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 319 | `test_client_construction_failure_does_not_publish_half_profile.client()` | Implements the client operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 333 | `test_missing_installation_is_reported_without_stopping_other_profiles()` | Tests the missing installation is reported without stopping other profiles scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 346 | `test_empty_inventory_needs_no_desktop_backend()` | Tests the empty inventory needs no desktop backend scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 347 | `test_empty_inventory_needs_no_desktop_backend.unexpected_backend()` | Implements the unexpected backend operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 358 | `test_launch_retries_are_bounded()` | Tests the launch retries are bounded scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 364 | `test_definitely_unstarted_process_is_retried_within_budget()` | Tests the definitely unstarted process is retried within budget scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 369 | `test_definitely_unstarted_process_is_retried_within_budget.transient_launch()` | Implements the transient launch operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 386 | `test_permanent_spawn_failure_stops_at_attempt_budget()` | Tests the permanent spawn failure stops at attempt budget scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 390 | `test_permanent_spawn_failure_stops_at_attempt_budget.unavailable()` | Implements the unavailable operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 404 | `test_late_window_is_adopted_without_relaunch()` | Tests the late window is adopted without relaunch scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 410 | `test_late_window_is_adopted_without_relaunch.recover()` | Implements the recover operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 431 | `test_recovery_probe_failure_keeps_launch_uncertain()` | Tests the recovery probe failure keeps launch uncertain scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 435 | `test_recovery_probe_failure_keeps_launch_uncertain.unavailable()` | Implements the unavailable operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 447 | `test_closed_window_is_rebuilt_and_healthy_profile_is_preserved()` | Tests the closed window is rebuilt and healthy profile is preserved scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 450 | `test_closed_window_is_rebuilt_and_healthy_profile_is_preserved.alive()` | Implements the alive operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 453 | `test_closed_window_is_rebuilt_and_healthy_profile_is_preserved.close()` | Closes the current object. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 469 | `test_failed_health_inspection_neither_closes_nor_duplicates_window()` | Tests the failed health inspection neither closes nor duplicates window scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 473 | `test_failed_health_inspection_neither_closes_nor_duplicates_window.alive()` | Implements the alive operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 498 | `test_cancelled_late_adoption_closes_the_owned_window()` | Tests the cancelled late adoption closes the owned window scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 503 | `test_cancelled_late_adoption_closes_the_owned_window.recover()` | Implements the recover operation. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 527 | `test_invalid_configuration_fails_before_creating_runtime_data()` | Tests the invalid configuration fails before creating runtime data scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 534 | `test_repeated_cancel_does_not_abandon_launch_or_cleanup()` | Tests the repeated cancel does not abandon launch or cleanup scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 552 | `test_cancelled_close_commits_cleanup_and_allows_restart()` | Tests the cancelled close commits cleanup and allows restart scenario. |

## `tests/test_browser_fleet.py`

| Line | Function / method | Description |
|---:|---|---|
| 559 | `test_cancelled_close_commits_cleanup_and_allows_restart.slow_close()` | Implements the slow close operation. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `test_managed_leader_matches_chrome_last_used_profile_not_another_browser()` | Tests the managed leader matches chrome last used profile not another browser scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `environment()` | Implements the environment operation. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `touch()` | Implements the touch operation. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 49 | `chrome()` | Implements the chrome operation. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `discover()` | Discovers the current object. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_installed_browsers_and_real_profiles_are_read_only_metadata()` | Tests the installed browsers and real profiles are read only metadata scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 75 | `test_installed_browsers_and_real_profiles_are_read_only_metadata.track_open()` | Implements the track open operation. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 95 | `test_registry_and_known_path_and_path_lookup_candidates_are_deduplicated()` | Tests the registry and known path and path lookup candidates are deduplicated scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 106 | `test_registry_path_expansion_and_case_insensitive_environment()` | Tests the registry path expansion and case insensitive environment scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 116 | `test_path_can_discover_nonstandard_installation()` | Tests the path can discover nonstandard installation scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 126 | `test_corrupt_local_state_falls_back_to_existing_directories()` | Tests the corrupt local state falls back to existing directories scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 134 | `test_locked_local_state_is_warning_and_directory_discovery_continues()` | Tests the locked local state is warning and directory discovery continues scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 138 | `test_locked_local_state_is_warning_and_directory_discovery_continues.locked()` | Implements the locked operation. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 149 | `test_metadata_paths_cannot_escape_profile_root()` | Tests the metadata paths cannot escape profile root scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 162 | `test_firefox_relative_absolute_and_aliased_profiles()` | Tests the firefox relative absolute and aliased profiles scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 183 | `test_firefox_corrupt_and_invalid_relative_entries_are_reported()` | Tests the firefox corrupt and invalid relative entries are reported scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 200 | `test_all_supported_browser_roots_and_legacy_opera()` | Tests the all supported browser roots and legacy opera scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 224 | `test_optional_managed_profile_keeps_separate_root_and_stable_identity()` | Tests the optional managed profile keeps separate root and stable identity scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 237 | `test_missing_browsers_or_uninitialized_profiles_are_not_created()` | Tests the missing browsers or uninitialized profiles are not created scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 248 | `test_chromium_launch_preserves_profile_and_opens_one_visible_window()` | Tests the chromium launch preserves profile and opens one visible window scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 262 | `test_firefox_launch_selects_exact_profile_and_one_window()` | Tests the firefox launch selects exact profile and one window scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 271 | `test_launch_rejects_non_web_urls_and_flags()` | Tests the launch rejects non web urls and flags scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 278 | `test_launch_rejects_a_profile_from_another_installation()` | Tests the launch rejects a profile from another installation scenario. |

## `tests/test_browser_inventory.py`

| Line | Function / method | Description |
|---:|---|---|
| 287 | `test_native_owner_marker_is_allowed_but_other_data_pages_are_rejected()` | Tests the native owner marker is allowed but other data pages are rejected scenario. |

## `tests/test_browser_supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `test_supervisor_retries_with_persisted_backoff()` | Tests the supervisor retries with persisted backoff scenario. |

## `tests/test_browser_supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `test_supervisor_retries_with_persisted_backoff.runner()` | Implements the runner operation. |

## `tests/test_browser_supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `test_supervisor_retries_with_persisted_backoff.status_reader()` | Implements the status reader operation. |

## `tests/test_browser_supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `test_uncertain_browser_submission_is_never_replayed()` | Tests the uncertain browser submission is never replayed scenario. |

## `tests/test_browser_supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `test_uncertain_browser_submission_is_never_replayed.runner()` | Implements the runner operation. |

## `tests/test_browser_supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `test_uncertain_browser_submission_is_never_replayed.status_reader()` | Implements the status reader operation. |

## `tests/test_browser_supervisor.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `test_supervisor_waits_without_busy_loop()` | Tests the supervisor waits without busy loop scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `inventory()` | Implements the inventory operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `Member.__init__()` | Initializes a Member instance. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `Member.ask()` | Implements the ask operation for Member. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `Fleet.__init__()` | Initializes a Fleet instance. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `Fleet.start()` | Starts the current object. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `Fleet.close()` | Closes the current object. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `test_inventory_and_status_never_create_a_fleet_or_database()` | Tests the inventory and status never create a fleet or database scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 46 | `test_inventory_and_status_never_create_a_fleet_or_database.forbidden()` | Implements the forbidden operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 61 | `test_cli_drives_real_peer_exchange_and_saved_status()` | Tests the cli drives real peer exchange and saved status scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 80 | `test_open_keeps_windows_and_never_sends_a_prompt()` | Tests the open keeps windows and never sends a prompt scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `test_run_excludes_only_confirmed_signouts_before_launch()` | Tests the run excludes only confirmed signouts before launch scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 100 | `test_run_excludes_only_confirmed_signouts_before_launch.checked_start()` | Implements the checked start operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 111 | `test_no_profiles_does_not_initialize_desktop()` | Tests the no profiles does not initialize desktop scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 112 | `test_no_profiles_does_not_initialize_desktop.forbidden()` | Implements the forbidden operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 120 | `test_cli_enables_managed_leader_with_no_native_profiles()` | Tests the cli enables managed leader with no native profiles scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 123 | `test_cli_enables_managed_leader_with_no_native_profiles.factory()` | Implements the factory operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 133 | `test_leader_only_rejects_profile_selection()` | Tests the leader only rejects profile selection scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 141 | `test_default_leader_keeps_signed_in_app_profile_and_open_window()` | Tests the default leader keeps signed in app profile and open window scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 150 | `test_default_leader_keeps_signed_in_app_profile_and_open_window.factory()` | Implements the factory operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 153 | `test_default_leader_keeps_signed_in_app_profile_and_open_window.forbidden_close()` | Implements the forbidden close operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 164 | `test_recover_reads_prior_reply_without_asking_again()` | Tests the recover reads prior reply without asking again scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 172 | `test_recover_reads_prior_reply_without_asking_again.recover()` | Implements the recover operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 186 | `test_status_includes_blocked_possibly_submitted_turns()` | Tests the status includes blocked possibly submitted turns scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 200 | `test_recovery_reports_unresolved_profile_even_when_it_could_not_launch()` | Tests the recovery reports unresolved profile even when it could not launch scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 220 | `test_invalid_limits_are_rejected_before_discovery()` | Tests the invalid limits are rejected before discovery scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 221 | `test_invalid_limits_are_rejected_before_discovery.forbidden()` | Implements the forbidden operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 228 | `test_failed_execution_reports_pause_and_closes_owned_windows()` | Tests the failed execution reports pause and closes owned windows scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 231 | `test_failed_execution_reports_pause_and_closes_owned_windows.execute()` | Executes the current object. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 242 | `test_run_entrypoint_injects_team_without_starting_playwright()` | Tests the run entrypoint injects team without starting playwright scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 247 | `test_run_entrypoint_injects_team_without_starting_playwright.close()` | Closes the current object. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 249 | `test_run_entrypoint_injects_team_without_starting_playwright.application()` | Implements the application operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 252 | `test_run_entrypoint_injects_team_without_starting_playwright.session()` | Implements the session operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 255 | `test_run_entrypoint_injects_team_without_starting_playwright.cli()` | Implements the cli operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 267 | `test_doctor_only_probes_and_writes_health_report()` | Tests the doctor only probes and writes health report scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 269 | `test_doctor_only_probes_and_writes_health_report.probe()` | Implements the probe operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 283 | `test_doctor_does_not_claim_readiness_without_probe_support()` | Tests the doctor does not claim readiness without probe support scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 292 | `test_fleet_failure_is_saved_and_status_can_read_it_without_a_team_database()` | Tests the fleet failure is saved and status can read it without a team database scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 303 | `test_fleet_failure_is_saved_and_status_can_read_it_without_a_team_database.forbidden()` | Implements the forbidden operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 314 | `test_doctor_reports_partial_fleet_even_when_available_members_are_ready()` | Tests the doctor reports partial fleet even when available members are ready scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 317 | `test_doctor_reports_partial_fleet_even_when_available_members_are_ready.probe()` | Implements the probe operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 331 | `test_corrupt_last_fleet_report_does_not_break_readonly_status()` | Tests the corrupt last fleet report does not break readonly status scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 341 | `test_report_write_failure_does_not_hide_successful_fleet_start()` | Tests the report write failure does not hide successful fleet start scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 345 | `test_report_write_failure_does_not_hide_successful_fleet_start.unavailable()` | Implements the unavailable operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 356 | `test_unknown_profile_cannot_open_any_window()` | Tests the unknown profile cannot open any window scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 363 | `test_desktop_route_passes_budgets_and_returns_blocked_without_false_success()` | Tests the desktop route passes budgets and returns blocked without false success scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 366 | `test_desktop_route_passes_budgets_and_returns_blocked_without_false_success.execute()` | Executes the current object. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 378 | `test_normal_startup_routes_to_browser_team_not_managed_chromium()` | Tests the normal startup routes to browser team not managed chromium scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 382 | `test_normal_startup_routes_to_browser_team_not_managed_chromium.cli()` | Implements the cli operation. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 392 | `test_outer_default_and_cli_launch_maintained_project()` | Tests the outer default and cli launch maintained project scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 408 | `test_gui_team_worker_does_not_call_legacy_runtime()` | Tests the gui team worker does not call legacy runtime scenario. |

## `tests/test_browser_team_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 412 | `test_gui_team_worker_does_not_call_legacy_runtime.cli()` | Implements the cli operation. |

## `tests/test_capability_broker.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `broker()` | Implements the broker operation. |

## `tests/test_capability_broker.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `test_video_goal_detects_real_local_gap_and_builds_safe_discovery_mission()` | Tests the video goal detects real local gap and builds safe discovery mission scenario. |

## `tests/test_capability_broker.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `test_broker_prefers_compatible_local_agent_before_discovery()` | Tests the broker prefers compatible local agent before discovery scenario. |

## `tests/test_capability_broker.py`

| Line | Function / method | Description |
|---:|---|---|
| 49 | `test_blender_creation_language_routes_to_blender_capability()` | Tests the blender creation language routes to blender capability scenario. |

## `tests/test_capability_broker.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `test_dashboard_pauses_unsupported_goal_and_starts_constrained_discovery()` | Tests the dashboard pauses unsupported goal and starts constrained discovery scenario. |

## `tests/test_capability_broker.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `test_dashboard_pauses_unsupported_goal_and_starts_constrained_discovery.scenario()` | Implements the scenario operation. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `FakeProvider.__init__()` | Initializes a FakeProvider instance. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `FakeProvider.open()` | Implements the open operation for FakeProvider. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `FakeProvider.verify_page()` | Verifies page. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `FakeProvider.start_conversation()` | Starts conversation. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `FakeProvider.send_prompt()` | Sends prompt. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `FakeProvider.wait_for_response()` | Waits for for response. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `FakeProvider.extract_response()` | Extracts response. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `context()` | Implements the context operation. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `test_website_metadata_is_converted_to_a_candidate_without_executing_code()` | Tests the website metadata is converted to a candidate without executing code scenario. |

## `tests/test_capability_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_website_cannot_select_unregistered_builder_or_change_tool_identity()` | Tests the website cannot select unregistered builder or change tool identity scenario. |

## `tests/test_capability_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `candidate()` | Implements the candidate operation. |

## `tests/test_capability_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `test_capability_lifecycle_validates_stages_promotes_and_rolls_back()` | Tests the capability lifecycle validates stages promotes and rolls back scenario. |

## `tests/test_capability_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `test_capability_lifecycle_validates_stages_promotes_and_rolls_back.build()` | Builds the current object. |

## `tests/test_capability_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 56 | `test_untrusted_candidate_is_rejected_and_never_registered()` | Tests the untrusted candidate is rejected and never registered scenario. |

## `tests/test_capability_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `test_failed_health_check_cannot_be_promoted()` | Tests the failed health check cannot be promoted scenario. |

## `tests/test_capability_skilling.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `plan()` | Plans the current object. |

## `tests/test_capability_skilling.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `test_missing_worker_is_explicitly_blocked()` | Tests the missing worker is explicitly blocked scenario. |

## `tests/test_capability_skilling.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `test_only_successful_bounded_validation_promotes_skill()` | Tests the only successful bounded validation promotes skill scenario. |

## `tests/test_capability_skilling.py`

| Line | Function / method | Description |
|---:|---|---|
| 47 | `_ok()` | Implements the ok operation. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `Page.__init__()` | Initializes a Page instance. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `Page.is_closed()` | Returns whether closed. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `Page.goto()` | Implements the goto operation for Page. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `Page.evaluate()` | Evaluates the current object. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `Driver.__init__()` | Initializes a Driver instance. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `Driver.start()` | Starts the current object. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `Driver.launch_persistent_context()` | Implements the launch persistent context operation for Driver. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 50 | `Driver.new_page()` | Implements the new page operation for Driver. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 55 | `Driver.close()` | Closes the current object. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `Driver.stop()` | Stops the current object. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 63 | `test_signed_out_leader_provider_is_not_opened()` | Tests the signed out leader provider is not opened scenario. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 78 | `test_managed_leader_pins_two_website_tabs_in_an_isolated_profile()` | Tests the managed leader pins two website tabs in an isolated profile scenario. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 95 | `test_managed_transport_rejects_code_and_cross_provider_navigation()` | Tests the managed transport rejects code and cross provider navigation scenario. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 109 | `test_managed_transport_preserves_submission_certainty()` | Tests the managed transport preserves submission certainty scenario. |

## `tests/test_chromium_leader.py`

| Line | Function / method | Description |
|---:|---|---|
| 121 | `test_cancelled_managed_launch_waits_for_context_and_closes_it()` | Tests the cancelled managed launch waits for context and closes it scenario. |

## `tests/test_cli_output.py`

| Line | Function / method | Description |
|---:|---|---|
| 4 | `test_cli_result_is_explicitly_advisory()` | Tests the cli result is explicitly advisory scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `Client.__init__()` | Initializes a Client instance. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `Client.use_conversation_session()` | Implements the use conversation session operation for Client. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `Client.set_checkpoint_context()` | Implements the set checkpoint context operation for Client. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `Client.set_request_context()` | Implements the set request context operation for Client. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `Client.ask()` | Implements the ask operation for Client. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `ask()` | Implements the ask operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 51 | `provider()` | Implements the provider operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 56 | `test_chromium_leader_synthesizes_even_if_native_peer_is_listed_first()` | Tests the chromium leader synthesizes even if native peer is listed first scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 69 | `test_failed_leader_yields_to_ready_peer()` | Tests the failed leader yields to ready peer scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 88 | `test_website_advice_can_only_invoke_a_registered_verified_repair()` | Tests the website advice can only invoke a registered verified repair scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 93 | `test_website_advice_can_only_invoke_a_registered_verified_repair.probe()` | Implements the probe operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 95 | `test_website_advice_can_only_invoke_a_registered_verified_repair.repair()` | Implements the repair operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 113 | `test_peer_repair_never_replays_unknown_submission()` | Tests the peer repair never replays unknown submission scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 116 | `test_peer_repair_never_replays_unknown_submission.repair()` | Implements the repair operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 129 | `test_peer_repair_budget_stops_diagnosis_loop()` | Tests the peer repair budget stops diagnosis loop scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 132 | `test_peer_repair_budget_stops_diagnosis_loop.probe()` | Implements the probe operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 134 | `test_peer_repair_budget_stops_diagnosis_loop.repair()` | Implements the repair operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 148 | `test_repair_claim_requires_an_independent_successful_probe()` | Tests the repair claim requires an independent successful probe scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 151 | `test_repair_claim_requires_an_independent_successful_probe.probe()` | Implements the probe operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 153 | `test_repair_claim_requires_an_independent_successful_probe.repair()` | Implements the repair operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 165 | `test_peers_exchange_and_final_schema_is_preserved()` | Tests the peers exchange and final schema is preserved scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 188 | `test_one_member_is_used_without_redundant_peer_loops()` | Tests the one member is used without redundant peer loops scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 197 | `test_login_member_is_blocked_and_others_diagnose()` | Tests the login member is blocked and others diagnose scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 209 | `test_timeout_is_never_replayed_and_is_persisted()` | Tests the timeout is never replayed and is persisted scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 210 | `test_timeout_is_never_replayed_and_is_persisted.delay()` | Implements the delay operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 226 | `test_only_explicit_unsubmitted_error_retries_once_after_diagnosis()` | Tests the only explicit unsubmitted error retries once after diagnosis scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 240 | `test_ambiguous_provider_error_is_not_retried()` | Tests the ambiguous provider error is not retried scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 253 | `test_permission_denial_propagates()` | Tests the permission denial propagates scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 263 | `test_rate_limit_not_retried_even_with_false_submission_flag()` | Tests the rate limit not retried even with false submission flag scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 277 | `test_pending_session_guard_and_recovery_does_not_resend()` | Tests the pending session guard and recovery does not resend scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 280 | `test_pending_session_guard_and_recovery_does_not_resend.delayed()` | Implements the delayed operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 306 | `test_crash_submission_intent_blocks_replay_and_complete_answer_recovers()` | Tests the crash submission intent blocks replay and complete answer recovers scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 321 | `test_completed_response_recovers_after_restart()` | Tests the completed response recovers after restart scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 334 | `test_checkpoint_is_bounded_and_prompt_size_rejected_before_input()` | Tests the checkpoint is bounded and prompt size rejected before input scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 346 | `test_default_checkpoint_restores_and_reaches_participants()` | Tests the default checkpoint restores and reaches participants scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 359 | `test_completed_answer_recovers_even_when_all_members_are_quarantined()` | Tests the completed answer recovers even when all members are quarantined scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 377 | `test_extracted_answer_is_not_resurrected_by_recovery()` | Tests the extracted answer is not resurrected by recovery scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 389 | `test_prompt_budget_preserves_original_with_unicode_and_many_peers()` | Tests the prompt budget preserves original with unicode and many peers scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 409 | `test_native_prompt_limit_is_validated_before_any_member_input()` | Tests the native prompt limit is validated before any member input scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 421 | `test_safe_retries_are_bounded_when_every_peer_fails_before_submission()` | Tests the safe retries are bounded when every peer fails before submission scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 422 | `test_safe_retries_are_bounded_when_every_peer_fails_before_submission.rejected()` | Implements the rejected operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 443 | `test_cancellation_quarantines_only_members_that_started_input()` | Tests the cancellation quarantines only members that started input scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 446 | `test_cancellation_quarantines_only_members_that_started_input.never_finishes()` | Implements the never finishes operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 464 | `test_member_recovery_confirms_only_saved_round_without_returning_new_answer()` | Tests the member recovery confirms only saved round without returning new answer scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 473 | `test_member_recovery_confirms_only_saved_round_without_returning_new_answer.recover()` | Implements the recover operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 498 | `test_startup_recovers_exact_old_session_without_submitting_or_replaying()` | Tests the startup recovers exact old session without submitting or replaying scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 508 | `test_startup_recovers_exact_old_session_without_submitting_or_replaying.recover()` | Implements the recover operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 530 | `test_native_readiness_waits_for_desktop_lane_before_starting_probe()` | Tests the native readiness waits for desktop lane before starting probe scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 532 | `test_native_readiness_waits_for_desktop_lane_before_starting_probe.probe()` | Implements the probe operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 552 | `test_member_recovery_leaves_ambiguous_and_cross_session_turns_untouched()` | Tests the member recovery leaves ambiguous and cross session turns untouched scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 560 | `test_member_recovery_leaves_ambiguous_and_cross_session_turns_untouched.unexpected_recovery()` | Implements the unexpected recovery operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 574 | `test_incomplete_recovery_never_clears_quarantine()` | Tests the incomplete recovery never clears quarantine scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 581 | `test_incomplete_recovery_never_clears_quarantine.recover()` | Implements the recover operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 596 | `test_authentication_failure_preserves_submission_certainty_across_restart()` | Tests the authentication failure preserves submission certainty across restart scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 612 | `test_certified_unsubmitted_synthesis_retries_once_with_same_round_identity()` | Tests the certified unsubmitted synthesis retries once with same round identity scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 625 | `test_pending_peer_stays_in_original_chat_while_healthy_peer_switches_project()` | Tests the pending peer stays in original chat while healthy peer switches project scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 632 | `test_pending_peer_stays_in_original_chat_while_healthy_peer_switches_project.keep_pending_chat()` | Implements the keep pending chat operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 652 | `ProbedClient.__init__()` | Initializes a ProbedClient instance. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 657 | `ProbedClient.probe()` | Implements the probe operation for ProbedClient. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 666 | `test_timed_out_turn_is_recovered_automatically_without_resubmission()` | Tests the timed out turn is recovered automatically without resubmission scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 667 | `test_timed_out_turn_is_recovered_automatically_without_resubmission.timeout()` | Implements the timeout operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 673 | `test_timed_out_turn_is_recovered_automatically_without_resubmission.recover()` | Implements the recover operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 689 | `test_automatic_recovery_timeout_is_bounded_and_never_sends_again()` | Tests the automatic recovery timeout is bounded and never sends again scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 693 | `test_automatic_recovery_timeout_is_bounded_and_never_sends_again.recover()` | Implements the recover operation. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 709 | `test_preflight_loading_retries_are_finite_and_dont_submit()` | Tests the preflight loading retries are finite and dont submit scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 724 | `test_preflight_pending_receipt_is_quarantined_across_restart()` | Tests the preflight pending receipt is quarantined across restart scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 746 | `test_uncertain_console_intervention_is_not_retried_as_page_loading()` | Tests the uncertain console intervention is not retried as page loading scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 764 | `test_explicit_console_setup_health_rejoins_after_setup_is_completed()` | Tests the explicit console setup health rejoins after setup is completed scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 779 | `test_preflight_recovers_loading_without_dropping_failure_diagnostics()` | Tests the preflight recovers loading without dropping failure diagnostics scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 795 | `test_preflight_rejoins_after_owner_finishes_authentication()` | Tests the preflight rejoins after owner finishes authentication scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 809 | `test_unsubmitted_authentication_block_survives_restart_then_rejoins()` | Tests the unsubmitted authentication block survives restart then rejoins scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 823 | `test_ready_probe_never_clears_ambiguous_submission()` | Tests the ready probe never clears ambiguous submission scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 837 | `test_rate_limit_remains_blocked_across_readiness_checks_and_restart()` | Tests the rate limit remains blocked across readiness checks and restart scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 853 | `test_unsigned_member_stays_skipped_until_next_preflight()` | Tests the unsigned member stays skipped until next preflight scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 869 | `test_preflight_permission_denial_is_persisted_and_not_retried()` | Tests the preflight permission denial is persisted and not retried scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 881 | `test_second_request_probes_again_after_consuming_first_answer()` | Tests the second request probes again after consuming first answer scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 893 | `test_rate_limit_can_rejoin_after_cooldown_by_read_only_probe()` | Tests the rate limit can rejoin after cooldown by read only probe scenario. |

## `tests/test_collaborative_provider.py`

| Line | Function / method | Description |
|---:|---|---|
| 909 | `test_explicit_rate_limit_recheck_sends_no_prompt()` | Tests the explicit rate limit recheck sends no prompt scenario. |

## `tests/test_computer_controls.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `FakeMouse.__init__()` | Initializes a FakeMouse instance. |

## `tests/test_computer_controls.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `FakeMouse.click()` | Implements the click operation for FakeMouse. |

## `tests/test_computer_controls.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `FakeKeyboard.__init__()` | Initializes a FakeKeyboard instance. |

## `tests/test_computer_controls.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `FakeKeyboard.write()` | Writes the current object. |

## `tests/test_computer_controls.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `FakeKeyboard.hotkey()` | Implements the hotkey operation for FakeKeyboard. |

## `tests/test_computer_controls.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `test_mouse_and_keyboard_delegate_to_injected_backends()` | Tests the mouse and keyboard delegate to injected backends scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `example()` | Implements the example operation. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `test_neighbours_share_exact_contract_and_context()` | Tests the neighbours share exact contract and context scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `test_footprints_attachments_and_corridors()` | Tests the footprints attachments and corridors scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `test_starter_layout_fits_every_district()` | Tests the starter layout fits every district scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 66 | `test_border_error_identifies_object_and_center_limits()` | Tests the border error identifies object and center limits scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 77 | `test_object_resume_retains_area_plans_and_polish()` | Tests the object resume retains area plans and polish scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 79 | `test_object_resume_retains_area_plans_and_polish.ask()` | Implements the ask operation. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 100 | `test_object_resume_retains_area_plans_and_polish.execute()` | Executes the current object. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 142 | `test_real_connected_objects()` | Tests the real connected objects scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 178 | `test_planning_recovery_and_explicit_pause()` | Tests the planning recovery and explicit pause scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 181 | `test_planning_recovery_and_explicit_pause.malformed()` | Implements the malformed operation. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 190 | `test_planning_recovery_and_explicit_pause.paused()` | Implements the paused operation. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 199 | `test_component_contract_rejects_wrong_phase_and_object()` | Tests the component contract rejects wrong phase and object scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 211 | `test_legacy_migration_and_render_budget_recovery()` | Tests the legacy migration and render budget recovery scenario. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 236 | `test_legacy_migration_and_render_budget_recovery.ask()` | Implements the ask operation. |

## `tests/test_connected_village.py`

| Line | Function / method | Description |
|---:|---|---|
| 246 | `test_legacy_migration_and_render_budget_recovery.execute()` | Executes the current object. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `Response.__init__()` | Initializes a Response instance. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `Response.count()` | Counts the current object. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `Response.nth()` | Implements the nth operation for Response. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `Response.is_visible()` | Returns whether visible. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `Response.is_enabled()` | Returns whether enabled. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 27 | `Response.inner_text()` | Implements the inner text operation for Response. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `Page.__init__()` | Initializes a Page instance. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `Page.goto()` | Implements the goto operation for Page. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 42 | `Page.bring_to_front()` | Implements the bring to front operation for Page. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `Page.is_closed()` | Returns whether closed. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `Page.close()` | Closes the current object. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 51 | `Page.reload()` | Implements the reload operation for Page. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 54 | `Page.locator()` | Implements the locator operation for Page. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `Context.__init__()` | Initializes a Context instance. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 65 | `Context.pages()` | Implements the pages operation for Context. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `Context.new_page()` | Implements the new page operation for Context. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 75 | `setup()` | Implements the setup operation. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 88 | `complete_turn()` | Implements the complete turn operation. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 95 | `test_rollover_closes_only_owned_project_tab_and_preserves_resume_mapping()` | Tests the rollover closes only owned project tab and preserves resume mapping scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 128 | `test_pending_response_cannot_roll_over_or_submit_twice()` | Tests the pending response cannot roll over or submit twice scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 144 | `test_recovery_reload_extracts_new_answer_without_resubmission()` | Tests the recovery reload extracts new answer without resubmission scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 159 | `test_uncertain_submission_cannot_be_automatically_replayed()` | Tests the uncertain submission cannot be automatically replayed scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 172 | `test_recovery_does_not_treat_old_answer_as_current_or_open_blank_chat()` | Tests the recovery does not treat old answer as current or open blank chat scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 188 | `test_rollover_and_recovery_require_manual_security_intervention()` | Tests the rollover and recovery require manual security intervention scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 203 | `test_project_switch_reuses_owned_tab_resets_counters_and_restores_right_url()` | Tests the project switch reuses owned tab resets counters and restores right url scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 225 | `test_checkpoint_context_is_bounded_valid_json_with_recent_evidence()` | Tests the checkpoint context is bounded valid json with recent evidence scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 236 | `test_character_limit_rolls_over_after_a_complete_answer()` | Tests the character limit rolls over after a complete answer scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 247 | `test_slow_composer_rolls_over_only_after_answer_is_complete()` | Tests the slow composer rolls over only after answer is complete scenario. |

## `tests/test_conversation_rollover.py`

| Line | Function / method | Description |
|---:|---|---|
| 263 | `test_workflow_recovers_response_without_replaying_submission()` | Tests the workflow recovers response without replaying submission scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `dashboard()` | Implements the dashboard operation. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `dashboard.runner()` | Implements the runner operation. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `test_dashboard_snapshot_uses_real_runtime_state_and_redacts_secrets()` | Tests the dashboard snapshot uses real runtime state and redacts secrets scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 46 | `test_dashboard_commands_require_authorization_and_emit_correlated_event()` | Tests the dashboard commands require authorization and emit correlated event scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `test_dashboard_http_api_auth_static_load_and_replay()` | Tests the dashboard http api auth static load and replay scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 81 | `test_dashboard_http_snapshot_reads_sqlite_stores_created_on_runtime_thread()` | Tests the dashboard http snapshot reads sqlite stores created on runtime thread scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 105 | `test_dashboard_event_history_survives_gateway_restart()` | Tests the dashboard event history survives gateway restart scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 119 | `test_authorized_create_mission_uses_operator_and_validates_input()` | Tests the authorized create mission uses operator and validates input scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 130 | `test_analytics_use_real_denominators_and_report_unavailable_without_data()` | Tests the analytics use real denominators and report unavailable without data scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 140 | `test_dashboard_approval_decision_flows_through_durable_runtime_authority()` | Tests the dashboard approval decision flows through durable runtime authority scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 145 | `test_dashboard_approval_decision_flows_through_durable_runtime_authority.scenario()` | Implements the scenario operation. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 165 | `test_dashboard_correlates_agents_actions_and_events_to_authoritative_mission()` | Tests the dashboard correlates agents actions and events to authoritative mission scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 188 | `test_dashboard_screen_guidance_is_authenticated_and_flows_to_perception()` | Tests the dashboard screen guidance is authenticated and flows to perception scenario. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 192 | `Guidance.test_dashboard_screen_guidance_is_authenticated_and_flows_to_perception.select()` | Selects the current object. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 197 | `Perception.test_dashboard_screen_guidance_is_authenticated_and_flows_to_perception.__init__()` | Initializes a Perception instance. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 198 | `Perception.test_dashboard_screen_guidance_is_authenticated_and_flows_to_perception.observe()` | Observes the current object. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 200 | `test_dashboard_screen_guidance_is_authenticated_and_flows_to_perception.scenario()` | Implements the scenario operation. |

## `tests/test_dashboard.py`

| Line | Function / method | Description |
|---:|---|---|
| 217 | `test_dashboard_assets_expose_quick_start_guidance_and_window_states()` | Tests the dashboard assets expose quick start guidance and window states scenario. |

## `tests/test_dashboard_end_to_end.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `test_complete_verified_mission_is_visible_in_dashboard()` | Tests the complete verified mission is visible in dashboard scenario. |

## `tests/test_dashboard_end_to_end.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `WriteOnce.test_complete_verified_mission_is_visible_in_dashboard.__init__()` | Initializes a WriteOnce instance. |

## `tests/test_dashboard_end_to_end.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `WriteOnce.test_complete_verified_mission_is_visible_in_dashboard.next_action()` | Implements the next action operation for WriteOnce. |

## `tests/test_dashboard_end_to_end.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `FileExists.test_complete_verified_mission_is_visible_in_dashboard.verify()` | Verifies the current object. |

## `tests/test_dashboard_end_to_end.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `test_complete_verified_mission_is_visible_in_dashboard.scenario()` | Implements the scenario operation. |

## `tests/test_dashboard_startup.py`

| Line | Function / method | Description |
|---:|---|---|
| 4 | `test_dashboard_generates_strong_per_run_token_when_unconfigured()` | Tests the dashboard generates strong per run token when unconfigured scenario. |

## `tests/test_dashboard_startup.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `test_dashboard_honors_valid_configured_token_and_rejects_short_value()` | Tests the dashboard honors valid configured token and rejects short value scenario. |

## `tests/test_desktop_automation.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `FakeKeyboard.__init__()` | Initializes a FakeKeyboard instance. |

## `tests/test_desktop_automation.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `FakeKeyboard.type_text()` | Implements the type text operation for FakeKeyboard. |

## `tests/test_desktop_automation.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `FakeKeyboard.press_hotkey()` | Implements the press hotkey operation for FakeKeyboard. |

## `tests/test_desktop_automation.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `FakeLauncher.__init__()` | Initializes a FakeLauncher instance. |

## `tests/test_desktop_automation.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `FakeLauncher.launch()` | Implements the launch operation for FakeLauncher. |

## `tests/test_desktop_automation.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `test_desktop_tools_use_allowlisted_launcher_and_keyboard()` | Tests the desktop tools use allowlisted launcher and keyboard scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `Desktop.__init__()` | Initializes a Desktop instance. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 27 | `Desktop.windows()` | Implements the windows operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `Desktop.identity()` | Implements the identity operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `Desktop.foreground()` | Implements the foreground operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `Desktop.focus()` | Implements the focus operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `Desktop.point_in_window()` | Implements the point in window operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `Desktop.click()` | Implements the click operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `Desktop.clipboard_read()` | Implements the clipboard read operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 51 | `Desktop.clipboard_write()` | Implements the clipboard write operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 54 | `Desktop.hotkey()` | Implements the hotkey operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `Desktop.snapshot()` | Implements the snapshot operation for Desktop. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `Team.__init__()` | Initializes a Team instance. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 73 | `Team.open()` | Implements the open operation for Team. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 76 | `Team.set_checkpoint_context()` | Implements the set checkpoint context operation for Team. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 79 | `Team.send_prompt()` | Sends prompt. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 84 | `Team.wait_for_response()` | Waits for for response. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 87 | `Team.extract_response()` | Extracts response. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 94 | `action()` | Implements the action operation. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 99 | `complete()` | Implements the complete operation. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 103 | `verify()` | Verifies the current object. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 107 | `setup()` | Implements the setup operation. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 115 | `test_team_executes_grounded_note_after_browser_focus_change_and_verifies()` | Tests the team executes grounded note after browser focus change and verifies scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 131 | `test_mutation_without_approval_is_blocked_without_click_or_input()` | Tests the mutation without approval is blocked without click or input scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 139 | `test_existing_permission_denial_is_not_bypassed_by_approval()` | Tests the existing permission denial is not bypassed by approval scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 154 | `test_unsafe_or_ungrounded_output_is_rejected_before_execution()` | Tests the unsafe or ungrounded output is rejected before execution scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 163 | `test_team_can_repair_a_rejected_proposal_from_new_observation()` | Tests the team can repair a rejected proposal from new observation scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 173 | `test_rejects_target_that_changed_during_peer_reasoning()` | Tests the rejects target that changed during peer reasoning scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 175 | `test_rejects_target_that_changed_during_peer_reasoning.changed()` | Implements the changed operation. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 186 | `test_false_completion_verification_cannot_mark_work_complete()` | Tests the false completion verification cannot mark work complete scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 194 | `test_prior_unknown_action_is_context_only_and_never_replayed()` | Tests the prior unknown action is context only and never replayed scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 207 | `test_action_budget_stops_additional_side_effects()` | Tests the action budget stops additional side effects scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 216 | `test_team_timeout_is_saved_as_blocked()` | Tests the team timeout is saved as blocked scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 218 | `test_team_timeout_is_saved_as_blocked.slow()` | Implements the slow operation. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 228 | `test_keyboard_requires_actual_target_focus()` | Tests the keyboard requires actual target focus scenario. |

## `tests/test_desktop_team_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 238 | `test_shell_context_is_not_a_text_execution_channel()` | Tests the shell context is not a text execution channel scenario. |

## `tests/test_engine_capabilities.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `test_blender_operations_are_fixed_and_paths_are_sandboxed()` | Tests the blender operations are fixed and paths are sandboxed scenario. |

## `tests/test_engine_capabilities.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `test_unreal_projects_are_sandboxed_and_have_required_extension()` | Tests the unreal projects are sandboxed and have required extension scenario. |

## `tests/test_engine_capabilities.py`

| Line | Function / method | Description |
|---:|---|---|
| 42 | `test_plan_render_default_matches_generated_render_path()` | Tests the plan render default matches generated render path scenario. |

## `tests/test_environment_autonomy.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `test_environment_explorer_is_bounded_and_reports_available_tools()` | Tests the environment explorer is bounded and reports available tools scenario. |

## `tests/test_environment_autonomy.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `test_boundary_memory_records_known_failure()` | Tests the boundary memory records known failure scenario. |

## `tests/test_environment_autonomy.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `test_tool_builder_only_stages_discovered_allow_listed_executables()` | Tests the tool builder only stages discovered allow listed executables scenario. |

## `tests/test_event_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `test_blueprint_creates_bounded_child_and_discovers_only_allowed_actions()` | Tests the blueprint creates bounded child and discovers only allowed actions scenario. |

## `tests/test_event_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `test_agent_action_and_chain_are_reusable_building_blocks()` | Tests the agent action and chain are reusable building blocks scenario. |

## `tests/test_event_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `test_agent_action_and_chain_are_reusable_building_blocks.scenario()` | Implements the scenario operation. |

## `tests/test_event_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `test_config_is_private_by_default_and_honors_dry_run()` | Tests the config is private by default and honors dry run scenario. |

## `tests/test_event_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `test_structured_logs_redact_sensitive_values()` | Tests the structured logs redact sensitive values scenario. |

## `tests/test_event_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 47 | `test_mock_event_generator_is_explicit_and_deterministic()` | Tests the mock event generator is explicit and deterministic scenario. |

## `tests/test_event_agent_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `test_mock_event_generator_is_explicit_and_deterministic.scenario()` | Implements the scenario operation. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `test_replay_routes_retained_event_without_duplicating_history()` | Tests the replay routes retained event without duplicating history scenario. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `test_replay_routes_retained_event_without_duplicating_history.scenario()` | Implements the scenario operation. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `test_optional_detector_failure_does_not_stop_healthy_detectors()` | Tests the optional detector failure does not stop healthy detectors scenario. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `Broken.test_optional_detector_failure_does_not_stop_healthy_detectors.poll()` | Polls the current object. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 27 | `Healthy.test_optional_detector_failure_does_not_stop_healthy_detectors.poll()` | Polls the current object. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `test_optional_detector_failure_does_not_stop_healthy_detectors.scenario()` | Implements the scenario operation. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `test_network_power_and_scheduler_use_injected_real_adapter_boundaries()` | Tests the network power and scheduler use injected real adapter boundaries scenario. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `test_network_power_and_scheduler_use_injected_real_adapter_boundaries.scenario()` | Implements the scenario operation. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `test_functional_agent_factory_and_action_discovery_are_permission_scoped()` | Tests the functional agent factory and action discovery are permission scoped scenario. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 61 | `test_circuit_breaker_opens_after_repeated_integration_failures()` | Tests the circuit breaker opens after repeated integration failures scenario. |

## `tests/test_event_system_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_circuit_breaker_opens_after_repeated_integration_failures.scenario()` | Implements the scenario operation. |

## `tests/test_fallback_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `CopyingProvider.__init__()` | Initializes a CopyingProvider instance. |

## `tests/test_fallback_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `CopyingProvider.copy_latest_response()` | Implements the copy latest response operation for CopyingProvider. |

## `tests/test_fallback_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `FakeOcr.read()` | Reads the current object. |

## `tests/test_fallback_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `test_clipboard_fallback_uses_provider_copy_control()` | Tests the clipboard fallback uses provider copy control scenario. |

## `tests/test_fallback_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `test_clipboard_fallback_rejects_empty_content()` | Tests the clipboard fallback rejects empty content scenario. |

## `tests/test_fallback_extractor.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `test_ocr_fallback_validates_ocr_text()` | Tests the ocr fallback validates ocr text scenario. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `test_guided_email_clarifies_executes_confirms_and_learns()` | Tests the guided email clarifies executes confirms and learns scenario. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `Provider.test_guided_email_clarifies_executes_confirms_and_learns.open()` | Implements the open operation for Provider. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `Provider.test_guided_email_clarifies_executes_confirms_and_learns.verify_page()` | Verifies page. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `Provider.test_guided_email_clarifies_executes_confirms_and_learns.start_conversation()` | Starts conversation. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `Provider.test_guided_email_clarifies_executes_confirms_and_learns.send_prompt()` | Sends prompt. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `Provider.test_guided_email_clarifies_executes_confirms_and_learns.wait_for_response()` | Waits for for response. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `Provider.test_guided_email_clarifies_executes_confirms_and_learns.extract_response()` | Extracts response. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `Locator.test_guided_email_clarifies_executes_confirms_and_learns.count()` | Counts the current object. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `Locator.test_guided_email_clarifies_executes_confirms_and_learns.fill()` | Implements the fill operation for Locator. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `Locator.test_guided_email_clarifies_executes_confirms_and_learns.click()` | Implements the click operation for Locator. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `Locator.test_guided_email_clarifies_executes_confirms_and_learns.first()` | Implements the first operation for Locator. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `Page.test_guided_email_clarifies_executes_confirms_and_learns.get_by_label()` | Retrieves by label. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `Page.test_guided_email_clarifies_executes_confirms_and_learns.get_by_role()` | Retrieves by role. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `Page.test_guided_email_clarifies_executes_confirms_and_learns.get_by_text()` | Retrieves by text. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `Browser.test_guided_email_clarifies_executes_confirms_and_learns.start()` | Starts the current object. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `Browser.test_guided_email_clarifies_executes_confirms_and_learns.page_for()` | Implements the page for operation for Browser. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `Prompt.test_guided_email_clarifies_executes_confirms_and_learns.ask()` | Implements the ask operation for Prompt. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `Prompt.test_guided_email_clarifies_executes_confirms_and_learns.confirm()` | Implements the confirm operation for Prompt. |

## `tests/test_guided_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `test_guided_workflow_rejects_unsafe_plan_and_requires_approval()` | Tests the guided workflow rejects unsafe plan and requires approval scenario. |

## `tests/test_intervention.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `test_intervention_gate_waits_for_explicit_continue()` | Tests the intervention gate waits for explicit continue scenario. |

## `tests/test_intervention.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `test_intervention_gate_waits_for_explicit_continue.scenario()` | Implements the scenario operation. |

## `tests/test_intervention.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `test_intervention_gate_obeys_emergency_stop()` | Tests the intervention gate obeys emergency stop scenario. |

## `tests/test_intervention.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `test_intervention_gate_obeys_emergency_stop.scenario()` | Implements the scenario operation. |

## `tests/test_landmark_planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `test_bevel_amount_is_normalized_and_bounded()` | Tests the bevel amount is normalized and bounded scenario. |

## `tests/test_landmark_planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `test_landmark_plan_is_executable_with_documented_limits()` | Tests the landmark plan is executable with documented limits scenario. |

## `tests/test_landmark_planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `test_tajmahal_planning_repairs_invalid_responses()` | Tests the tajmahal planning repairs invalid responses scenario. |

## `tests/test_landmark_planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `test_tajmahal_planning_repairs_invalid_responses.ask()` | Implements the ask operation. |

## `tests/test_landmark_planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `test_tajmahal_planning_repairs_invalid_responses.stop_before_execution()` | Stops before execution. |

## `tests/test_landmark_planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 42 | `test_tajmahal_planning_repairs_invalid_responses.request()` | Implements the request operation. |

## `tests/test_landmark_planning.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `test_real_tajmahal_arches_domes_and_bevel()` | Tests the real tajmahal arches domes and bevel scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `make_skill()` | Implements the make skill operation. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `test_experience_is_durable_ranked_and_external_content_is_not_trusted()` | Tests the experience is durable ranked and external content is not trusted scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `test_skills_are_versioned_candidate_first_and_regressions_are_rejected()` | Tests the skills are versioned candidate first and regressions are rejected scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 37 | `test_second_goal_retrieves_experience_discovers_skill_and_synthesizes_reusable_graph()` | Tests the second goal retrieves experience discovers skill and synthesizes reusable graph scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 53 | `test_execution_evaluation_creates_candidate_only_from_verified_structured_workflow()` | Tests the execution evaluation creates candidate only from verified structured workflow scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_conflicts_require_verification_or_high_risk_escalation()` | Tests the conflicts require verification or high risk escalation scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 70 | `test_learning_coordinator_records_first_execution_and_reuses_advisory_workflow()` | Tests the learning coordinator records first execution and reuses advisory workflow scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 86 | `test_continuous_learning_reuses_candidate_and_evaluates_repeated_outcomes()` | Tests the continuous learning reuses candidate and evaluates repeated outcomes scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 108 | `test_continuous_learning_never_auto_activates_and_deprecates_regression()` | Tests the continuous learning never auto activates and deprecates regression scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 125 | `test_skill_sandbox_rejects_permission_escalation()` | Tests the skill sandbox rejects permission escalation scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 133 | `test_corrupt_and_expired_experiences_do_not_break_advisory_retrieval()` | Tests the corrupt and expired experiences do not break advisory retrieval scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 146 | `test_runtime_policy_never_grants_skill_permissions_or_ignores_preconditions()` | Tests the runtime policy never grants skill permissions or ignores preconditions scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 160 | `test_skill_sandbox_evaluation_requires_test_before_human_approval_and_audits()` | Tests the skill sandbox evaluation requires test before human approval and audits scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 175 | `test_evidence_store_is_durable()` | Tests the evidence store is durable scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 184 | `test_human_feedback_is_durable_and_cannot_target_unknown_experience()` | Tests the human feedback is durable and cannot target unknown experience scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 193 | `test_feedback_changes_experience_ranking_and_explanation_is_structured()` | Tests the feedback changes experience ranking and explanation is structured scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 206 | `test_agent_performance_is_durable_and_contextual()` | Tests the agent performance is durable and contextual scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 216 | `test_disposable_filesystem_sandbox_is_isolated_and_removed()` | Tests the disposable filesystem sandbox is isolated and removed scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 225 | `test_skill_sandbox_restricted_runner_accepts_only_runtime_experience()` | Tests the skill sandbox restricted runner accepts only runtime experience scenario. |

## `tests/test_learning.py`

| Line | Function / method | Description |
|---:|---|---|
| 229 | `test_skill_sandbox_restricted_runner_accepts_only_runtime_experience.runner()` | Implements the runner operation. |

## `tests/test_live_blender_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `test_live_runtime_tracks_edited_geometry_without_camera_or_visibility_side_effects()` | Tests the live runtime tracks edited geometry without camera or visibility side effects scenario. |

## `tests/test_live_blender_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 78 | `start_job()` | Starts job. |

## `tests/test_live_blender_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `finish_job()` | Implements the finish job operation. |

## `tests/test_memory.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `test_sqlite_memory_stores_and_searches()` | Tests the sqlite memory stores and searches scenario. |

## `tests/test_memory_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `test_memory_manager_formats_bounded_relevant_context()` | Tests the memory manager formats bounded relevant context scenario. |

## `tests/test_memory_screenshot_migration.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `test_sqlite_memory_migrates_and_stores_screenshot_path()` | Tests the sqlite memory migrates and stores screenshot path scenario. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `session()` | Implements the session operation. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `Workflow.session.__init__()` | Initializes a Workflow instance. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `Workflow.session.run()` | Runs the current object. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `session.start()` | Starts the current object. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `test_interactive_new_subject_does_not_modify_previous_project()` | Tests the interactive new subject does not modify previous project scenario. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `test_related_request_after_restart_uses_selected_project()` | Tests the related request after restart uses selected project scenario. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 69 | `test_explicit_resume_id_is_not_rerouted_to_selected_project()` | Tests the explicit resume id is not rerouted to selected project scenario. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 79 | `test_explicit_new_same_subject_gets_separate_project()` | Tests the explicit new same subject gets separate project scenario. |

## `tests/test_model_task_session.py`

| Line | Function / method | Description |
|---:|---|---|
| 93 | `test_ambiguous_initial_task_is_classified_before_scene_changes()` | Tests the ambiguous initial task is classified before scene changes scenario. |

## `tests/test_model_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `cube()` | Implements the cube operation. |

## `tests/test_model_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `test_general_model_resume_update_and_retry()` | Tests the general model resume update and retry scenario. |

## `tests/test_model_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `test_general_model_resume_update_and_retry.ask()` | Implements the ask operation. |

## `tests/test_model_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `test_general_model_resume_update_and_retry.execute()` | Executes the current object. |

## `tests/test_model_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `test_general_model_rejects_invalid_and_destructive_update_plans()` | Tests the general model rejects invalid and destructive update plans scenario. |

## `tests/test_model_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 81 | `test_one_visible_blender_process_for_multiple_steps()` | Tests the one visible blender process for multiple steps scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `observation()` | Implements the observation operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `test_fusion_combines_sources_and_preserves_untrusted_boundary()` | Tests the fusion combines sources and preserves untrusted boundary scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 42 | `test_semantic_grounding_precedes_geometry_and_ambiguity_fails_closed()` | Tests the semantic grounding precedes geometry and ambiguity fails closed scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `test_spatial_and_ordinal_grounding()` | Tests the spatial and ordinal grounding scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 76 | `test_change_and_human_blocker_detection()` | Tests the change and human blocker detection scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 86 | `test_active_engine_uses_authorized_controller_observation_and_updates_world()` | Tests the active engine uses authorized controller observation and updates world scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 88 | `Controller.test_active_engine_uses_authorized_controller_observation_and_updates_world.observe()` | Observes the current object. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 91 | `Controller.test_active_engine_uses_authorized_controller_observation_and_updates_world.execute()` | Executes the current object. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 94 | `test_active_engine_uses_authorized_controller_observation_and_updates_world.scenario()` | Implements the scenario operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 109 | `test_context_is_bounded_and_screen_data_cannot_create_action_intent()` | Tests the context is bounded and screen data cannot create action intent scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 123 | `test_dashboard_observation_uses_gateway_and_redacts_visible_secrets()` | Tests the dashboard observation uses gateway and redacts visible secrets scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 127 | `Source.test_dashboard_observation_uses_gateway_and_redacts_visible_secrets.observe()` | Observes the current object. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 133 | `test_dashboard_observation_uses_gateway_and_redacts_visible_secrets.scenario()` | Implements the scenario operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 150 | `test_filesystem_source_reports_real_bounded_metadata_changes()` | Tests the filesystem source reports real bounded metadata changes scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 151 | `test_filesystem_source_reports_real_bounded_metadata_changes.scenario()` | Implements the scenario operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 164 | `test_agent_perception_requires_runtime_grant_and_scopes_extra_fields()` | Tests the agent perception requires runtime grant and scopes extra fields scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 168 | `Source.test_agent_perception_requires_runtime_grant_and_scopes_extra_fields.observe()` | Observes the current object. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 171 | `test_agent_perception_requires_runtime_grant_and_scopes_extra_fields.scenario()` | Implements the scenario operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 183 | `test_perception_degrades_when_one_source_fails_without_leaking_error()` | Tests the perception degrades when one source fails without leaking error scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 187 | `Good.test_perception_degrades_when_one_source_fails_without_leaking_error.observe()` | Observes the current object. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 192 | `Broken.test_perception_degrades_when_one_source_fails_without_leaking_error.observe()` | Observes the current object. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 194 | `test_perception_degrades_when_one_source_fails_without_leaking_error.scenario()` | Implements the scenario operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 205 | `test_owner_selected_region_becomes_semantic_evidence_without_execution()` | Tests the owner selected region becomes semantic evidence without execution scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 207 | `Selector.test_owner_selected_region_becomes_semantic_evidence_without_execution.select()` | Selects the current object. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 212 | `test_owner_selected_region_becomes_semantic_evidence_without_execution.scenario()` | Implements the scenario operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 236 | `test_desktop_window_source_reports_minimized_maximized_and_active_states()` | Tests the desktop window source reports minimized maximized and active states scenario. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 238 | `Window.test_desktop_window_source_reports_minimized_maximized_and_active_states.__init__()` | Initializes a Window instance. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 248 | `Backend.test_desktop_window_source_reports_minimized_maximized_and_active_states.getAllWindows()` | Implements the getAllWindows operation for Backend. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 252 | `test_desktop_window_source_reports_minimized_maximized_and_active_states.scenario()` | Implements the scenario operation. |

## `tests/test_multimodal_perception.py`

| Line | Function / method | Description |
|---:|---|---|
| 270 | `test_window_minimize_and_focus_changes_are_structural_drift()` | Tests the window minimize and focus changes are structural drift scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `test_current_website_accessible_composer_labels_are_recognized()` | Tests the current website accessible composer labels are recognized scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `test_focus_click_requires_inert_visible_caption_and_original_identity()` | Tests the focus click requires inert visible caption and original identity scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `test_focus_click_requires_inert_visible_caption_and_original_identity.rectangle()` | Implements the rectangle operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `test_focus_click_requires_inert_visible_caption_and_original_identity.hit_test()` | Implements the hit test operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 55 | `test_focus_restores_non_topmost_state_if_caption_activation_fails()` | Tests the focus restores non topmost state if caption activation fails scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_focus_restores_non_topmost_state_if_caption_activation_fails.failed()` | Implements the failed operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 72 | `Desktop.__init__()` | Initializes a Desktop instance. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 87 | `Desktop.windows()` | Implements the windows operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `Desktop.spawn()` | Implements the spawn operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 96 | `Desktop.identity()` | Implements the identity operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 99 | `Desktop.focus()` | Implements the focus operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 104 | `Desktop.foreground()` | Implements the foreground operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 107 | `Desktop.hotkey()` | Implements the hotkey operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 118 | `Desktop.console_ready()` | Implements the console ready operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 122 | `Desktop.clipboard_read()` | Implements the clipboard read operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 125 | `Desktop.clipboard_write()` | Implements the clipboard write operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 129 | `Desktop.point_in_window()` | Implements the point in window operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 132 | `Desktop.click()` | Implements the click operation for Desktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 135 | `Desktop.close()` | Closes the current object. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 140 | `transport()` | Implements the transport operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 145 | `owned()` | Implements the owned operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 150 | `test_launch_adopts_only_new_exact_marker_and_close_preserves_personal_windows()` | Tests the launch adopts only new exact marker and close preserves personal windows scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 163 | `test_launch_never_adopts_existing_window_even_with_matching_title()` | Tests the launch never adopts existing window even with matching title scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 175 | `test_failed_launch_without_process_can_be_retried()` | Tests the failed launch without process can be retried scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 179 | `test_failed_launch_without_process_can_be_retried.fail()` | Implements the fail operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 194 | `test_late_launch_recovery_uses_one_read_only_probe_and_original_window_set()` | Tests the late launch recovery uses one read only probe and original window set scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 206 | `test_late_launch_recovery_uses_one_read_only_probe_and_original_window_set.windows()` | Implements the windows operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 222 | `test_uncertain_spawn_keeps_evidence_and_prevents_duplicate_launch()` | Tests the uncertain spawn keeps evidence and prevents duplicate launch scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 226 | `test_uncertain_spawn_keeps_evidence_and_prevents_duplicate_launch.uncertain_spawn()` | Implements the uncertain spawn operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 241 | `test_post_spawn_inspection_failure_does_not_permit_relaunch()` | Tests the post spawn inspection failure does not permit relaunch scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 245 | `test_post_spawn_inspection_failure_does_not_permit_relaunch.fail_after_spawn()` | Implements the fail after spawn operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 263 | `test_ambiguous_launch_retains_evidence_until_exactly_one_new_marker_remains()` | Tests the ambiguous launch retains evidence until exactly one new marker remains scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 267 | `test_ambiguous_launch_retains_evidence_until_exactly_one_new_marker_remains.ambiguous_spawn()` | Implements the ambiguous spawn operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 285 | `test_late_launch_does_not_adopt_unverified_window_identity()` | Tests the late launch does not adopt unverified window identity scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 301 | `test_window_health_is_read_only_and_retains_cleanup_ownership()` | Tests the window health is read only and retains cleanup ownership scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 320 | `test_window_health_propagates_inspection_error_without_losing_ownership()` | Tests the window health propagates inspection error without losing ownership scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 324 | `test_window_health_propagates_inspection_error_without_losing_ownership.unavailable()` | Implements the unavailable operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 336 | `test_native_operation_budgets_reject_unbounded_or_invalid_values()` | Tests the native operation budgets reject unbounded or invalid values scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 342 | `test_native_operation_deadlines_and_poll_interval_must_be_positive()` | Tests the native operation deadlines and poll interval must be positive scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 348 | `test_close_retains_ownership_until_window_actually_disappears()` | Tests the close retains ownership until window actually disappears scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 362 | `test_close_of_already_closed_or_reused_window_never_targets_new_owner()` | Tests the close of already closed or reused window never targets new owner scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 379 | `test_marker_title_is_not_a_substring_match()` | Tests the marker title is not a substring match scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 384 | `test_edge_profile_title_and_invisible_brand_character_are_recognized()` | Tests the edge profile title and invisible brand character are recognized scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 392 | `test_uncertain_console_tab_does_not_quarantine_its_sibling()` | Tests the uncertain console tab does not quarantine its sibling scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 411 | `test_evaluate_selects_tab_atomically_and_restores_clipboard()` | Tests the evaluate selects tab atomically and restores clipboard scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 422 | `test_unverified_console_never_pastes_or_submits_any_script()` | Tests the unverified console never pastes or submits any script scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 434 | `test_timeout_pauses_without_self_xss_bypass_or_replay()` | Tests the timeout pauses without self xss bypass or replay scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 451 | `test_unrelated_clipboard_changes_are_preserved_and_nonce_must_match()` | Tests the unrelated clipboard changes are preserved and nonce must match scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 462 | `test_focus_must_match_before_each_input_and_stops_after_paste()` | Tests the focus must match before each input and stops after paste scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 474 | `test_reused_handle_never_gets_focused()` | Tests the reused handle never gets focused scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 484 | `test_navigation_only_provider_sites_and_owned_clicks()` | Tests the navigation only provider sites and owned clicks scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 500 | `test_global_lock_serializes_separate_transport_instances()` | Tests the global lock serializes separate transport instances scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 505 | `test_global_lock_serializes_separate_transport_instances.long_operation()` | Implements the long operation operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 521 | `test_cancelled_operation_finishes_before_releasing_input_lane()` | Tests the cancelled operation finishes before releasing input lane scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 538 | `test_repeated_cancellation_drains_native_operation_before_returning()` | Tests the repeated cancellation drains native operation before returning scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 544 | `test_repeated_cancellation_drains_native_operation_before_returning.blocked()` | Implements the blocked operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 597 | `test_console_accessibility_checks_focused_control()` | Tests the console accessibility checks focused control scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 601 | `accessibility_nodes()` | Implements the accessibility nodes operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 616 | `AccessibleDesktop.__init__()` | Initializes a AccessibleDesktop instance. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 626 | `AccessibleDesktop.accessibility_snapshot()` | Implements the accessibility snapshot operation for AccessibleDesktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 630 | `AccessibleDesktop.control_at()` | Implements the control at operation for AccessibleDesktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 633 | `AccessibleDesktop.focused_control()` | Implements the focused control operation for AccessibleDesktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 636 | `AccessibleDesktop.click()` | Implements the click operation for AccessibleDesktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 642 | `AccessibleDesktop.hotkey()` | Implements the hotkey operation for AccessibleDesktop. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 650 | `native_bind()` | Implements the native bind operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 654 | `test_accessibility_extracts_explicit_assistant_group_without_user_text()` | Tests the accessibility extracts explicit assistant group without user text scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 665 | `test_native_path_pastes_and_clicks_observed_controls_without_console()` | Tests the native path pastes and clicks observed controls without console scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 684 | `test_native_input_does_not_send_if_control_or_content_cannot_be_verified()` | Tests the native input does not send if control or content cannot be verified scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 703 | `test_native_unknown_send_is_latched_and_never_clicked_twice()` | Tests the native unknown send is latched and never clicked twice scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 718 | `test_native_rechecks_provider_url_and_prompt_before_send()` | Tests the native rechecks provider url and prompt before send scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 733 | `test_native_does_not_clear_uncertain_console_execution()` | Tests the native does not clear uncertain console execution scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 743 | `test_semantic_composer_focus_and_send_do_not_depend_on_parent_hit_testing()` | Tests the semantic composer focus and send do not depend on parent hit testing scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 746 | `test_semantic_composer_focus_and_send_do_not_depend_on_parent_hit_testing.focus()` | Implements the focus operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 750 | `test_semantic_composer_focus_and_send_do_not_depend_on_parent_hit_testing.invoke()` | Implements the invoke operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 764 | `test_semantic_send_exception_retains_unknown_outcome_without_second_invocation()` | Tests the semantic send exception retains unknown outcome without second invocation scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 766 | `test_semantic_send_exception_retains_unknown_outcome_without_second_invocation.invoke()` | Implements the invoke operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 780 | `test_chatgpt_temporary_url_becomes_pinned_canonical_conversation()` | Tests the chatgpt temporary url becomes pinned canonical conversation scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 795 | `test_anonymous_composer_with_visible_login_button_is_not_ready()` | Tests the anonymous composer with visible login button is not ready scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 801 | `test_repair_prompt_mentioning_captcha_is_not_a_challenge()` | Tests the repair prompt mentioning captcha is not a challenge scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 810 | `test_current_chatgpt_answer_group_requires_adjacent_response_action_controls()` | Tests the current chatgpt answer group requires adjacent response action controls scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 823 | `test_gemini_accessibility_only_author_label_requires_own_feedback_controls()` | Tests the gemini accessibility only author label requires own feedback controls scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 843 | `test_long_reply_keeps_offscreen_text_in_nested_reading_order()` | Tests the long reply keeps offscreen text in nested reading order scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 856 | `test_current_chatgpt_scrolled_reply_footer_still_identifies_answer()` | Tests the current chatgpt scrolled reply footer still identifies answer scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 868 | `test_chatgpt_flattened_history_does_not_hide_a_new_turn()` | Tests the chatgpt flattened history does not hide a new turn scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 888 | `test_navigation_requires_address_focus_and_exact_url_before_enter()` | Tests the navigation requires address focus and exact url before enter scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 900 | `test_copy_response_preserves_json_escaping_and_restores_clipboard()` | Tests the copy response preserves json escaping and restores clipboard scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 908 | `test_copy_response_preserves_json_escaping_and_restores_clipboard.copy()` | Implements the copy operation. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 924 | `test_response_correlation_requires_exact_copy_message_hash()` | Tests the response correlation requires exact copy message hash scenario. |

## `tests/test_native_console.py`

| Line | Function / method | Description |
|---:|---|---|
| 933 | `test_response_correlation_requires_exact_copy_message_hash.copy()` | Implements the copy operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `FakeTransport.__init__()` | Initializes a FakeTransport instance. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `FakeTransport.queue()` | Implements the queue operation for FakeTransport. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `FakeTransport.navigate()` | Implements the navigate operation for FakeTransport. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `FakeTransport.state()` | Implements the state operation for FakeTransport. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `FakeTransport.evaluate()` | Evaluates the current object. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 76 | `FakeTransport.calls()` | Implements the calls operation for FakeTransport. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 81 | `client()` | Implements the client operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 91 | `restart()` | Implements the restart operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 99 | `test_coordinator_recovers_native_completed_response_after_crash_gap()` | Tests the coordinator recovers native completed response after crash gap scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 123 | `test_submission_intent_precedes_send_and_prompt_stays_json_data()` | Tests the submission intent precedes send and prompt stays json data scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 126 | `test_submission_intent_precedes_send_and_prompt_stays_json_data.inspect_intent()` | Implements the inspect intent operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 146 | `test_old_answer_text_changes_are_not_new_turns()` | Tests the old answer text changes are not new turns scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 158 | `test_virtualized_reply_needs_exact_user_prompt_verification()` | Tests the virtualized reply needs exact user prompt verification scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 167 | `test_virtualized_reply_needs_exact_user_prompt_verification.action()` | Implements the action operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 187 | `test_fallback_selector_is_compared_to_its_own_baseline()` | Tests the fallback selector is compared to its own baseline scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 199 | `test_growing_fallback_selector_can_produce_new_answer()` | Tests the growing fallback selector can produce new answer scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 211 | `test_observation_failure_never_makes_sent_prompt_safe_to_retry()` | Tests the observation failure never makes sent prompt safe to retry scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 225 | `test_latest_canonical_url_survives_polling_failure()` | Tests the latest canonical url survives polling failure scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 237 | `test_confirmed_pre_send_failure_permits_retry()` | Tests the confirmed pre send failure permits retry scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 250 | `test_owner_interventions_before_send_never_create_pending_receipt()` | Tests the owner interventions before send never create pending receipt scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 260 | `test_submission_cancellation_is_durable_and_restart_does_not_replay()` | Tests the submission cancellation is durable and restart does not replay scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 275 | `test_read_only_recovery_in_current_tab_never_submits_again()` | Tests the read only recovery in current tab never submits again scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 288 | `test_restart_recovers_only_saved_canonical_chat()` | Tests the restart recovers only saved canonical chat scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 300 | `test_recovery_never_accepts_a_reply_from_another_conversation()` | Tests the recovery never accepts a reply from another conversation scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 315 | `test_completed_response_recovery_requires_exact_coordinator_round()` | Tests the completed response recovery requires exact coordinator round scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 331 | `test_pending_receipt_mismatch_cannot_be_attributed_to_another_round()` | Tests the pending receipt mismatch cannot be attributed to another round scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 348 | `test_pending_request_context_cannot_change()` | Tests the pending request context cannot change scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 360 | `test_recovery_without_canonical_url_does_not_navigate_or_send()` | Tests the recovery without canonical url does not navigate or send scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 370 | `test_rollover_survives_safe_retry_and_restart_with_checkpoint()` | Tests the rollover survives safe retry and restart with checkpoint scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 388 | `test_completed_turn_count_survives_restart_and_rotates_chat()` | Tests the completed turn count survives restart and rotates chat scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 400 | `test_rollover_context_never_truncates_original_task_or_exceeds_limit()` | Tests the rollover context never truncates original task or exceeds limit scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 411 | `test_bind_waits_for_navigation_origin_transition()` | Tests the bind waits for navigation origin transition scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 419 | `test_probe_preserves_prior_console_intervention_and_uncertainty()` | Tests the probe preserves prior console intervention and uncertainty scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 422 | `test_probe_preserves_prior_console_intervention_and_uncertainty.navigate()` | Implements the navigate operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 436 | `test_console_setup_probe_is_blocked_without_inventing_a_submission()` | Tests the console setup probe is blocked without inventing a submission scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 445 | `test_team_rejoins_after_prior_console_uncertainty_is_resolved()` | Tests the team rejoins after prior console uncertainty is resolved scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 462 | `test_malformed_console_prepare_still_allows_certified_safe_retry()` | Tests the malformed console prepare still allows certified safe retry scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 464 | `test_malformed_console_prepare_still_allows_certified_safe_retry.unsupported_native()` | Implements the unsupported native operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 478 | `test_auto_loading_errors_never_open_developer_console()` | Tests the auto loading errors never open developer console scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 479 | `test_auto_loading_errors_never_open_developer_console.native_action()` | Implements the native action operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 489 | `test_peer_repair_cannot_switch_input_for_pending_prompt()` | Tests the peer repair cannot switch input for pending prompt scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 499 | `test_peer_reload_preserves_conversation_and_never_sends()` | Tests the peer reload preserves conversation and never sends scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 511 | `test_peer_reload_refuses_a_generating_tab()` | Tests the peer reload refuses a generating tab scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 521 | `test_peer_can_switch_unsent_client_to_native_and_recheck()` | Tests the peer can switch unsent client to native and recheck scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 524 | `test_peer_can_switch_unsent_client_to_native_and_recheck.native_action()` | Implements the native action operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 534 | `test_malformed_native_probe_keeps_submission_pending()` | Tests the malformed native probe keeps submission pending scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 538 | `test_malformed_native_probe_keeps_submission_pending.invalid_native()` | Implements the invalid native operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 548 | `test_malformed_native_fallback_is_classified_before_reading_result()` | Tests the malformed native fallback is classified before reading result scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 549 | `test_malformed_native_fallback_is_classified_before_reading_result.native_action()` | Implements the native action operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 560 | `test_session_cannot_change_during_initial_navigation()` | Tests the session cannot change during initial navigation scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 563 | `test_session_cannot_change_during_initial_navigation.navigate()` | Implements the navigate operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 580 | `test_saved_urls_are_validated_without_parser_crashes()` | Tests the saved urls are validated without parser crashes scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 584 | `test_checkpoint_is_detached_and_bounded_even_after_json_escaping()` | Tests the checkpoint is detached and bounded even after json escaping scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 593 | `test_session_store_closes_every_connection()` | Tests the session store closes every connection scenario. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 597 | `test_session_store_closes_every_connection.connect()` | Implements the connect operation. |

## `tests/test_native_website.py`

| Line | Function / method | Description |
|---:|---|---|
| 612 | `test_fixed_dom_program_with_offline_javascript_dom_fixture()` | Tests the fixed dom program with offline javascript dom fixture scenario. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `Controller.__init__()` | Initializes a Controller instance. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 18 | `Controller.observe()` | Observes the current object. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `Controller.execute()` | Executes the current object. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `setup()` | Implements the setup operation. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `test_malicious_proposals_are_rejected_before_tool_or_resource_access()` | Tests the malicious proposals are rejected before tool or resource access scenario. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 37 | `test_malicious_proposals_are_rejected_before_tool_or_resource_access.run()` | Runs the current object. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `test_structured_reasoning_proposal_cannot_grant_permissions_or_use_extra_arguments()` | Tests the structured reasoning proposal cannot grant permissions or use extra arguments scenario. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `test_world_model_comparison_and_simulation_do_not_execute_actions()` | Tests the world model comparison and simulation do not execute actions scenario. |

## `tests/test_no_direct_llm_boundary.py`

| Line | Function / method | Description |
|---:|---|---|
| 64 | `test_runtime_decisions_prefer_information_and_counterfactuals_are_inert()` | Tests the runtime decisions prefer information and counterfactuals are inert scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `test_persisted_time_and_filesystem_triggers_are_deterministic()` | Tests the persisted time and filesystem triggers are deterministic scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `test_persisted_time_and_filesystem_triggers_are_deterministic.scenario()` | Implements the scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `test_health_monitor_releases_dead_agent_resources_without_escalation()` | Tests the health monitor releases dead agent resources without escalation scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `test_health_monitor_releases_dead_agent_resources_without_escalation.scenario()` | Implements the scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 37 | `test_mode_policy_blocks_watch_and_requires_supervised_approval()` | Tests the mode policy blocks watch and requires supervised approval scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 46 | `test_task_engine_mission_runner_restores_graph_and_maps_verified_outcome()` | Tests the task engine mission runner restores graph and maps verified outcome scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 53 | `Engine.test_task_engine_mission_runner_restores_graph_and_maps_verified_outcome.run_graph()` | Runs graph. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `test_task_engine_mission_runner_restores_graph_and_maps_verified_outcome.graph_for()` | Implements the graph for operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 65 | `test_condition_and_prerequisite_mission_triggers_respect_runtime_policy()` | Tests the condition and prerequisite mission triggers respect runtime policy scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 66 | `test_condition_and_prerequisite_mission_triggers_respect_runtime_policy.scenario()` | Implements the scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 80 | `test_benchmark_harness_records_verified_local_report_workflow()` | Tests the benchmark harness records verified local report workflow scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 82 | `test_benchmark_harness_records_verified_local_report_workflow.report_scenario()` | Implements the report scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 92 | `test_interruption_and_presence_detection_keep_user_data_out_of_runtime()` | Tests the interruption and presence detection keep user data out of runtime scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 101 | `test_supervised_runtime_waits_for_independent_approval_before_execution()` | Tests the supervised runtime waits for independent approval before execution scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 111 | `test_supervised_runtime_waits_for_independent_approval_before_execution.scenario()` | Implements the scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 119 | `test_supervised_runtime_waits_for_independent_approval_before_execution.scenario.work()` | Implements the work operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 133 | `test_autonomy_governor_enforces_mission_authority_and_budgets()` | Tests the autonomy governor enforces mission authority and budgets scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 141 | `test_autonomy_governor_enforces_mission_authority_and_budgets.scenario()` | Implements the scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 161 | `test_runtime_deduplicates_same_action_identity()` | Tests the runtime deduplicates same action identity scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 168 | `test_runtime_deduplicates_same_action_identity.scenario()` | Implements the scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 182 | `test_capability_lease_is_task_scoped_and_fail_closed_on_revoke()` | Tests the capability lease is task scoped and fail closed on revoke scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 188 | `test_capability_lease_is_task_scoped_and_fail_closed_on_revoke.scenario()` | Implements the scenario operation. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 203 | `test_persisted_event_details_are_redacted_before_storage()` | Tests the persisted event details are redacted before storage scenario. |

## `tests/test_operator_extensions.py`

| Line | Function / method | Description |
|---:|---|---|
| 205 | `test_persisted_event_details_are_redacted_before_storage.scenario()` | Implements the scenario operation. |

## `tests/test_pause.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `test_pause_controller_waits_until_resumed()` | Tests the pause controller waits until resumed scenario. |

## `tests/test_pause.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `test_pause_controller_waits_until_resumed.scenario()` | Implements the scenario operation. |

## `tests/test_persistent_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `test_tasks_survive_store_reopen_and_duplicate_submission()` | Tests the tasks survive store reopen and duplicate submission scenario. |

## `tests/test_persistent_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `test_runtime_processes_task_and_remains_alive_when_idle()` | Tests the runtime processes task and remains alive when idle scenario. |

## `tests/test_persistent_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `test_runtime_processes_task_and_remains_alive_when_idle.executor()` | Implements the executor operation. |

## `tests/test_persistent_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `test_runtime_recovers_running_tasks_and_limits_retries()` | Tests the runtime recovers running tasks and limits retries scenario. |

## `tests/test_persistent_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_runtime_recovers_running_tasks_and_limits_retries.executor()` | Implements the executor operation. |

## `tests/test_persistent_runtime.py`

| Line | Function / method | Description |
|---:|---|---|
| 75 | `test_health_reports_stale_or_missing_heartbeat()` | Tests the health reports stale or missing heartbeat scenario. |

## `tests/test_prompt_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `test_prompt_variables_render()` | Tests the prompt variables render scenario. |

## `tests/test_prompt_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `test_provider_specific_template_overrides_default()` | Tests the provider specific template overrides default scenario. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `FakeCandidate.__init__()` | Initializes a FakeCandidate instance. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `FakeCandidate.is_visible()` | Returns whether visible. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `FakeCandidate.is_enabled()` | Returns whether enabled. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `FakeCollection.__init__()` | Initializes a FakeCollection instance. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `FakeCollection.count()` | Counts the current object. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `FakeCollection.nth()` | Implements the nth operation for FakeCollection. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `FakePage.__init__()` | Initializes a FakePage instance. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `FakePage.locator()` | Implements the locator operation for FakePage. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `test_input_discovery_skips_hidden_and_disabled_duplicate_composers()` | Tests the input discovery skips hidden and disabled duplicate composers scenario. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 42 | `test_input_discovery_skips_hidden_and_disabled_duplicate_composers.scenario()` | Implements the scenario operation. |

## `tests/test_provider_input_discovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 54 | `test_provider_selector_catalogs_cover_current_rich_text_composers()` | Tests the provider selector catalogs cover current rich text composers scenario. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 7 | `FakeResponseLocator.__init__()` | Initializes a FakeResponseLocator instance. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `FakeResponseLocator.count()` | Counts the current object. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `FakeResponseLocator.nth()` | Implements the nth operation for FakeResponseLocator. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `FakeResponseLocator.is_visible()` | Returns whether visible. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `FakeResponseLocator.is_enabled()` | Returns whether enabled. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `FakeResponseLocator.inner_text()` | Implements the inner text operation for FakeResponseLocator. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `FakeResponsePage.__init__()` | Initializes a FakeResponsePage instance. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `FakeResponsePage.locator()` | Implements the locator operation for FakeResponsePage. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `FakeStopLocator.__init__()` | Initializes a FakeStopLocator instance. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 42 | `FakeStopLocator.count()` | Counts the current object. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `FakeStopLocator.is_visible()` | Returns whether visible. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 50 | `FakeStopPage.__init__()` | Initializes a FakeStopPage instance. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 53 | `FakeStopPage.locator()` | Implements the locator operation for FakeStopPage. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 57 | `test_provider_extracts_the_response_added_after_submission()` | Tests the provider extracts the response added after submission scenario. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `test_provider_extracts_the_response_added_after_submission.scenario()` | Implements the scenario operation. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 70 | `test_provider_checks_async_stop_controls_without_using_async_generator_any()` | Tests the provider checks async stop controls without using async generator any scenario. |

## `tests/test_provider_response_extraction.py`

| Line | Function / method | Description |
|---:|---|---|
| 71 | `test_provider_checks_async_stop_controls_without_using_async_generator_any.scenario()` | Implements the scenario operation. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `FakeChatbot.__init__()` | Initializes a FakeChatbot instance. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `FakeChatbot.open()` | Implements the open operation for FakeChatbot. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `FakeChatbot.verify_page()` | Verifies page. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `FakeChatbot.start_conversation()` | Starts conversation. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `FakeChatbot.send_prompt()` | Sends prompt. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `FakeChatbot.wait_for_response()` | Waits for for response. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `FakeChatbot.extract_response()` | Extracts response. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `test_chatbot_reasoning_adapter_redacts_context_and_returns_only_proposal_data()` | Tests the chatbot reasoning adapter redacts context and returns only proposal data scenario. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `test_world_model_exports_serializable_evidence_for_checkpoint_and_learning()` | Tests the world model exports serializable evidence for checkpoint and learning scenario. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 44 | `test_agent_manager_assigns_and_rebinds_stable_task_ids()` | Tests the agent manager assigns and rebinds stable task ids scenario. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 55 | `test_orchestrator_uses_configured_reasoning_provider_only_through_validator()` | Tests the orchestrator uses configured reasoning provider only through validator scenario. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 63 | `Controller.test_orchestrator_uses_configured_reasoning_provider_only_through_validator.__init__()` | Initializes a Controller instance. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 64 | `Controller.test_orchestrator_uses_configured_reasoning_provider_only_through_validator.observe()` | Observes the current object. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 65 | `Controller.test_orchestrator_uses_configured_reasoning_provider_only_through_validator.execute()` | Executes the current object. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `Provider.test_orchestrator_uses_configured_reasoning_provider_only_through_validator.__init__()` | Initializes a Provider instance. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 69 | `Provider.test_orchestrator_uses_configured_reasoning_provider_only_through_validator.propose()` | Implements the propose operation for Provider. |

## `tests/test_reasoning_provider_integration.py`

| Line | Function / method | Description |
|---:|---|---|
| 77 | `test_orchestrator_uses_configured_reasoning_provider_only_through_validator.scenario()` | Implements the scenario operation. |

## `tests/test_registry_and_tasks.py`

| Line | Function / method | Description |
|---:|---|---|
| 5 | `test_registry_reports_configured_provider_names()` | Tests the registry reports configured provider names scenario. |

## `tests/test_registry_and_tasks.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `test_task_parser_detects_multi_provider_request()` | Tests the task parser detects multi provider request scenario. |

## `tests/test_registry_and_tasks.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `test_task_parser_selects_analysis_profile_and_avoids_provider_substrings()` | Tests the task parser selects analysis profile and avoids provider substrings scenario. |

## `tests/test_runtime_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `runtime()` | Implements the runtime operation. |

## `tests/test_runtime_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `test_response_control_signals_stop_without_reload_or_fallback()` | Tests the response control signals stop without reload or fallback scenario. |

## `tests/test_runtime_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `test_reload_control_signals_stop_without_another_read()` | Tests the reload control signals stop without another read scenario. |

## `tests/test_runtime_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 49 | `test_clipboard_control_signals_propagate_without_ocr()` | Tests the clipboard control signals propagate without ocr scenario. |

## `tests/test_runtime_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 64 | `test_optional_claude_provider_cannot_hide_control_signals()` | Tests the optional claude provider cannot hide control signals scenario. |

## `tests/test_runtime_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `test_runtime_upgrade_verifies_stages_activates_and_rolls_back()` | Tests the runtime upgrade verifies stages activates and rolls back scenario. |

## `tests/test_runtime_upgrade.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `test_runtime_upgrade_rejects_tampering_and_untrusted_versions()` | Tests the runtime upgrade rejects tampering and untrusted versions scenario. |

## `tests/test_settings.py`

| Line | Function / method | Description |
|---:|---|---|
| 4 | `test_default_settings_load()` | Tests the default settings load scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `test_state_transitions_are_recorded()` | Tests the state transitions are recorded scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `test_focusing_input_is_an_explicit_runtime_state()` | Tests the focusing input is an explicit runtime state scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `test_recovery_retries_after_failure()` | Tests the recovery retries after failure scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `test_recovery_retries_after_failure.operation()` | Implements the operation operation. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `test_recovery_retries_after_failure.recover()` | Implements the recover operation. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `test_recovery_rejects_invalid_retry_budgets()` | Tests the recovery rejects invalid retry budgets scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 50 | `test_recovery_survives_a_failed_reload_and_uses_the_remaining_read_attempt()` | Tests the recovery survives a failed reload and uses the remaining read attempt scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 58 | `test_recovery_exhaustion_preserves_the_last_read_error()` | Tests the recovery exhaustion preserves the last read error scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 69 | `test_recovery_does_not_consume_more_attempts_when_cancelled()` | Tests the recovery does not consume more attempts when cancelled scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 79 | `test_recovery_decisions_respect_the_attempt_budget()` | Tests the recovery decisions respect the attempt budget scenario. |

## `tests/test_state_and_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 83 | `test_conditional_actions_require_observation_before_retrying()` | Tests the conditional actions require observation before retrying scenario. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `FakeBrowser.start()` | Starts the current object. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `FakeProvider.__init__()` | Initializes a FakeProvider instance. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `FakeProvider.open()` | Implements the open operation for FakeProvider. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 28 | `FakeProvider.verify_page()` | Verifies page. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `FakeProvider.start_conversation()` | Starts conversation. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `FakeProvider.send_prompt()` | Sends prompt. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `FakeProvider.wait_for_response()` | Waits for for response. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `FakeProvider.extract_response()` | Extracts response. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 44 | `FakeProvider.recover()` | Implements the recover operation for FakeProvider. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 49 | `RecoveringProvider.__init__()` | Initializes a RecoveringProvider instance. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 54 | `RecoveringProvider.extract_response()` | Extracts response. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `RecoveringProvider.recover()` | Implements the recover operation for RecoveringProvider. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 65 | `FakeRegistry.__init__()` | Initializes a FakeRegistry instance. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 68 | `FakeRegistry.get()` | Retrieves the current object. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 73 | `test_runtime_executes_and_persists_a_single_provider_task()` | Tests the runtime executes and persists a single provider task scenario. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 74 | `test_runtime_executes_and_persists_a_single_provider_task.scenario()` | Implements the scenario operation. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 100 | `test_runtime_cancels_an_action_when_the_global_task_budget_expires()` | Tests the runtime cancels an action when the global task budget expires scenario. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 101 | `test_runtime_cancels_an_action_when_the_global_task_budget_expires.scenario()` | Implements the scenario operation. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 106 | `test_runtime_cancels_an_action_when_the_global_task_budget_expires.scenario.slow_operation()` | Implements the slow operation operation. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 116 | `test_runtime_records_recovery_and_reobserves_before_retrying_extraction()` | Tests the runtime records recovery and reobserves before retrying extraction scenario. |

## `tests/test_task_lifecycle.py`

| Line | Function / method | Description |
|---:|---|---|
| 117 | `test_runtime_records_recovery_and_reobserves_before_retrying_extraction.scenario()` | Implements the scenario operation. |

## `tests/test_task_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 6 | `test_task_manager_applies_selected_multi_provider_workflow()` | Tests the task manager applies selected multi provider workflow scenario. |

## `tests/test_task_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `test_task_manager_rejects_unknown_provider()` | Tests the task manager rejects unknown provider scenario. |

## `tests/test_task_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `test_task_manager_automatically_synthesizes_explicitly_selected_providers()` | Tests the task manager automatically synthesizes explicitly selected providers scenario. |

## `tests/test_task_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `test_task_manager_rejects_invalid_multi_provider_selection()` | Tests the task manager rejects invalid multi provider selection scenario. |

## `tests/test_task_manager.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `test_task_manager_rejects_duplicate_providers()` | Tests the task manager rejects duplicate providers scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `test_clear_followups_stay_in_current_project()` | Tests the clear followups stay in current project scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 32 | `test_unrelated_creation_and_explicit_new_do_not_edit_old_project()` | Tests the unrelated creation and explicit new do not edit old project scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 41 | `test_shared_generic_words_do_not_connect_unrelated_subjects()` | Tests the shared generic words do not connect unrelated subjects scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 47 | `test_ambiguous_requests_need_classification_or_explicit_control()` | Tests the ambiguous requests need classification or explicit control scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 51 | `test_explicit_controls_and_existing_object_names()` | Tests the explicit controls and existing object names scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 63 | `test_clear_intent_does_not_request_another_chat()` | Tests the clear intent does not request another chat scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 64 | `test_clear_intent_does_not_request_another_chat.forbidden()` | Implements the forbidden operation. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 72 | `test_ambiguous_intent_uses_injected_request_and_bounded_validation()` | Tests the ambiguous intent uses injected request and bounded validation scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 74 | `test_ambiguous_intent_uses_injected_request_and_bounded_validation.request()` | Implements the request operation. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 88 | `test_provider_failure_and_invalid_fallback_remain_uncertain()` | Tests the provider failure and invalid fallback remain uncertain scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 89 | `test_provider_failure_and_invalid_fallback_remain_uncertain.failed()` | Implements the failed operation. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 91 | `test_provider_failure_and_invalid_fallback_remain_uncertain.invalid()` | Implements the invalid operation. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 93 | `test_provider_failure_and_invalid_fallback_remain_uncertain.slow()` | Implements the slow operation. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 101 | `test_permission_denial_is_not_swallowed()` | Tests the permission denial is not swallowed scenario. |

## `tests/test_task_relation.py`

| Line | Function / method | Description |
|---:|---|---|
| 102 | `test_permission_denial_is_not_swallowed.denied()` | Implements the denied operation. |

## `tests/test_team_diagnostics.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `Member.__init__()` | Initializes a Member instance. |

## `tests/test_team_diagnostics.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `Member.ask()` | Implements the ask operation for Member. |

## `tests/test_team_diagnostics.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `test_smoke_verifies_each_provider_and_persists_a_labelled_report()` | Tests the smoke verifies each provider and persists a labelled report scenario. |

## `tests/test_team_diagnostics.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `test_smoke_does_not_pass_with_only_one_provider()` | Tests the smoke does not pass with only one provider scenario. |

## `tests/test_team_diagnostics.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `test_smoke_reports_partial_when_a_selected_profile_never_launched()` | Tests the smoke reports partial when a selected profile never launched scenario. |

## `tests/test_team_diagnostics.py`

| Line | Function / method | Description |
|---:|---|---|
| 63 | `test_smoke_rejects_stale_incorrect_or_noncontract_replies()` | Tests the smoke rejects stale incorrect or noncontract replies scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `test_json_code_fence_preserves_escapes_and_rejects_surrounding_prose()` | Tests the json code fence preserves escapes and rejects surrounding prose scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 21 | `plan()` | Plans the current object. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `test_invalid_dependency_plans_are_rejected()` | Tests the invalid dependency plans are rejected scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `PartClient.__init__()` | Initializes a PartClient instance. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `PartClient.ask()` | Implements the ask operation for PartClient. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 72 | `test_parts_run_concurrently_honour_dependencies_and_deliver_tagged_messages()` | Tests the parts run concurrently honour dependencies and deliver tagged messages scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 94 | `test_unsigned_tab_is_skipped_for_entire_task()` | Tests the unsigned tab is skipped for entire task scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 99 | `test_unsigned_tab_is_skipped_for_entire_task.probe()` | Implements the probe operation. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 112 | `test_board_mail_survives_restart_and_cannot_target_unknown_members()` | Tests the board mail survives restart and cannot target unknown members scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 145 | `test_software_analysis_preserves_explicit_choice()` | Tests the software analysis preserves explicit choice scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 152 | `test_part_handoff_only_when_original_was_certified_unsent()` | Tests the part handoff only when original was certified unsent scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 156 | `Member.test_part_handoff_only_when_original_was_certified_unsent.__init__()` | Initializes a Member instance. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 158 | `Member.test_part_handoff_only_when_original_was_certified_unsent.ask()` | Implements the ask operation for Member. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 188 | `test_cli_board_messages_do_not_launch_browsers()` | Tests the cli board messages do not launch browsers scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 190 | `test_cli_board_messages_do_not_launch_browsers.forbidden()` | Implements the forbidden operation. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 202 | `test_json_presentation_unwrap_preserves_data_and_rejects_prose()` | Tests the json presentation unwrap preserves data and rejects prose scenario. |

## `tests/test_team_parts.py`

| Line | Function / method | Description |
|---:|---|---|
| 212 | `test_reuse_complete_parts_requires_exact_request_and_resolved_receipts()` | Tests the reuse complete parts requires exact request and resolved receipts scenario. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `test_understanding_routes_simple_and_collaborative_tasks()` | Tests the understanding routes simple and collaborative tasks scenario. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `test_plan_contains_bounded_verifiable_youtube_steps()` | Tests the plan contains bounded verifiable youtube steps scenario. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 43 | `Adapter.__init__()` | Initializes a Adapter instance. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 46 | `Adapter.execute()` | Executes the current object. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 50 | `Adapter.verify()` | Verifies the current object. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 55 | `test_coordinator_persists_verified_completion()` | Tests the coordinator persists verified completion scenario. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 76 | `test_browser_team_adapter_returns_structured_verified_result()` | Tests the browser team adapter returns structured verified result scenario. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 79 | `test_browser_team_adapter_returns_structured_verified_result.runner()` | Implements the runner operation. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 96 | `_answer()` | Implements the answer operation. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 100 | `test_checksum_requests_have_deterministic_bounded_plan()` | Tests the checksum requests have deterministic bounded plan scenario. |

## `tests/test_universal_mission.py`

| Line | Function / method | Description |
|---:|---|---|
| 109 | `test_checksum_adapter_rejects_paths_outside_workspace()` | Tests the checksum adapter rejects paths outside workspace scenario. |

## `tests/test_universal_router.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `Broker.assess()` | Implements the assess operation for Broker. |

## `tests/test_universal_router.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `Service.__init__()` | Initializes a Service instance. |

## `tests/test_universal_router.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `Service.ensure()` | Ensures the current object. |

## `tests/test_universal_router.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `test_router_acquires_missing_capability_then_retries_execution()` | Tests the router acquires missing capability then retries execution scenario. |

## `tests/test_universal_router.py`

| Line | Function / method | Description |
|---:|---|---|
| 35 | `test_router_fails_closed_when_acquisition_is_rejected()` | Tests the router fails closed when acquisition is rejected scenario. |

## `tests/test_universal_router.py`

| Line | Function / method | Description |
|---:|---|---|
| 46 | `_record()` | Records the current object. |

## `tests/test_video_capability.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `test_video_paths_cannot_escape_sandbox()` | Tests the video paths cannot escape sandbox scenario. |

## `tests/test_video_capability.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `test_video_builder_requires_ffmpeg()` | Tests the video builder requires ffmpeg scenario. |

## `tests/test_village_blender_smoke.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `test_real_blender_stages_and_render()` | Tests the real blender stages and render scenario. |

## `tests/test_village_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `test_queue_and_status_do_not_start_browser()` | Tests the queue and status do not start browser scenario. |

## `tests/test_village_cli.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `test_queue_and_status_do_not_start_browser.forbidden()` | Implements the forbidden operation. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `test_project_revision_and_request_persist_after_reopen()` | Tests the project revision and request persist after reopen scenario. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `test_request_order_filters_and_project_isolation()` | Tests the request order filters and project isolation scenario. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `test_unfinished_revision_does_not_replace_latest_verified_revision()` | Tests the unfinished revision does not replace latest verified revision scenario. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 66 | `test_cross_project_links_fail_without_partial_updates()` | Tests the cross project links fail without partial updates scenario. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 85 | `test_events_preserve_structured_payload_and_sql_text()` | Tests the events preserve structured payload and sql text scenario. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 102 | `test_checkpoint_snapshot_recovery_and_project_ownership()` | Tests the checkpoint snapshot recovery and project ownership scenario. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 123 | `test_concurrent_cli_requests_are_not_lost()` | Tests the concurrent cli requests are not lost scenario. |

## `tests/test_village_project_store.py`

| Line | Function / method | Description |
|---:|---|---|
| 138 | `test_blank_or_nontext_objectives_and_requests_are_rejected()` | Tests the blank or nontext objectives and requests are rejected scenario. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `village_runtime()` | Implements the village runtime operation. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `village_runtime.ask()` | Implements the ask operation. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `village_runtime.execute()` | Executes the current object. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `test_revision_reuses_prefix_and_keeps_original()` | Tests the revision reuses prefix and keeps original scenario. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 77 | `test_unavailable_request_is_unresolved()` | Tests the unavailable request is unresolved scenario. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 90 | `test_planned_revision_survives_crash_before_seed()` | Tests the planned revision survives crash before seed scenario. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 105 | `test_render_downgrade_is_not_reported_as_final_quality()` | Tests the render downgrade is not reported as final quality scenario. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 109 | `test_render_downgrade_is_not_reported_as_final_quality.flaky()` | Implements the flaky operation. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 124 | `test_revision_validation_rejects_unbounded_changes()` | Tests the revision validation rejects unbounded changes scenario. |

## `tests/test_village_projects.py`

| Line | Function / method | Description |
|---:|---|---|
| 134 | `test_only_one_worker_can_write_a_project()` | Tests the only one worker can write a project scenario. |

## `tests/test_village_projects_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `test_adopted_completed_checkpoint_has_durable_snapshot()` | Tests the adopted completed checkpoint has durable snapshot scenario. |

## `tests/test_village_projects_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 40 | `test_unseeded_child_repairs_parent_artifact_before_fork()` | Tests the unseeded child repairs parent artifact before fork scenario. |

## `tests/test_village_projects_recovery.py`

| Line | Function / method | Description |
|---:|---|---|
| 85 | `test_parseable_invalid_checkpoint_restores_database_snapshot()` | Tests the parseable invalid checkpoint restores database snapshot scenario. |

## `tests/test_village_surface_blender.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `test_real_blender_surface_controls_and_footprints()` | Tests the real blender surface controls and footprints scenario. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `Provider.prepare_conversation()` | Prepares conversation. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `Provider.open()` | Implements the open operation for Provider. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 11 | `Provider.verify_page()` | Verifies page. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `Provider.start_conversation()` | Starts conversation. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `Provider.send_prompt()` | Sends prompt. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 14 | `Provider.wait_for_response()` | Waits for for response. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 15 | `Provider.remember_conversation()` | Implements the remember conversation operation for Provider. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `Provider.extract_response()` | Extracts response. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 22 | `test_resume_skips_completed_stages_and_detects_tampering()` | Tests the resume skips completed stages and detects tampering scenario. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `test_resume_skips_completed_stages_and_detects_tampering.execute()` | Executes the current object. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 51 | `test_config_rejects_unbounded_and_non_integer_values()` | Tests the config rejects unbounded and non integer values scenario. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 56 | `test_village_routing()` | Tests the village routing scenario. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 62 | `test_website_pause_prevents_execution()` | Tests the website pause prevents execution scenario. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 64 | `PausingProvider.test_website_pause_prevents_execution.extract_response()` | Extracts response. |

## `tests/test_village_workflow.py`

| Line | Function / method | Description |
|---:|---|---|
| 67 | `test_website_pause_prevents_execution.execute()` | Executes the current object. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `FakeStreamingTransport.__init__()` | Initializes a FakeStreamingTransport instance. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 23 | `FakeStreamingTransport.connect()` | Implements the connect operation for FakeStreamingTransport. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 29 | `FakeStreamingTransport.stream_microphone()` | Implements the stream microphone operation for FakeStreamingTransport. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `FakeStreamingTransport.disconnect()` | Implements the disconnect operation for FakeStreamingTransport. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `FakeStreamingTransport.health_check()` | Implements the health check operation for FakeStreamingTransport. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `runtime()` | Implements the runtime operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 38 | `runtime.runner()` | Implements the runner operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `test_partial_turn_updates_ui_but_never_creates_mission()` | Tests the partial turn updates ui but never creates mission scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 49 | `test_partial_turn_updates_ui_but_never_creates_mission.scenario()` | Implements the scenario operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `test_final_turn_creates_one_runtime_mission_and_dashboard_trace()` | Tests the final turn creates one runtime mission and dashboard trace scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 61 | `test_final_turn_creates_one_runtime_mission_and_dashboard_trace.scenario()` | Implements the scenario operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 74 | `test_low_confidence_and_sensitive_turns_do_not_execute_without_confirmation()` | Tests the low confidence and sensitive turns do not execute without confirmation scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 75 | `test_low_confidence_and_sensitive_turns_do_not_execute_without_confirmation.scenario()` | Implements the scenario operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 86 | `test_connection_retries_cleanup_and_minimal_persistence()` | Tests the connection retries cleanup and minimal persistence scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 87 | `test_connection_retries_cleanup_and_minimal_persistence.scenario()` | Implements the scenario operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 97 | `test_interrupt_intents_have_deterministic_priority()` | Tests the interrupt intents have deterministic priority scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 104 | `test_voice_approval_fails_closed_without_independent_authorizer()` | Tests the voice approval fails closed without independent authorizer scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 105 | `test_voice_approval_fails_closed_without_independent_authorizer.scenario()` | Implements the scenario operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 113 | `test_voice_control_plane_reconnects_a_paused_session()` | Tests the voice control plane reconnects a paused session scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 115 | `test_voice_control_plane_reconnects_a_paused_session.scenario()` | Implements the scenario operation. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 129 | `test_voice_resume_transitions_paused_mission_and_emits_wakeup()` | Tests the voice resume transitions paused mission and emits wakeup scenario. |

## `tests/test_voice.py`

| Line | Function / method | Description |
|---:|---|---|
| 130 | `test_voice_resume_transitions_paused_mission_and_emits_wakeup.scenario()` | Implements the scenario operation. |

## `tests/test_voice_dashboard_configuration.py`

| Line | Function / method | Description |
|---:|---|---|
| 16 | `test_dashboard_configures_and_controls_voice_without_exposing_key()` | Tests the dashboard configures and controls voice without exposing key scenario. |

## `tests/test_voice_dashboard_configuration.py`

| Line | Function / method | Description |
|---:|---|---|
| 17 | `test_dashboard_configures_and_controls_voice_without_exposing_key.scenario()` | Implements the scenario operation. |

## `tests/test_voice_dashboard_configuration.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `test_dashboard_configures_and_controls_voice_without_exposing_key.scenario.factory()` | Implements the factory operation. |

## `tests/test_voice_dashboard_configuration.py`

| Line | Function / method | Description |
|---:|---|---|
| 65 | `test_dashboard_voice_configuration_is_validated()` | Tests the dashboard voice configuration is validated scenario. |

## `tests/test_voice_dashboard_configuration.py`

| Line | Function / method | Description |
|---:|---|---|
| 86 | `test_dashboard_rejects_non_finite_voice_confidence()` | Tests the dashboard rejects non finite voice confidence scenario. |

## `tests/test_vscode_worker.py`

| Line | Function / method | Description |
|---:|---|---|
| 8 | `test_coordination_packet_is_browser_authorized()` | Tests the coordination packet is browser authorized scenario. |

## `tests/test_vscode_worker.py`

| Line | Function / method | Description |
|---:|---|---|
| 19 | `test_coordination_packet_rejects_path_escape()` | Tests the coordination packet rejects path escape scenario. |

## `tests/test_vscode_worker.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `test_validation_rejects_unapproved_commands()` | Tests the validation rejects unapproved commands scenario. |

## `tests/test_vscode_worker.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `test_delegate_rejects_unknown_worker()` | Tests the delegate rejects unknown worker scenario. |

## `tests/test_vscode_worker.py`

| Line | Function / method | Description |
|---:|---|---|
| 39 | `test_workspace_path_rejects_escape()` | Tests the workspace path rejects escape scenario. |

## `tests/test_vscode_worker.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `test_extension_id_is_validated()` | Tests the extension id is validated scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 12 | `test_keyboard_transitions_hotkey_and_private_printable_keys()` | Tests the keyboard transitions hotkey and private printable keys scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 13 | `test_keyboard_transitions_hotkey_and_private_printable_keys.scenario()` | Implements the scenario operation. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 24 | `test_keyboard_privacy_always_redacts_sensitive_windows()` | Tests the keyboard privacy always redacts sensitive windows scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 30 | `test_mouse_derives_button_drag_target_and_double_click_events()` | Tests the mouse derives button drag target and double click events scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 31 | `test_mouse_derives_button_drag_target_and_double_click_events.scenario()` | Implements the scenario operation. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 51 | `test_device_audio_session_and_notification_adapters_emit_real_diffs()` | Tests the device audio session and notification adapters emit real diffs scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 52 | `test_device_audio_session_and_notification_adapters_emit_real_diffs.scenario()` | Implements the scenario operation. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 72 | `test_paused_bus_retains_pending_events_until_resume()` | Tests the paused bus retains pending events until resume scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 73 | `test_paused_bus_retains_pending_events_until_resume.scenario()` | Implements the scenario operation. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 86 | `test_dispatch_rate_limit_and_agent_risk_boundary()` | Tests the dispatch rate limit and agent risk boundary scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 87 | `test_dispatch_rate_limit_and_agent_risk_boundary.scenario()` | Implements the scenario operation. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 104 | `test_platform_factory_keeps_sensitive_detectors_disabled_by_default()` | Tests the platform factory keeps sensitive detectors disabled by default scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 110 | `test_sync_action_executor_is_timeout_guarded_without_blocking_loop()` | Tests the sync action executor is timeout guarded without blocking loop scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 111 | `test_sync_action_executor_is_timeout_guarded_without_blocking_loop.scenario()` | Implements the scenario operation. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 120 | `test_filesystem_rename_and_specific_window_transitions()` | Tests the filesystem rename and specific window transitions scenario. |

## `tests/test_windows_detector_building_blocks.py`

| Line | Function / method | Description |
|---:|---|---|
| 121 | `test_filesystem_rename_and_specific_window_transitions.scenario()` | Implements the scenario operation. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 9 | `test_bus_filters_deduplicates_routes_and_replays()` | Tests the bus filters deduplicates routes and replays scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 10 | `test_bus_filters_deduplicates_routes_and_replays.scenario()` | Implements the scenario operation. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 20 | `test_conditions_support_nested_logic_and_changes()` | Tests the conditions support nested logic and changes scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 25 | `test_filesystem_detector_emits_real_create_modify_delete()` | Tests the filesystem detector emits real create modify delete scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 26 | `test_filesystem_detector_emits_real_create_modify_delete.scenario()` | Implements the scenario operation. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 33 | `test_action_registry_permissions_risk_dry_run_retry_and_stop()` | Tests the action registry permissions risk dry run retry and stop scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 34 | `test_action_registry_permissions_risk_dry_run_retry_and_stop.scenario()` | Implements the scenario operation. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 36 | `test_action_registry_permissions_risk_dry_run_retry_and_stop.scenario.execute()` | Executes the current object. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 45 | `test_capability_report_is_explicit_not_fabricated()` | Tests the capability report is explicit not fabricated scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 48 | `test_agents_receive_only_subscribed_events_with_held_observation_permission()` | Tests the agents receive only subscribed events with held observation permission scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 49 | `test_agents_receive_only_subscribed_events_with_held_observation_permission.scenario()` | Implements the scenario operation. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 60 | `test_autowindow_one_call_actions_data_variables_and_stop()` | Tests the autowindow one call actions data variables and stop scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 72 | `test_privacy_safe_clipboard_mouse_display_and_process_detectors()` | Tests the privacy safe clipboard mouse display and process detectors scenario. |

## `tests/test_windows_event_system.py`

| Line | Function / method | Description |
|---:|---|---|
| 73 | `test_privacy_safe_clipboard_mouse_display_and_process_detectors.scenario()` | Implements the scenario operation. |


## `app/dashboard/static/app.js`

| Line | Function | Description |
|---:|---|---|
| 43 | `api()` | Sends a request to the dashboard API and returns its response. |
| 56 | `table()` | Builds an HTML table for dashboard records. |
| 61 | `overview()` | Renders the dashboard overview panel. |
| 72 | `voice()` | Renders voice configuration and status. |
| 79 | `perception()` | Renders perception and observation details. |
| 91 | `missions()` | Renders the missions list. |
| 102 | `missionDetail()` | Renders details for the selected mission. |
| 112 | `tasks()` | Renders the tasks list. |
| 116 | `agents()` | Renders the agent list. |
| 120 | `activity()` | Renders recent runtime activity. |
| 124 | `schedules()` | Renders schedules. |
| 128 | `actions()` | Renders recorded actions. |
| 132 | `approvals()` | Renders pending and past approvals. |
| 136 | `resources()` | Renders resource usage. |
| 142 | `hierarchy()` | Renders the agent hierarchy. |
| 148 | `world()` | Renders current world facts. |
| 150 | `health()` | Renders component health checks. |
| 151 | `recovery()` | Renders recovery events. |
| 152 | `security()` | Renders security decisions. |
| 153 | `leases()` | Renders capability leases. |
| 154 | `memory()` | Renders stored task memory. |
| 155 | `skills()` | Renders capability skill records. |
| 156 | `inventory()` | Renders authoritative runtime inventory. |
| 157 | `analytics()` | Renders runtime analytics. |
| 160 | `setConnection()` | Updates the dashboard connection indicator. |
| 167 | `render()` | Chooses and displays the selected dashboard view. |
| 184 | `loadPerceptionScreenshot()` | Loads the current perception screenshot. |
| 198 | `toast()` | Displays a temporary status message. |
| 206 | `refresh()` | Fetches dashboard state and refreshes the view. |
| 219 | `stream()` | Opens the event stream for live dashboard updates. |
| 240 | `command()` | Submits a dashboard command and refreshes its state. |
