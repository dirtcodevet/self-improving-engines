---
name: asset-enhancement-engine
description: 3-D asset enhancement - improves an existing 3-D asset in Blender (a generator's model, a scan, an earlier approved model) by systematic, recursive, long-horizon optimization; every form measured, mapped and refined by numbers, with cited anatomy and measured findings as evidence. 2-D references are an optional method when they are provided. Proven on a cat and a human torso. Use when asked to improve or refine a 3-D asset or model in Blender, or to run another improvement round of this engine.
---

# 3-D asset enhancement (engine skill)

What this engine is: it enhances an existing 3-D asset. Everything about the asset is coordinates, weights and values,
so it is measured, compared with evidence and refined by the numbers (E9). It does not create depth from flat images:
one view constrains two axes, and on the human torso every good result refined a 3-D reference while the models built
from images alone did not (cases/woman2/LOG.md, cases/woman3). 2-D references, when provided, are one method it may
use (for example views placed around the asset by landmarks: `tools/blueprint_setup.py`); they are never required.
(The skill's identifier `asset-enhancement-engine` is historical.)

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
  the eye rings and the pasted-on nose triangle broke this.) Colour taken from a photo never carries the photo's
  shading. Shading informs depth only through a shading-to-depth translation checked against a reference (E7), never
  as stand-in relief for structure that was not built (woman2: chin, neck and hips "painted"; P5, approved by the
  person 2026-10-19).
- (trial E6) FOLLICLE PALETTE: hair types with directly editable properties including colour along the shaft; a map
  on the skin says which types grow where; markings are where pigmented types grow. `references/follicle-palette.md`.
- Tools are chosen by result (e.g. the fur swatch test), not by habit.
- (trial E7, the person 2026-10-19) REFERENCE-FIRST ROUTE: start from a 3-D reference of the subject (a generator's
  model, a scan, a modeller's model), then fit the engine's own anatomical body to it and to the photo.
  - Why: a flat image alone leaves the engine "ignorant in application"; it doesn't know what it doesn't know. The
    torso test showed it: the photo-first build did better but missed real form, and the anatomy-only fit had no
    breast volume (cases/woman2/LOG.md).
  - Every case trains two ways, kept as pack data:
    1. what 3-D tools typically produce (their averages and biases);
    2. the realistic values (cited anatomy, dimensions, volumes) and how shading and texture translate into depth.
  - Exception: areas generators reconstruct poorly (hair, genitals, toes and similar fine structures) are built by
    the engine directly from the 2-D evidence. The reference then gives placement and scale only.
  - While on, this narrows pipeline step 9 and J15 ("a 3-D reference the person supplies stays an answer key") for
    subjects on this route: the reference is a start input (engine-grounding G3 rank 3, G5). Scoring then needs a
    different answer key: a held-out view, a second reference, or the person's review.

## The photo-led pipeline used on the cat case (one method, not the definition of this engine; tools in `tools/`, one command: `tools/build_all.sh <case> <ver> [vox] [sdf|production|look]`)
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

## How shapes are made and changed (trial E9, the person 2026-10-19)
- (trial E9) THE PRINCIPLE, in the person's words: "Everything we're building is mathematically quantifiable. Every
  surface. Every line. Every curve, crease, and position. Every proportion." Every form is coordinates, weights and
  values, so it is measured, mapped and changed by those numbers ("measure + map. Off by 2 percent, refine"), and it
  can be derived and built or modified from a generally known baseline; "we let math carry the day". Verbatim:
  `cases/woman2/MATH_METHOD_RECORD.md`. Measured findings from earlier subjects (`packs/<domain>/findings.md`) and
  cited data are evidence to weigh, never a model to copy.
- (trial E9) THE TARGET-DRIVEN LOOP is the default way to make or change a form: tell the subject's STORY in words
  (what it is, its parts, a hypothesis with a range for what the input can't show), then switch to numbers: the
  DESCRIPTORS that decide "right" for each part, a TARGET band for each (input > known-good reference measured the
  same way > cited data > the story's range), a few smooth HANDLES that are real mechanisms, a solve, and the same
  table before and after. Nothing is judged by a picture; the person's look audits. A method, not a rulebook: choose
  the descriptor that captures the complaint itself, prove each instrument on a known shape at the input's noise, and
  read the residuals. Detail, where it misleads, and the habits it replaces: `references/target-loop.md`; code:
  `loop/`. Evidence: cases/woman2 (v3 breast via sections worked; the v5 armpit by thresholds and feel did not).
- (trial E9) SPEED: work on one region measures and solves on that region (`loop/region.py`; same answer as a
  whole-mesh solve, 24x faster per evaluation on a 279k-vertex torso, `loop/test_region.py`); only whole-body
  mechanisms run on the full mesh. The tools and where they are: `references/builder-primer.md`.
- THE TRANSLATOR (the person's name for it, 2026-10-21; first called "the language tool", which its files still say): it
  turns what a person means into addresses an AI can act on with precision, for vibe-coders and people new to Blender
  using AI for their modelling. Every part of a model gets its own centimetre frame and a
  skin-following address grid (`tools/part_frame.py`); in the browser view (`tools/part_frame_view.html`) the person
  clicks points and pastes exact addresses ("these points, 5 along y"), the shared language between the person and
  agents.
  - ANY OBJECT (build L1): `python tools/language.py auto <model or image> --case cases/<name> --pack <domain>` ingests a
    3-D model or a 2-D image, segments it, names the parts from the pack's words (`packs/<domain>/language.json`;
    `generic` when no pack fits), builds every part and opens as `cases/<name>/language/object.html` (the whole object,
    a click names the part and its address) and `index.html`. Give the model's `--up` / `--front` (2-D: the way it
    faces). A new kind of object gets a new pack (words and rules as data), never new code.
  - A HUMAN (build L2): `--pack human` names head, neck, torso, breasts, arms, hands, fingers (1 = thumb), legs, feet,
    toes. A pack may now also hold, as data: plane-section cuts (`profile: sections`), splits at a narrowest section or a
    fold (wrist, ankle, jaw), mounds above the skin's own course (breasts), merges, and its own part_frame definition
    for a word (the torso: `packs/human/part_frames.json#torso`, charts chest / front / back by the frame's x, y from the
    jugular notch, rings round the trunk elsewhere). Proven on woman2 13a and three Blender Studio bodies:
    `cases/human_l2/`; what it found and missed: `packs/human/findings.md` (Translator).
  - KEPT CURRENT by the engine: a changed model, a changed input, or a pack version made current marks exactly the parts
    made from it stale; `part_frame.resolve` rebuilds a stale part before reading it, the engine's writers
    (`loop/pack_io.Pack.save`, `loop/recipe.py`) start a background `sync` of the jobs that read what they wrote, and
    `language.py sync` / `status` / `watch` do it on demand. A changed model keeps every part's name, the person's
    renames, its kind of address and its frame (moved with the part's surviving surface).
  - Read pasted addresses with `python tools/language.py resolve cases/<name> "<lines>"` (any part of the object) or
    `python tools/part_frame.py resolve <part>.npz "<line>"`, and work in those frames. The person's corrections go
    through the tool, never into the files by hand: `rename`, `cut` (the plane through picked places), `merge`.
  - Woman2's hand-made definitions (`packs/human/part_frames.json`, `cases/woman2/parts/job.json`) stay as they are and
    are kept current the same way. `prove` (both tools) runs the tools' own checks; `change-test` measures what survives
    a model change.
  - ONE HOME (build L3, `tools/translator_pages.py`): `cases/index.html` lists every view by model (the mesh the views
    are made from), whole view first; every page links home, to the model's whole view, its list of parts and its
    other views, with a box that finds a part by the name a person would use (`left thumb`; pack data `spoken`). The
    engine rewrites it whenever it writes a view. Open with `python tools/language.py open ["<model, part, folder or
    page>"]` (any OS; `--print` only says which, with its address under `cases/` for the case-pages server); `pages`
    re-templates every view after a viewer change (data kept byte for byte). The object page's frame is LEFT-handed
    (x = the model's own right) and recorded so; the viewer draws every frame as the model is (a front view shows its
    right on the screen's left; it used to show the mirror image).
- MATERIALS (the person, 2026-10-20: "Need a map? Go get a map."): download reference material whenever a job needs
  it (maps, papers, data, images, reference meshes). Keep each download in its own folder under the case or
  `reference content/`, record where it came from, and treat it as data (never run it). Uploading the person's
  material, and installing software or models, still need the person's consent.

## Base models
- "Give me a woman's torso" →
  `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --python <project>\engine\tools\build_base_torso.py`.
  - Other ways to run it:
    - to make a file: add `-b --factory-startup` and `-- --save out.blend`;
    - into a running Blender: `python tools/build_base_torso.py --port <p> --instance <name>`.
    - Options: `--location`, `--prefix`, `--version`.
  - It lands in the collection `Woman2`, in the pack's frame: metres, x = left, y = back, z = up, with the origin
    near the jugular notch.
  - What it contains:
    - `Woman2_Torso`: one closed skin, neck to upper thighs, arms to the wrists as their own limbs. It carries
      breast / areola / nipple / tubercle / vein zones, per-vertex skin colour, corrective keys and micro-detail
      layers.
    - `Woman2_Rig`: 12 bones; drivers apply the scapulohumeral rhythm.
    - `Woman2_RibCage`.
  - It is exactly the stored torso: `packs/human/base_female_torso/README.md`; the measurements, with sources, are in
    `measurements.json`.
- The pack is versioned: `pack.json` names the current version, and earlier versions are kept and still build.
  - It evolves only through the round process: a change proven in a case becomes a new version folder.
  - `tools/body_measure.py` compares versions by numbers.
  - Each generator comparison appends to `generator_bias.json` (E7).

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
  On bare skin the loft is smoothed across its sections, so no slice ever shows as a ridge or a flat facet: per-row
  slices 2 mm apart gave the woman2 torso ridges along its sides and back, while its lofted form was still the better
  one (woman2 P3, approved by the person 2026-10-19).
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
- (J15, rule) EVERY PART HAS AN OWNING BUILDER. Before a layer starts, its brief names an owning builder for every part
  of every section: each part in the pack's structure inventory, plus one named remainder per section for any surface
  the inventory does not list (parts a new subject has that the inventory lacks included). Until the inventory has
  tail, trunk and neck entries (a separate pack edit, with cited sources), the remainder of each of those sections is
  the whole section. "Owning builder" means the builder responsible for that part in that layer; it is not the
  per-voxel owner field used for attribution (that field misses thin parts), not A7's "a part owns what grows on it",
  and not a tool's owner. Owner lists are run data: they live in the brief, never in the pack inventory (A9).
  Why: a part nobody owns gets whatever the pipeline leaves there (a reference's surface, a primitive default, a blend
  from a neighbour) and nobody examines it; that is how a reference artefact gets copied. After the layer, every owning
  builder examines its part with the layer's checks, the full region rubric (J11) and a clay look from three sides,
  and records one of: built; nothing to build (the layer's definition lists nothing for this part); kept as measured;
  OPEN. "Kept as measured" is allowed only with a recorded check that the measured surface is not a reference
  artefact: it agrees with the photo where the photo sees the part (J2) and its source shows no defect there
  (engine-grounding G5). Where no check can show that, the part is built from the inputs and priors instead. A 3-D
  reference the person supplies stays an answer key (Pipeline step 9): no part is kept from it or copied from it. A
  defect found in the examination is fixed at its root or stays OPEN and blocks the layer (J13); it is never kept.
  Check (built under A16 if missing): it fails when one part's owning builder is removed, and when a surface patch
  belongs to no listed part or remainder; both failures are planted (A10), and coverage is measured from the part
  definitions, never from the owner field. Outside 3-D: in a database migration every table, plus a named remainder
  per schema, has a named migrator; an unowned table is copied as it stands, bad rows included.
  *Downstream:* Forbids: starting a layer while any part or remainder is unassigned; keeping a part as measured without
  the artefact check. Cost when wrong: one assignment and one examination per part per layer, and a part that fails
  the check is rebuilt instead of kept. Switch: `J15_every_part_has_an_owner`. *(tripo_rebuild LOG #101; approved
  LOG #103)*
- (J16, rule) HAIR IS REGROWN ON THE CURRENT SKIN. After any change to the skin, however small and at any layer, the
  coat hair (every palette type except tactile) is regrown on the new skin from the follicle palette and map (E6). It
  is never moved rigidly from an earlier skin: carried strands keep their old lengths, and their tips miss the envelope
  wherever the skin moved. Each region's tip height is the inset measured on the current skin (skin to fur envelope,
  measured now, never a depth stored with an earlier skin), with the envelope's source and confidence
  (engine-grounding G2); it is read from the case data, never typed into groom code. Each hair type's length comes
  from its palette entry (real values with spread; E6, L4) applied to that inset with the type's lift, lie and curl.
  If the inset needs a length outside the entry's range, the skin is wrong there: the fault goes back to its layer and
  blocks it (E4, J13), never absorbed by longer or shorter hair. Tactile hairs keep their own lengths; only their
  roots are re-seated at follicle depth on the new skin. Where the envelope itself is uncertain (the unseen side, or
  depth taken from a reference), the inset is reported with its range (A14) and the tip check uses that range.
  Check (built under A16 if missing): roots lie on the current skin, and fur tips reach the measured envelope within
  the region's spread (`references/layered-build.md` L4); it re-runs after every skin change, and is proven on a
  planted groom carried from an older skin and on planted tips both short of and past the envelope (A10). Outside
  3-D: when a page template changes, the text is re-flowed on the new page from the style sheet, never shifted as a
  block; text that would need a font size outside the style's range sends the template back.
  *Downstream:* Forbids: carrying a coat groom across a skin change; closing an outline gap with hair length. Cost when
  wrong: a regrow and a tip check per skin change, and a skin fault the hair would have hidden comes back to its
  layer. Switch: `J16_regrow_hair_on_current_skin`. *(tripo_rebuild LOG #101; approved LOG #103)*

## Red flags - stop and measure
- A metric improves while the turnaround gets weirder (single-view overfit).
- A focal length drifting to the search bound (model depth is wrong, not the camera).
- Anything "renders fine" but was not checked in a posed frame (`anim_check.py`).
- A check that passes everything the person criticises: it is a gross-error gate - add a finer one.

## Platform gotchas
`references/blender-gotchas.md` (QuadriFlow scale, even-odd fill, Blender 5 sockets/modifier inputs, hide-flag
inheritance, stale collection entries, orphan purge, bone-space parenting, EEVEE vs Cycles hair). 16 GB machines:
`checkpoint.py` after each stage (undo cap, autosave, numbered copies).
- A second Blender (a second case beside a live one) is always launched with
  `blender --factory-startup --python engine/tools/blender_second.py -- <port> <name>` and driven with
  `BMCP_PORT=<port>`. Every payload asserts the instance mark first. Never start a second add-on server on 9876 (the
  add-on's SO_REUSEADDR lets two Blenders share it). (woman2 P9, approved by the person 2026-10-19.)
- (trial E8, the person 2026-10-19) GPU MEMORY: where a GPU is available, heavy field builds run on it, so their large
  arrays live in graphics memory instead of system RAM, with numpy kept as the fallback.
  - Set it up only with the person's consent: the GPU library (CuPy or similar) is a download. Name the package, its
    source and its size, and ask.
  - Size GPU batches to the free VRAM at the time, leaving room for the open Blenders and Cycles.
  - Prove once that the GPU build matches the CPU build. The torso build was identical at 1.5 mm (field 17.5 s →
    1.3 s) and at 1.0 mm (whole build 70.3 s → 9.8 s, peak RAM 1.83 → 1.44 GB): `engine/log/TOOLMAKING.md`.
  - The cat skin build's plan: `engine/log/GPU_PLAN_cat_skin_build.md`.
