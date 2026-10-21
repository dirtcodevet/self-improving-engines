# Tool map: what each engine tool does, how to call it, and what it gets wrong (grep the tool's name; open a file only for the part you use)

Moved out of `builder-primer.md` by build A2 (2026-10-21), unchanged: the primer lists every tool by name and points here
for the signatures, options and measured gotchas. Root: `<project>`. A big tool (over
~1,000 lines) starts with a function index: read it and grep, not the whole file (`engine/tools/func_index.py` refreshes
it; `part_frame_view.html` has one too, as an HTML comment).

## The loop (`engine/loop/`, import as `from loop.core import ...` with `engine` on sys.path)
| Module | What you call |
|---|---|
| `core.py` | `Target(key, value, sd, source, rank, weight=1, inside_free=True)`; `measure(state, [(fn, kwargs)])`; `table`; `solve(state, handles, descriptors, targets, reg=0.05, max_nfev=60, diff_step=0.05, workers=8, jac_every=1)` -> (state, params, report); `save_report` |
| `region.py` | `Region(state, core_mask, margin_m)`: `.state` (sub-state: V, F, every per-vertex array sliced), `.core`, `.ids`, `.local(full_ids)`, `.put(full, sub)` (asserts only the core moved); `solve_region(state, core, make(sub, R) -> (handles, descriptors), targets, margin_m)`. Margin must cover what handles and descriptors read past the core (NormalBumps: 2 rings) |
| `shape.py` | descriptors `profile_arcs`, `limb_sections` (section flat share, aspect, curvature jump; reads 0.67x of a true flat: test_limb_flats), `state_value`; handles `NormalBumps` (biharmonic), `SliceBend`, `RigidTurn` |
| `rigstate.py` | `load_pack(dir)`, `posed_state(pk, total_deg)`, `posed_change_to_keys(pk, st, V_new, side_sign)`, `save_keys` |
| `relief.py` | skin micro-relief from CITED numbers (furrows, plateaus, follicles), its statistics, a handle, tile export. Not the same as `surface_fairing.relief()` (a mesh's own fine relief above a local quadric) or `body_measure.Body.relief` |
| `recipe.py` | `python engine/loop/recipe.py <recipe.json> [--only S] [--from S] [--no-cache]`: replays stages from the base, caches unchanged ones, Blender sweep, fold gate, vs reference, `runs/<id>/card.json` |
| `job.py` | the generic recipe stage: `python engine/loop/job.py <job.json> <in_pack> <out_pack>` (catalogue ops; `solve`, `measure`) |
| `catalogue.py`, `lib/` | named pieces: `@descriptor`, `@handle`, `@op`; `python engine/loop/catalogue.py` lists what exists |
| `pack_io.py` | `Pack(dir)`: `npz`, `json`, `state`, `put_state`, `set_npz`, `set_json`, `write_file`, `save(out)`; `same_pack(a, b)` |
| `pack_carry.py` | a new pack from the last one with the skin moved: `carry(prev, out, V, note, copy)`, `a28_diff(V_prev, V, declared, masks)`, `depth_under` |
| `test_*.py` | proofs of the above; copy their pattern for a new descriptor's proof |

A `state` is a dict: `"V"` (n,3) float, `"F"` (m,3), plus any per-vertex masks (n,) you add.

## Instruments and checks (`engine/tools/`, `engine/checks/`, `engine/review/`)
- `mesh_geom.py`: the ONE closest point on triangles / on a mesh (`closest_on_mesh`, `MeshProj`), face and vertex
  normals, cotangent Laplacian and mean curvature, dihedral edges, polygon edges / fan triangles. Use these; don't
  write another. `bvh.py`: rays, nearest points, self-overlaps by Blender's BVH (background), safe in parallel.
- `quad_grid.py`: quad-grid walk, rectangles, boundary loops, inset rings (loops added in place), harmonic / mean-value /
  conformal layouts, UV charts; `mirror_map` (a mesh's topological mirror twin per vertex: walk a near-symmetric parent,
  e.g. the unsculpted base, and pass it as `init`), `grid_line` (an edge loop walked straight on).
- `quad_relayout.py` (13b): slide a quad mesh's vertices over its OWN surface (connectivity unchanged): poles to new
  places, loops onto curves (`relayout_surface`; the flat-layout `relayout` misplaces moves on deep curved patches),
  `resample` per-vertex fields, `quality` of quads. Hold sharp creases out of the free set or the chords cut them.
- `surface_fairing.py`: `fair` (umbrella bi-Laplacian band), `fill(V, F, free, weights="cotan", detail="keep")` (the
  smoothest patch, with the skin's fine relief carried back by default; proof `test_fill_detail.py`), `relief()` (each
  vertex's height above a local quadric), `scalar_fill`, `match_fill` (a region takes another surface's form, e.g. the
  other side mirrored; `test_match_fill.py`). `mound_resize.py`: a mound made smaller / larger by its smooth height
  above a wall (`test_mound_resize.py`); `resize_similar` keeps its proportions instead (the footprint and the fold move
  with it, a cap keeps its size; `test_mound_similar.py`, build 13a5).
- `checks/surface_quality.py`: edge turn, curvature roughness, quad stats, turned-over triangles, crossings near a
  region, `changed_region` (a changed region's soundness table). `checks/limb_flats.py`: the person's no-flats gate
  (limb section flat share, inner-arm clearance, armpit vault). `checks/folds.py`: `compare(result, reference)` (no new folds).
- `section_curvature.py` (`profiles` on planes through an axis), `surface_scan.py` (whole-skin anomaly patches; its
  smoothing uses the global mean edge: on the arms "5 mm" acts like ~15 mm), `surface_analysis.py`, `contact_crease.py`,
  `body_measure.py`, `posed_correctives.py`, `fit_to_reference.py`, `render_relief_bl.py`, `build_base_torso.py`.
- Shots (background Blender): `review/clay_pairs.py` (two skins, same camera and raking light, labelled pairs and
  same-pixel crops), `review/pack_shots_bl.py` (a pack's mesh in clay or its own skin material from any cameras),
  `review/clay_sheet.py` (PLYs from fixed views).
- The Translator (the person's name), `part_frame.py` + `part_frame_view.html`: part frames in cm with skin addresses.
  - `build <job.json>`; `resolve <part>.npz "<address>"` (the part is rebuilt first if stale); `prove`.
  - Meshes from Blender: `bl_export_mesh.py` (one object), `bl_export_scene.py` (every object of a file).
- Any object, kept current: `language.py` (L1-L3, A1).
  - `auto <model|image> --case cases/<name> --pack <domain> [--only PART,...]`: segment, name, define, build (the
    segmentation is cached; `--only` builds just those parts, so iterate on one part, then build all once).
  - `resolve`, `rename`, `cut`, `merge`; `status` / `sync` / `watch` over every job at any depth in cases/;
    `change-test` / `compare`; `prove [--only facets|creature|2d|current]`.
  - `regress`: woman2's hand-made parts rebuild identical and every pasted line of `build13/picks_*.md` resolves where
    the baseline says (`cases/woman2/translator_regress.json`). Run it after any change to part_frame or language.
  - Human bodies (L2): `--pack human`, `cases/human_l2/`. Pages (L3, `translator_pages.py`): `language.py home`,
    `open [what] [--print]`, `pages`.
  - A head's own parts (L4, `part_features.py`, the human pack's `features` block): ears, eyes, nose, lips and the
    inside of the mouth from the head's shape (height above its radial course, pockets, curvature), after the splits;
    four bodies and K1 in `cases/human_l4/`; proof `test_part_features.py`. Gaps: findings.md, "The head's own parts".
  - The Variance view (L5, L5b): every page's Variance button (V) colours the skin by its height against its own smooth
    form, with Size and Show from; the VARIANCE block of `part_frame_view.html`, run outside a page by
    `variance_node.js` (V/F, `info`, or `page`); proof `test_surface_variance.py` (A features, B 13a3's plate, C the
    sign in every frame). + is out of the body, so pass the page's `info`. Not `surface_fairing.relief()`.
- Corrective shapes (13c): `pose_correctives.py` (ARAP restore on a region, the breast under its skin envelope, contact
  pushes, posed fix -> rest key by J^-1, pose-space hat weights and their driver expressions; proof
  `test_pose_correctives.py`), `pose_samples_bl.py` (a format-3 pack posed by its controls with each vertex's skinning
  Jacobian), `bvh.inside` (skin inside the body by ray parity); `build_base_torso.py` format 3 builds a pack's
  `shape_keys` with drivers. woman2's keys and their layout: `cases/woman2/build13c/` (c1-c7). Contact is not solved.
- `pose_study_bl.py` / `pose_study.py` (pose at given arm angles, measure per zone; 13b: `"build_pack"` builds a format-3
  pack in place of a blend, mode `"controls"` poses named poses (bone rotations + control properties), `"skinning"`
  linear / dq / mix); `build_base_torso.py` format 3 (13b: the whole body, `rig3` = any bone list with drivers,
  constraints, control properties, a glide surface; sparse weights; linear + dual quaternion mixed by `dq_mix`);
  woman2's rig and test poses: `cases/woman2/build13b/` (r2_rig.py, r3_poses.py, r4_girdle.py); `vendor.py` (Pose Shape Keys, Robust
  Weight Transfer, OpenSim + thoracoscapular model, in background factory Blender only).
- One subject's instruments stay with its case (the person's D30): woman2's chest wall (`cases/woman2/lib/chest_wall.py`),
  cup sizing (`lib/cup.py`), limb form (`lib/limb_form.py`); build 13's bindings (`build13/b13lib.py`, `b13pack.py`,
  `a2_measure.py`, `m_arm.py`). Build 13's stages replay into a scratch folder and diff against what is stored:
  `python cases/woman2/build13/replay_check.py`.
