---
name: asset-enhancement-engine
description: Turns one reference photo of an animal (quadrupeds; cats proven) into a proper Blender model - lofted anatomical body, engineered face (lidded eyes, opening mouth, teeth, tongue), groomed fur, whiskers, claws, a 60-bone rig and a demo animation - built live through the Blender MCP socket and gated by scored checks. Use when asked to make a Blender model of an animal from a photo, or to run another improvement round of this engine.
---

# Photo -> Blender creature (engine skill)

The memory of this engine. Read this, not old chats. Long-tail detail lives in `references/`.
Teaching log: `log/METHOD.md`. Process: the person's `recursive-improvement` skill (project copy with flagged
additions: the `recursive-improvement` plugin) and its companion the `engine-grounding` plugin. Items marked
(trial Ex) here are switchable in `flags.json`: `false` = ignore that item.

## How the build is ordered (trial E4, E5, E6 - approved by the person 2026-10-17; supersede the old all-at-once order)
- (trial E4) LAYERED BUILD: frame (simplified, form-giving - not a precise skeleton) -> muscle -> fat, skin and
  features -> hair roots and fur -> pigment -> rig and motion. One layer across the whole subject, section by
  section (head, neck, chest/shoulders, forelimbs, trunk, pelvis/hindlimbs, tail, paws), each section accepted
  before the next; a later layer never fixes an earlier one. Acceptance is defined before building; the person sees
  three milestones (form, skin, fur). Detail and the acceptance checks: `references/layered-build.md`.
- (trial E5) NO PAINTED ANATOMY: every shape, shadow and line comes from structure; paint only where real pigment
  is (nose leather colour, coat pigment). A feature must show in a colourless clay render. (R3g: the red lip line,
  the eye rings and the pasted-on nose triangle broke this.)
- (trial E6) FOLLICLE PALETTE: hair types with directly editable properties including colour along the shaft; a map
  on the skin says which types grow where; markings are where pigmented types grow. `references/follicle-palette.md`.
- Tools are chosen by result (e.g. the fur swatch test), not by habit.

## Pipeline (tools in `tools/`, one command: `tools/build_all.sh <case> <ver> [vox] [sdf|production|look]`)
1. **Reference prep** - `ref_mask.py` (seeded GrabCut), mark builder points (`ref_points.json`: eyes, nose, chin,
   ear tips, paw toe-fronts). Freeze one camera (`fit_camera.py` once, then `camera_frozen.json`).
