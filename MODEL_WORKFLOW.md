# General 3D modelling workflow

This application is for repeated 3D modelling work: products, furniture, robots,
buildings, interiors, cities, villages and other scenes. A village is one specialized
builder, not the definition of the product.

Run from this directory:

```powershell
python run.py cli
```

Describe a Blender/3D task. General models and cities use `ModelProjectWorkflow`;
villages retain the district/block/gully/house/wall construction workflow. Both use
the same permission-checked Blender tool, durable project store and live worker.

## One active chat and one Blender window

Planning, checkpoint reviews, repairs and follow-up requests use one active project
chat at a time. After 20 submitted prompts, 100,000 conversation characters, or a
slow composer interaction, the next completed-turn boundary closes that owned tab
and opens a fresh chat. A bounded checkpoint summary carries the objective, current
revision, next step and recent evidence forward. The latest URL remains associated
with the project for resume. Unrelated tabs are preserved. Pending responses are
recovered from the same conversation rather than blindly resubmitted.

Blender stays open while actions arrive through a local queue. Primitive creation
and position/rotation/scale changes are animated in the viewport. Components of a
district appear in sequence, and the view smoothly follows the edited object throughout movement and scaling, including bevel/material edits to existing objects. It uses evaluated geometry bounds and preserves the scene camera. This is a
visible scripted simulation of modelling; it does not pretend to move a human's
mouse. Heavy geometry generation, saving and final rendering can pause UI refresh.

The CLI can reconnect to the visible worker after restarting. If the worker closes,
the next retry restarts Blender and loads the previous verified checkpoint. The
window stays open for inspection after a successful task.

## Revisions and checkpoints

Each model operation writes a numbered `.blend` and a geometry report. General-model chat reviews cover up to eight upcoming actions, reducing browser traffic without removing operation checkpoints. SQLite stores
the plan, queue, progress, errors and latest checkpoint snapshot. Updated models
start from the previous revision's scene; earlier revision files remain available.
The CLI asks for another update after a revision completes.

You can queue requests in a second terminal while the current revision is running:

```powershell
python run.py 3d update PROJECT_ID "Move Body to x=4, y=2, z=1 and rotate it 40 degrees around Z"
python run.py 3d status PROJECT_ID
python run.py 3d resume PROJECT_ID
```

Use the project ID printed at startup. Queued updates run after the current revision
finishes. `village` remains an alias for these management commands. Existing village
project paths remain compatible; the shared database is
`data/village-workspace/village-projects.sqlite3`. General model scenes are under
`data/village-workspace/model-projects/<project-id>/revision-<id>/`.

## Supported controls and recovery

The trusted operation set includes mesh primitives, named-object transforms,
materials, bounded bevels, onion domes, pointed arch frames, smoothing, cameras, lights, car templates, rendering and GLB
export. Plans use structured values; model-generated Python is not executed.
General revisions preserve the scene and target objects by name. Each iteration is
bounded to 180 operations, with further iterations available through updates.

Planning and execution errors receive bounded retries and validation feedback.
Damaged output is rebuilt from verified checkpoints. Persistent failures retain
resumable state; login challenges, permission refusals and user pauses are respected.
Unsupported modelling operations and missing assets cannot be repaired by pretending
they succeeded. Geometry reports verify execution, not artistic quality.

Final rendering prioritizes 256 samples and 2560px output by default. Detailed assets,
materials, lighting and art direction are still needed for cinematic realism. No
GTA6-equivalence claim or guarantee of zero failures is made.

## Verification

```powershell
python -m pytest tests/test_model_workflow.py tests/test_browser_conversations.py tests/test_village_projects.py -q
$env:BRAINLESS_BLENDER_LIVE_SMOKE='1'
python -m pytest tests/test_model_workflow.py::test_one_visible_blender_process_for_multiple_steps -q
```

The opt-in live test opens its own Blender window, verifies process reuse and recovery,
then closes only that test process.


## Task recognition and planning repair

Natural follow-ups are matched to the current project. For example, `make dome
larger` edits the Taj Mahal, while `create a sports car in Blender` starts a separate
project. The last selected project persists across CLI restarts. Ambiguous requests
are classified against the current objective; if intent remains unclear, use
`/update TEXT` or `/new TEXT`. `/new` also creates a fresh project for a repeated
subject without discarding the old scenes. An explicit `3d resume PROJECT_ID` keeps
its chosen project and is never rerouted to a different recent project.

Bevel accepts `width` or the common alias `amount` (0..10) and `segments` (1..12).
Architectural plans can use `add_dome` and `add_arch` with name, location, rotation
and scale. `add_dome` has unit radius, a two-unit height and its base at local Z=0;
`add_arch` is a pointed frame two units wide and three units tall, depth .3.

A valid executable plan can proceed with recorded detail limitations. Such output
is marked `needs_attention`, so approximate geometry is not represented as exact
or fully detailed. If initial Taj Mahal planning fails validation three times, a
validated procedural starter provides a terrace, mausoleum, central and corner
domes, four minarets, arch frames, reflecting pool, garden elements, camera and
lighting. It is an approximation, not a survey-accurate architectural reproduction.

Resume the reported Taj Mahal project from this directory:

```powershell
python run.py 3d resume 77c822f50bcf630f6ce0
```
