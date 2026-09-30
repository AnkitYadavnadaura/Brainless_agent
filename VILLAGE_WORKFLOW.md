# Staged village construction

To let all installed browser profiles collaborate through ChatGPT and Gemini,
use the [browser team workflow](BROWSER_TEAM.md). Add `--execute` to use that team
for the existing village/3D planning, review and recovery steps.

The CLI now uses the [connected district workflow](CONNECTED_VILLAGE.md). This document
describes the earlier seven-stage implementation, retained for existing callers and checkpoints.

For the current general 3D workflow, see [MODEL_WORKFLOW.md](MODEL_WORKFLOW.md).
It supports repeated updates for models, products, buildings, cities and villages.
The old example objective is not a product restriction or a quality guarantee.

Requests containing village, hamlet, or settlement select the staged village route.
Blender must be installed (or set `BLENDER_EXECUTABLE`) and the persistent Chrome
profile must be signed in to ChatGPT. Reasoning uses the ChatGPT website.

ChatGPT chooses a bounded configuration, then reviews factual metadata before
each stage: terrain, roads, buildings, architectural details, vegetation, lighting,
and render. The existing agent manager owns the child and checks each tool call.
Stage subdivision is sequential because stages share a scene. This route does not
use the general task-graph scheduler or parallel children.

The trusted procedural builder supplies gabled houses, foundations, porches,
windows, chimneys, gravel roads, surrounding trees, procedural bump materials,
Cycles denoising, physical sky, AgX, and an overview camera. The default planning
suggestion is 100 buildings, 240 trees, 1920px output and 64 samples. ChatGPT may
adjust these within the documented bounds in `village_workflow.py`. Rendering
uses Blender's available/default Cycles device; GPU acceleration is not assumed.

Outputs live in `data/village-workspace/villages/<objective-hash>/`:

- `00.blend` through `06.blend`: separate stage snapshots.
- `checkpoint.json`: configuration, completed stages, metadata and SHA-256 hashes.
- `village.png`: final render.
- Numbered JSON reports, scripts and logs: actual execution evidence.

Repeat the exact same request to resume. Verified stages are skipped. A failed
stage runs from its preceding snapshot; no completed scene is overwritten by a
later stage. Changed or missing checkpoint artifacts stop resume. To build a new
variation, change the request. Each Blender subprocess has a two-hour timeout.

This is a procedural environment foundation, not GTA 6 equivalent production
art. It does not provide scanned assets, detailed interiors, animated population,
traffic, authored textures, or visual critique of rendered images. ChatGPT reviews
metadata only and cannot certify appearance. Final quality needs visual review
and asset/art-direction work. The new workflow is wired to the nested CLI, not
the dashboard or outer duplicate project tree.

Tests: `python -m pytest tests/test_village_workflow.py tests/test_blender_planner.py
tests/test_blender_workflows.py -q`. For the real Blender smoke test, set
`BRAINLESS_BLENDER_SMOKE=1` and run `python -m pytest
tests/test_village_blender_smoke.py -q`; outputs go to `data/village-smoke`.