2. **3D reference (optional, person's approval - uploads the photo)** - `rodin_ref.py` -> `ref_align.py` ->
   canonicalise -> `ref_measure.py`. See `references/generative-reference.md`.
3. **Priors** - list every dimension the photo CANNOT measure (depth along the view: muzzle projection, forehead
   slope, ear cup, torso volume...) and give each an anatomical prior (`priors.json`, sources in
   `references/cat-anatomy.md`); `checks/priors.py` gates them (R3c #50). Never let a primitive default fill one.
4. **Spec** (case folder) - trunk = `loft_y` from measured profiles, its closing end a tilted ellipsoid FITTED to the
   closing stations (`front_fit`); neck/legs/tail = `loft_curve` through joints, haunches `loft_z` measured sections;
   paws/toes; head from engineered parts (`eye_aperture`+lid shell, `slit_cavity` mouth with lip line, `pinna`
   ears - cupped shell, conch, Henry's notch; `ear_cone` is the old blade, R3c #56 - rhinarium + nostrils, philtrum
   cleft, lip lobes, whisker pads, temporalis). Muzzle DEPTH from the prior via `muzzle_warp` (also mapped in
   `mouth_geom` and the landmarks). Junction blends: `var_blend` (wide where a limb meets the body, narrow between
   limbs; measure first with `review/junction_sweep.py`). Feature sizes from photo TRACES, not by eye.
   Per-part fur depth via `with_fur`.
   The mouth's geometry has ONE definition (`tools/mouth_geom.py`) used by the SDF and every Blender-side tool;
   accessories that sit in the mouth (tongue) are seated from it, not hand-placed.
   **Local detail loop:** `part_lab.py` (one region, 0.25 mm, seconds) + `lab_view.py` + `lab_profile.py`.
   `photo_fit.py` fits head pose + paws to the photo with priors to the reference.
5. **Mesh** - `sdf_core.run` (auto-bounds) -> `import_mesh.py` -> `production_mesh.py` (voxel remesh + decimate +
   fidelity check).
6. **Look** - case `coat.py` (colour/rough/fur maps from landmarks), `materials.py`, case `look.py` (calibrated by
   `light_match.py` + `tone_match.py`), `groom.py` (comb field, tip-sampled colour, clumping, surface-attached).
   (trial E1) Hair is ZONED and LAYERED: coat writes zone / hair_lift / hair_clump / hair_rscale per vertex; groom grows a
   guard layer (zone-driven) over a short, dense, crimped, paler undercoat (R3d #61).
   (trial E3, off) Hair grows along a GROWTH FIELD: `photo_flow.py` measures the photo's fur direction (hair-scale
   detail, two scales so turns read), `hair_field.py` turns the hair-tract prior (`hair_tracts.py`) toward it on the
   skin and smooths without erasing turns; groom follows it when E3 is on.
7. **Rig + parts + motion** (only after structure is right - person, R3b) - `rig.py` (bone heat on a proxy + procedural face weights), `accessories.py`,
   `eevee_outputs.py`, `anim_idle.py`, `anim_check.py`.
8. **Gates** - `checks/checks.py` (topology, ground, eyes, proportions, coherence, lipline), `checks/multiview.py`
   (5 silhouettes + profiles + local surface deviation vs the 3D reference), photo probe + `diff_parts.py`.
   Scorer with the answer key lives outside the engine (`eval/`).
9. **Review** (gates catch gross errors; the review finds what a person sees) - `review/review.sh <case> <ver>`:
   seam FAIRNESS (`fairness.py`: curvature jumps at part junctions vs a seam-free baseline, attributed to parts;
   heat map + ZEBRA reflection-line renders centred on the worst bands), ALIGNMENT (`trace_photo.py` traces eyes,
   iris, pupils, nose leather, nostrils, mouth Y, head top, inner ears; the SAME tracer runs on a render from the
   frozen camera; `compare_features.py` = shape descriptors + overlay; `compare_regions.py` = colour dE, texture,
   contrast, fur flow per region), and a BLIND REVIEWER packet (`REVIEWER.md`: a fresh agent sees only the photo
   and renders, never scores or the person's notes). Acceptance: the review must reproduce the person's own review.
   Fast photo-camera checks without Blender: `review/project_mask.py` + `head_outline.py`. A 3-D reference the
   person supplies is an ANSWER KEY on the scorer side (`eval/`): measure the process against it, never copy it.

## Rules (each backed by a check that fails on a planted defect)
- The photo silhouette of a furry animal is the **fur envelope**: model skin, score `_env`.
- One view constrains two axes. Every iteration: turnaround (`views.py`) + `multiview.py`. Depth comes from a 3D
  reference or anatomy priors, never from the photo.
- Fix by **attribution** (`diff_parts.py`, multiview part blame), never by eyeballing a scalar.
- Eyes: lids are a shell lying on the globe; the cut goes only through that shell (`checks.eyes`).
- Subtractive details must cross the surface and be >= 2 voxels wide (`checks.topology`: no bubbles).
- SDF bounds derive from the primitives (`sdf_core.run` auto-bounds; `checks.topology` open edges).
- Score at **rest pose**; a probe/tool restores the exact prior state of everything it touches, and makes every
  state change INSIDE its try/finally (a crash between "hide" and "try" left the lights off for every later render).
- Closed-mouth frames: no tooth/tongue exposure (`anim_check.py` ray test), no skin inside eyeballs, fur attached.
- Rest pose = closed mouth: the slit is thin (gap_edge) through the whole lip zone (`slit_cavity lip_e`), thick only
  behind it; lip margins are smooth curves (`checks.lipline`: bend radius >= 2 mm, sawtooth <= 0.2 mm).
- A loft's closing end must continue the loft's own taper (no crease ring): `loft_y front_fit` (`checks.coherence`).
- (trial E2) A paint mask for a modelled part reads the part's OWN definition (exported in the landmarks) in the unwarped frame,
  and every count a stage prints is asserted non-empty: the nose leather was silently unpainted for 5 builds
  (`coat.py` assert; R3d #59).
- (PARKED by the person until the closed mouth is right) The OPEN mouth (widest jaw frame) is checked too: `tools/mouth_open_check.py` (taper < 0.85, tongue share > 0.08,
  both upper canines visible, RENDERED interior luminance > 0.35; provisional thresholds). Lower jaw tucked inside the
  upper lip (`sdf_core.jaw_warp`), lower-lip skin near the corners held up (`corner_hold`), teeth seated on the
  gum lines of `mouth_geom`, oral walls get a small glow (`oral` attribute) - a cavity is never lit by the key.

## Judgment lessons (approved by the person 2026-10-17, each switchable as Jx in `flags.json`; cite log)
- (J1) Blob primitives (smooth-min of ellipsoids) are wrong for mammal trunks/limbs: loft measured sections (R1, R2).
- (J2) When the 3D reference and the photo disagree, the photo wins for what it sees (tail, paws) (R2 #5).
- (J3) A low camera makes ray-ground constraints useless; check the grazing angle first (R2 #4).
- (J4) Muzzle reads as "cat" only with real anatomy: split upper lip, lobes over a recessed lower lip, corners under
  the eye, shield rhinarium with comma nostrils (R1 #5-7, person's anatomy question).
- (J5) Before editing a local artefact a fourth time, isolate it: `part_lab.py` or a unit test of the primitive
  (R2b #24, R2c #28-#29: both v26 artefacts were design faults visible in the first lab render).
- (J6) A formula needed by more than one tool lives in one module; copies drift (R2c #31).
- (J7) Instruments: follow `recursive-improvement` addition A3 (the person softened the strict version that stood
  here: "very strict ... could see possible breakage"). Evidence R3a #40, R3b #43-#44, R3c #51, R3d #64.
- (J8) One region per build; isolate in the lab first. v32-v34 changed warp + pads + lips + nose together and the gates
  moved in opposite directions (R3c).
- (J9) Build in the order structure -> appearance -> motion; the open mouth was built before the closed mouth was right
  and had to be parked (person, R3b).
- (J10) Before widening a junction blend, sweep it (`junction_sweep.py`): legs were too-narrow blends, but pads, jaw, tail
  root and ear bases got WORSE when widened - those parts were the wrong shape (R3b #47-#49).
- (J11) Review a region with the full rubric (outline, 3-D form, inner structure, surface/hair, colour, placement,
  junction, motion), not a symptom list - the ear summary missed most of it (person, R3c #56).
- (J12) Judge colour/lighting defects on the RENDER, not on albedo: the first open-mouth metric read painted colour
  (0.66, "fine") while the render was black (0.13) (R3a #37).
- (J13) NO ACCEPTED DEFECTS: a defect found in a layer is fixed at its root in that layer, or it stays OPEN and blocks
  that layer's acceptance - never "accepted and flagged because a later layer covers it". A covered defect breaks later
  work somewhere, and finding the old decision then starts "a whole long list of battles that never end" (person
  2026-10-17, on 1-2 mm streaks left on the L1 skull). Uncertainties (a measurement spread, a source conflict) are not
  defects: they are reported with their size; a SHAPE the build got wrong is a defect.
- (J14) Measure a feature in its OWN frame: cut a curve perpendicular to its own direction, look straight into a cavity,
  section a limb across its own axis - never along a frame borrowed from elsewhere. When the frame is uncertain, sweep it
  and report the best value with the band of frames near it. Fixed-x cuts made the mouth "end" at 7 mm (REVIEW_mouth);
  a 4 deg change of view axis moved a nostril depth by 0.3-0.4 mm until the view was swept (tripo_rebuild LOG #81).
  Moved here from the base skill's proposal (R7) because it holds for geometry, not across domains (person 2026-10-18).

## Red flags - stop and measure
- A metric improves while the turnaround gets weirder (single-view overfit).
- A focal length drifting to the search bound (model depth is wrong, not the camera).
- Anything "renders fine" but was not checked in a posed frame (`anim_check.py`).
- A check that passes everything the person criticises: it is a gross-error gate - add a finer one.

## Platform gotchas
`references/blender-gotchas.md` (QuadriFlow scale, even-odd fill, Blender 5 sockets/modifier inputs, hide-flag
inheritance, stale collection entries, orphan purge, bone-space parenting, EEVEE vs Cycles hair). 16 GB machines:
`checkpoint.py` after each stage (undo cap, autosave, numbered copies).
