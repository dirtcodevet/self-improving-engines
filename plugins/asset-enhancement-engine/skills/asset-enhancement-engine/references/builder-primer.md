# Builder primer: what the engine already has (read this first; open a file only for the part you use)

Written 2026-10-19 for rapid-shot builders (the person's D26): a fresh builder used to read ~1 M characters before
building. This page is the map; it does not say how to solve an issue. Root: `<project>`.

## The method in four lines (`engine/SKILL.md` E9; `engine/references/target-loop.md`)
- No fact about the model without its measurement. Prove a new descriptor once on a known shape at the mesh's noise.
- Story in words, then descriptors, ranked targets (input > reference measured the same way > cited > story band),
  smooth handles that are real mechanisms, `solve`, the same table before and after.
- A job that changes one region solves on that REGION (`loop/region.py`): 24x faster per evaluation on the torso.
  It checks there too: prove nothing outside the region moved (one diff against the last checked state), check the
  region and a border on each try, and run the whole-model checks once per accepted stage and before showing. A fault
  found outside the region is recorded in the case's `KNOWN_FAULTS.md`, then fixed and re-measured on its own, never
  accepted (`skills/recursive-improvement` A28, items 6, 8, 9).
- Every fix is a recipe stage that replays; no Blender shape tools; never the live Blender (ports 9876/9877).

## The loop (`engine/loop/`, import as `from loop.core import ...` with `engine` on sys.path)
| Module | What you call |
|---|---|
| `core.py` | `Target(key, value, sd, source, rank, weight=1, inside_free=True)`; `measure(state, [(fn, kwargs)])`; `table`; `solve(state, handles, descriptors, targets, reg=0.05, max_nfev=60, diff_step=0.05, workers=8, jac_every=1)` -> (state, params, report); `save_report` |
| `region.py` | `Region(state, core_mask, margin_m)`: `.state` (sub-state: V, F, every per-vertex array sliced), `.core`, `.ids`, `.local(full_ids)`, `.put(full, sub)` (asserts only the core moved); `solve_region(state, core, make(sub, R) -> (handles, descriptors), targets, margin_m)`. Margin must cover what handles and descriptors read past the core (NormalBumps: 2 rings) |
| `shape.py` | descriptors `profile_arcs` (a profile's convex/concave arcs), `limb_sections` (section flat share, aspect, curvature jump), `state_value`; handles `NormalBumps(state, region, centres, bound_m)` (biharmonic, smooth by construction), `SliceBend` (body bending about horizontal axes, carriers, rigid bands), `RigidTurn` |
| `rigstate.py` | `load_pack(dir)`, `posed_state(pk, total_deg)`, `posed_change_to_keys(pk, st, V_new, side_sign)`, `save_keys`: pose in numpy exactly as Blender does; posed fixes become corrective keys |
| `relief.py` | skin micro-relief from cited numbers (furrows, plateaus, follicles), its statistics, a handle, tile export |
| `recipe.py` | `python engine/loop/recipe.py <recipe.json> [--only S] [--from S] [--no-cache]`: replays stages from the base, caches unchanged ones, Blender sweep, fold gate, vs reference, writes `runs/<id>/card.json` |
| `job.py` | the generic recipe stage: `python engine/loop/job.py <job.json> <in_pack> <out_pack>` runs a spec's steps (catalogue ops) on a pack; built-in ops `solve` (region + descriptors + targets + handles by name) and `measure`; `"$var:<name>"`, `"$core"`, `"$mask:<k>"` references (docstring) |
| `catalogue.py`, `lib/` | named pieces: `@descriptor`, `@handle`, `@op` register them; `python engine/loop/catalogue.py` lists what exists. A missing piece is added to `lib/` (with its proof) and is then reusable by name |
| `pack_io.py` | `Pack(dir)`: `npz`, `json`, `state`, `put_state`, `set_npz`, `set_json`, `write_file`, `save(out)`; `same_pack(a, b)` compares two packs file by file |
| `test_*.py` | proofs of the above; copy their pattern for a new descriptor's proof |

A `state` is a dict: `"V"` (n,3) float, `"F"` (m,3), plus any per-vertex masks (n,) you add.

## Instruments and checks (`engine/tools/`, `engine/checks/`)
- `section_curvature.py`: `profiles(V, F, centre, axis, ref_dir, angles_deg, inner)` -> curvature along the real skin
  curve on planes through a feature's axis.
- `surface_scan.py`: whole-skin anomaly patches (DENT proven; FLAT/BUMP/CREASE/ASYMMETRY/STEP candidates). Its
  smoothing uses the global mean edge (on the arms "5 mm" acts like ~15 mm): known limit.
- `surface_analysis.py`, `surface_fairing.py` (bi-Laplacian fairing), `contact_crease.py` (`revert_crossings`),
  `body_measure.py` (pack measurements), `posed_correctives.py`, `fit_to_reference.py`.
- `render_relief_bl.py` evaluates a pack's render-time relief in background Blender.
- `checks/folds.py`: folded faces; `compare(result, reference)` is the build gate (no new folds).
- `build_base_torso.py`: builds a pack into Blender (the recipe's verify and the orchestrator's renders use it).
- The Translator (the person's name; first called "the language tool"), `part_frame.py` with `part_frame_view.html`:
  part frames in cm with skin-following addresses.
  - `build <job.json>`: a job file binds a model's mesh and inputs to the definitions in
    `engine/packs/<domain>/part_frames.json`; example `cases/woman2/parts/job.json`.
  - `resolve <part>.npz "<address>"`: where a pasted address lands (the part is rebuilt first if it is stale).
  - `prove`: the tool's own checks.
  - Meshes from Blender: `bl_export_mesh.py` (one object), `bl_export_scene.py` (every object of any file Blender opens).
- Any object, kept current: `language.py` (build L1).
  - `auto <model|image> --case cases/<name> --pack <domain> [--up +z --front -y]`: segment, name (pack words in
    `engine/packs/<domain>/language.json`: generic, masonry, creature), define, build; open
    `cases/<name>/language/index.html` or `object.html`; `object.png` is the agents' picture of the parts.
  - `resolve cases/<name> "<lines>"`: addresses naming any part; `rename`, `cut`, `merge`: the person's corrections.
  - `status` / `sync` / `watch`: what is stale and rebuilding it (every job in cases/); `pack_io.Pack.save` and
    `recipe.py` call `notify` themselves.
  - `change-test <case> <new model> --work <dir>` / `compare`: what survives a model change; `prove`: planted objects.
- `pose_study_bl.py` / `pose_study.py`: pose a body at given arm angles and measure crossings, creases, stretched
  sheets, joint travel and nipple travel per zone (woman2 build 12).
- `vendor.py`: loads the tools kept in `engine/vendor/` (Pose Shape Keys, Robust Weight Transfer, OpenSim with the
  thoracoscapular shoulder model), in background factory-startup Blender only.

## Packs
- A pack folder holds the model's files (skin, weights, rig, keys, shading, maps, measurements); its `pack.json` names
  the current version. `pack_io.Pack` reads and writes them. Background Blender:
  `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python <script> -- <args>`
  (its Python has numpy, not scipy).

## The rapid-shot workflow (the case's `recipe/` folder)
- Brief: `ISSUE_NN_*.md` (issue, the person's decisions, conditions, report). Queue and order: `QUEUE.md`.
- Recipe: `torso_recipe.json` (stages from base v5; each stage `python <script> <in_pack> <out_pack>`, an `out_pack`, a
  `report`); stage scripts in `stages/`.
- Cited data: `engine/packs/human/references/*.md` (each starts with a short summary and a descriptor list; read the
  sections your issue names). Tool record: `engine/log/TOOLMAKING.md` (add a row for a new or changed tool).
