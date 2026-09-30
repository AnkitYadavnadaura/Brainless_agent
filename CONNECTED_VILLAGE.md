# Connected village construction

In the nested `Brainless_agent` directory run `py run.py cli` and enter:

> Create a large interconnected village with houses, villas, trees, plants, gullies, stairs, gates, doors, ponds and drums. Refine every object for realism.

The persistent Chrome profile must be signed in to ChatGPT. Blender must be installed
or configured with `BLENDER_EXECUTABLE`. The nested CLI routes village/hamlet/settlement
requests to `VillageProjectWorkflow`, which wraps `ConnectedVillageWorkflow`. General 3D tasks use [ModelProjectWorkflow](MODEL_WORKFLOW.md). The older seven-stage checkpoints remain separate.

## Construction sequence

1. ChatGPT chooses scene/render settings and a district grid, with an art direction.
2. Python creates one shared world-coordinate border registry. Adjacent districts reference
   the same road portals, widths, elevations, verge constraints and style. Drainage channels
   align across columns, and bridges preserve the roadway across each channel.
3. Before each area, ChatGPT receives its bounds, fixed borders, neighbouring plans and
   the most recent twelve geometry observations from each already built neighbour.
4. The area plan lists individual objects in dependency order. Python checks footprint
   overlap, border clearance, road/verge clearance, drainage clearance and access paths.
   Invalid spatial plans receive up to three repair attempts with validation feedback.
5. Shared infrastructure is saved, then every object is created sequentially. Doors,
   stairs and gates attach to an earlier house/villa at runtime-owned coordinates.
6. After creation, ChatGPT uses the object's actual geometry report to choose detail,
   weathering and roughness settings. Its individual polish step gets another checkpoint.
7. Before each execution ChatGPT reviews the last result and can pause the run. All actions
   pass through the running child's existing permission-checked Blender tool.
8. Lighting and final rendering follow all district/object work.

Each district now checkpoints block ground, two gully road axes and drainage
separately. Houses and villas checkpoint foundation, four walls, roof and entrance
before refinement. All other objects have create/refine checkpoints. Checkpoint
counts depend on the chosen hierarchy and object kinds.

## Individual refinement

| Type | Refinement |
|---|---|
| House / villa | Roof tiles, windows, sills, gutters, chimney; villa veranda |
| Tree | Branches and individually modelled leaf sprays |
| Plants | Leaf geometry and stems |
| Door | Jambs and handle, attached to the parent's entrance |
| Stairs / gate | Worn-edge geometry modifiers |
| Drum | Raised bands, cap, metallic surface |
| Water | Banks, transmissive surface, reeds |

Materials belong to individual logical objects, so polishing one does not alter its neighbours.

## Checkpoints and resume

Outputs: `data/village-workspace/connected-villages/<objective-hash>/`.

- `checkpoint.json`: master borders, area plans, individual polish settings, job sequence,
  actual geometry reports and file hashes.
- Numbered `.blend`, `.json`, `.py` and `.log`: each execution's scene and evidence.
- `village.png`: final overview render.

Repeat the exact request to resume. Saved plans and polish decisions are reused;
completed jobs are skipped. SQLite snapshots recover missing/changed checkpoint
metadata, and damaged geometry is replayed from the last verified scene. Each step
is a separate saved `.blend`; retained revisions can consume substantial disk space.

The CLI uses one continuing ChatGPT conversation and one visible Blender worker
window. New components appear in sequence. General model primitives and transforms
are interpolated visibly; this is scripted simulation, not mouse impersonation.
See [MODEL_WORKFLOW.md](MODEL_WORKFLOW.md) for queued updates and status commands.
Standalone headless callers and smoke tests remain supported.

## Quality and current limits

GTA 6 equivalence is not an established result. This implementation uses procedural
geometry rather than scanned production assets. ChatGPT sees geometry metadata, not
rendered images, and cannot certify appearance. Base settlement elevation is flat to
guarantee continuity. Footprint/access validation is conservative axis-aligned geometry,
not a final mesh collision audit or navigation simulation. Ponds are local; the fixed
drainage network connects across district borders. Cycles denoising is enabled; GPU
configuration is not assumed. Production realism still needs authored/scanned assets,
close-up render inspection and visual art direction.

This route is wired to the nested CLI, not the dashboard or the outer duplicate tree.

## Verification

`py -m pytest tests/test_connected_village.py tests/test_village_workflow.py -q`

Set `BRAINLESS_BLENDER_SMOKE=1` to include real Blender verification. The test creates
and polishes all supported object types, builds adjacent infrastructure and renders an
overview in `data/connected-village-smoke/`. Planning/resume tests use a fake website
provider; they do not establish live ChatGPT UI reliability.
