# The target-driven loop: language for the story, math for the form

Source: the person's insight of 2026-10-19 ("everything we're building is mathematically quantifiable"; "let math
carry the day") and the story-first refinement after base torso v5 ("this is a rock ... let's finish the story of the
front, on the back"). Verbatim: `cases/woman2/MATH_METHOD_RECORD.md`. Code: `engine/loop/`. This is a method, not a
rulebook: it says what helps and where it misleads; the judgement stays the builder's.

## The idea
Any subject can be described twice. In words: what it is, what its parts are, what the input shows and what it hides,
and a believable hypothesis for the hidden part (the rock's weathered back carries on the front's asymmetry; a woman's
back carries on the curve her front implies). In numbers: for each property that decides whether the shape is right,
a value, how much it normally varies, and where that knowledge came from. Words end where numbers start. From there
the loop measures, compares, moves smooth handles and measures again, and nothing is judged by a picture.

## One pass
1. **Story.** Write what the subject is, its parts, and the hypotheses for what the input can't see, each with a
   plausible range. The story is where the person's observations land ("the arm doesn't flatten there"; "she looks
   curved inward") - as evidence to turn into numbers, not as instructions to sculpt.
2. **Descriptors.** Choose the properties that define "right" for each part: a profile's arc angles, a limb's
   cross-section roundness, a gap between parts, a ratio of widths, a surface roughness. Choose the property that
   captures the person's complaint itself: a smooth shelf passes every curvature-threshold test, so "irregularity" was
   the wrong descriptor for "the arm flattens" (woman2 v5); a section's flat share is the right one.
3. **Targets, ranked** (engine-grounding G3): measured in the input > a known-good reference measured with the SAME
   descriptor (stacked at one position, A29) > cited data with its normal spread (packs) > the story's own range
   (flagged as a hypothesis). Every target is a band (value +- sd). Inside the band is normal variation and is kept;
   only the part outside costs. A modifier (age, bust, weight, a rock's weathering) shifts targets, never the mesh.
4. **Prove each instrument once** on a shape whose answer is known, at the noise level of the real input (A10).
   `engine/loop/test_shape.py` is the pattern: known arcs at 0-1.2 mm noise, a known flat side, a planted bend the
   loop must undo.
5. **Measure and compare**: one table, each descriptor as z = (measured - target) / sd. This table is the defect
   list. The current state is reported with its range across the instrument's settings (A14).
6. **Handles**: a few smooth ways the region may change, chosen to be anatomical (or geological) mechanisms rather
   than vertex pushes: a spine bending over a height range with the pelvis turning rigidly below; biharmonic bumps that
   meet their surroundings tangentially; a texture's generating parameters. Few handles, smooth by construction.
7. **Solve**: `core.solve` moves the handles to bring every descriptor into its band with the smallest change
   (least squares with a regulariser). Constraints that must hold (no crossing faces at any pose, approved parts
   unchanged, totals like a pelvis that stays where it stands) are descriptors with tight bands, or checks after.
8. **Verify on the same table**, plus the engine's standing checks (pose sweep, rebuild from the pack). Then show the
   person, labelled (A17). The person's look is the final audit, never the acceptance test.

## The first principle (the person, 2026-10-19)
"We cannot assert a fact without measuring." Every statement about the model - what is wrong, where, why, what causes
it - carries the measurement that shows it, or is labelled a hypothesis and measured before anything acts on it. A
label from a tool (a region name, a category) is not a measurement of the thing it names: check what the label sits on.
(woman2 v7: four "breast" flat patches were 100 % arm vertices, named by position; a cause was asserted from the label.)

## Where it misleads
- A descriptor that doesn't capture the complaint: the loop will satisfy it and the shape will still be wrong. When
  the person's next look disagrees with a green table, the descriptor is wrong; find the property they saw.
- Data measured one way compared with an instrument that measures another (surface angles from different devices
  differ by 10-20 deg; replica and in-vivo skin roughness differ by 2x). Match the definition before the number.
- A handle that can't express the needed change: the solver hits a bound or trades one target against another. Read
  the parameters and the residuals, not only the table.
- Missing data: the story's range is a hypothesis; say so in the table (rank "story") and let the person or a
  reference confirm it.
- Structure the loop can't build: true armpit form needs muscle, tendon and ligament structure (the person,
  2026-10-19). Targets on the surface can only approximate what an unbuilt layer would produce; say when a job is
  in that territory.

## Habits it replaces (each failed on woman2, 2026-10-19)
- "Defect = curvature above a threshold" with no target: found irregularity, not wrongness.
- Magnitudes picked by feel ("a 15 mm cup looks right"): the old way in math clothing.
- Screenshots or averaged heat maps as acceptance.
- Iterating a tool's mechanics by trial (eight runs of a crease fix) instead of defining the shape.
- Smoothing a later layer around a shape an earlier layer built wrong (the arm's flat inner side came from Stage 4).

## The code (`engine/loop/`)
- `core.py`: `Target`, `measure`, `table`, `solve`, the report.
- `shape.py`: descriptors `profile_arcs` (a surface profile's convex/concave arcs and hollow), `limb_sections`
  (cross-section flat share, aspect, curvature jump), `state_value`; handles `SliceBend`, `NormalBumps`.
- `relief.py`: a skin micro-relief model from cited numbers (network of furrows, follicles), its statistics, a
  handle over its parameters, tile export.
- `rigstate.py`: a rigged mesh posed in numpy (matched to Blender), and a posed change turned into corrective keys.
- `region.py`: region-only evaluation for work on one region: `Region(state, core, margin_m)`
  (a sub-state the handles and descriptors run on unchanged; `.put()` writes the core back and asserts nothing else
  moved) and `solve_region(...)`. The margin must cover what the handles and descriptors read past the core.
- `recipe.py`: the model as a replay of stages from a stored base, with a stage cache (`--no-cache` replays all).
- Domain numbers live in packs (`packs/human/references/*.md` and their JSON), never in this code (A9, G14).

## A job
A job is a small script or JSON in the case folder: the story (text), the state (which mesh, which pose), the
descriptors with their settings, the targets with source and rank, the handles, the constraints, and where the result
goes (a new pack version beside the old one). The report keeps the table before and after, the handle values, and the
checks. Jobs are the engine's work; the orchestrator reviews the table and the person audits the result.
