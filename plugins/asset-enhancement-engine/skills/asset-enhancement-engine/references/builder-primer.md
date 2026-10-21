# Builder primer: what the engine already has (read this first; open a file only for the part you use)

**Before you start:** `python engine/tools/build_log.py <words of your task>` prints a short ranked list of earlier builds
(id, title, keys) and the top one to three whole; `--id <id> [id ...]` prints entries whole (your brief names related builds
by id). **Before you report:** add your own entry at the end of `engine/log/BUILD_LOG.md` (its shape is at the top; no
approval needed: it is a record, not a rule).

Written 2026-10-19 (the person's D26), revised by A1, slimmed by A2 (2026-10-21). This page is the map; it does not say
how to solve an issue. Root: `<project>`. A big tool (over ~1,000 lines: part_frame,
language, surface_fairing, body_measure, fit_to_reference, and the viewer `part_frame_view.html`) starts with a function
index: read it and grep, not the whole file (`engine/tools/func_index.py` refreshes it).

## The method in four lines (`engine/SKILL.md` E9; `engine/references/target-loop.md`)
- No fact about the model without its measurement. Prove a new descriptor once on a known shape at the mesh's noise.
- Story in words, then descriptors, ranked targets (input > reference measured the same way > cited > story band),
  smooth handles that are real mechanisms, `solve`, the same table before and after.
- A job that changes one region solves on that REGION (`loop/region.py`): 24x faster per evaluation on the torso.
  It checks there too: prove nothing outside the region moved (one diff against the last checked state), check the
  region and a border on each try, and run the whole-model checks once per accepted stage and before showing. A fault
  found outside the region is recorded in the case's `KNOWN_FAULTS.md`, then fixed and re-measured on its own, never
  accepted (`skills/recursive-improvement` A28, items 6, 8, 9).
- Every change is a script that rebuilds its output from its inputs and replays (a recipe stage, or a build's stage
  scripts such as `cases/woman2/build13/a4_build.py`); no Blender shape tools; never the live Blender (ports 9876/9877).

## Measured findings (read the section your job touches before building)
- `engine/packs/human/findings.md`: Measuring; Shaping; Carrying detail; Junctions; Posing the shoulder; Volumes and
  sizes; The Translator on human bodies (incl. why pasted addresses miss across builds).
- Each pack's `language.json` "findings" block (generic, masonry, creature: build L1's segmentation and naming results).
- Cited data: `engine/packs/human/references/*.md` (each starts with a summary and a descriptor list).

## The loop, instruments and checks, by name (signatures, options, gotchas: `engine/references/tool-map.md`; grep the name)
- Loop, `engine/loop/`: `core.py` (Target, measure, table, solve), `region.py` (solve on one region), `shape.py`
  (descriptors; handles NormalBumps, SliceBend, RigidTurn), `rigstate.py` (posed states, keys), `relief.py` (skin micro-relief
  from cited numbers), `recipe.py` + `job.py` (replay a recipe's stages, cached), `catalogue.py` + `lib/` (named descriptors,
  handles, ops), `pack_io.py` (Pack read / write), `pack_carry.py` (the next pack from the last), `test_*.py` (proofs: copy
  their pattern). Three things are called `relief`: `loop/relief.py`, `surface_fairing.relief()` (a mesh's own fine relief
  above a local quadric), `body_measure.Body.relief`.
- Geometry, `engine/tools/`: `mesh_geom.py` (the ONE closest point, normals, Laplacian, curvature, dihedral edges: use it,
  don't write another), `bvh.py` (rays, nearest points, self-overlaps), `quad_grid.py` (quad walks, inset rings, layouts,
  `mirror_map`), `quad_relayout.py` (slide a quad mesh's vertices over its own surface), `surface_fairing.py` (fair, fill,
  relief, match_fill), `mound_resize.py`, `section_curvature.py`, `surface_scan.py`, `surface_analysis.py`,
  `contact_crease.py`, `body_measure.py`, `fit_to_reference.py`, `render_relief_bl.py`, `build_base_torso.py` (builds a pack;
  format 3 = whole body, rig, shape keys).
- Checks, `engine/checks/`: `surface_quality.py` (edge turn, roughness, quad stats, turned-over triangles, changed_region),
  `limb_flats.py` (the person's no-flats gate), `folds.py`. Shots, `engine/review/` (background Blender): `clay_pairs.py`,
  `pack_shots_bl.py`, `clay_sheet.py`.
- The Translator (the person's name: part frames in cm with skin addresses): `part_frame.py` + `part_frame_view.html`
  (build, resolve, prove; the Variance view, run outside a page by `variance_node.js`, proof `test_surface_variance.py`),
  `language.py` (any object: auto, resolve, rename, cut, merge, sync / status / watch, prove, home / open / pages; **run
  `regress` after any change to part_frame or language**), `part_features.py` (a head's ears, eyes, nose, lips),
  `translator_pages.py`, `bl_export_mesh.py` / `bl_export_scene.py` (meshes out of Blender).
- Posing and corrective shapes: `pose_correctives.py`, `pose_samples_bl.py`, `pose_study_bl.py` + `pose_study.py`,
  `posed_correctives.py`, `vendor.py` (Pose Shape Keys, Robust Weight Transfer, OpenSim: background factory Blender only).
- One subject's instruments stay with its case (the person's D30): woman2's `cases/woman2/lib/` (chest_wall, cup, limb_form),
  `build13/` (b13lib, b13pack, a2_measure, m_arm; `replay_check.py`), `build13b/` (rig, poses), `build13c/` (keys).

## Machine and harness (measured; each cost a builder minutes)
- Windows 11, 16 GB, 16 cores: size parallel jobs by memory (a 686k-vertex pack step ~3 GB, estimate). No `psutil`.
- System Python has numpy + scipy; Blender's Python has numpy only. Background Blender:
  `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python <script> -- <args>`.
  Give it ABSOLUTE output paths: a relative path in `-b` lands under Blender's own folder (renders were lost that way).
- Foreground `sleep` is blocked and a command over ~2 min is moved to the background: start long runs (proof suites,
  replays, renders) in the background and keep writing; you are told when they finish.
- Heredocs break on nested quotes (9 failures in one night): write the script to a file, then run it. A `\n` typed in
  a Python string inside a heredoc arrived as a real newline (A2, 3 times): write code with Write / Edit.
- Writing a whole new `.md` over an existing findings file is blocked: use Edit to add to it.
- `ProcessPoolExecutor` on Windows re-imports the main script in each worker: keep a script's work under
  `if __name__ == "__main__":`.

## Packs
- A pack folder holds the model's files (skin, weights, rig, keys, shading, maps, measurements); its `pack.json` names
  the current version. `pack_io.Pack` reads and writes them; `pack_carry.carry` makes the next one from the last.

## The rapid-shot workflow (the case's `recipe/` folder)
- Brief: `BUILD_<id>_*.md` (issue, the person's decisions, conditions, report; runs 1-5 used `ISSUE_NN_*.md`). Queue and
  order: `QUEUE.md`; cost and time per build: `COSTS.md`.
- `torso_recipe.json` replays the old torso line (stages from base v5 to v12, `stages/`); the new base (build 13 on)
  replays by its own stage scripts in `cases/woman2/build13/` (each pack's README says which).
- Tool record: `engine/log/TOOLMAKING.md` (a row for a new or changed tool). Lessons that are judgments go to
  `engine/log/METHOD.md` as candidates; the person approves lessons.
