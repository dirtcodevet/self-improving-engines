# Layered build protocol (trial E4; approved by the person 2026-10-17)

Why: R3g root cause - every layer was built at once and the whole stack was tuned against one photo, so layers
covered for each other (fur filled the outline the skull lacked; paint stood in for lips, eye rings and the nose)
and no layer was ever accepted on its own. Person: "build the cat in full layers ... skeletal structure, muscle
structure (both provide form and function for everything beyond), skin, and fur ... working on the body in
sections until the whole thing is complete for that section"; "I do NOT want to babysit every step"; and "I don't
think it's necessary to reproduce a full and anatomically correct/precise skeleton. That's overkill."

The protocol is domain-neutral: a subject is built from where its form ORIGINATES outward, each layer only as
detailed as the visible result needs. A cat: frame -> muscle -> fat and skin -> what grows from the skin -> pigment
-> motion. A tree: trunk -> branches -> bark and leaves. A human head: skull -> muscle -> skin -> hair. An importer:
source -> file -> record -> field -> value.

## Order
LAYER-MAJOR, SECTION-MINOR: one layer across the whole subject; inside a layer, section by section, each section
brought to the layer's acceptance before the next section starts. A later layer never fixes an earlier one (fur
never fills a missing shape, paint never stands in for structure): an earlier-layer defect found later goes back to
that layer.

Cat layers:
- L1 FRAME - a SIMPLIFIED, form-giving skeleton at real scale in the photo's pose: only the bone forms that shape
  what is seen (skull: brow, orbits, cheekbones, nasal bridge, jaw; scapulae; the ribcage as one volume; pelvis;
  spine curve; limbs as proportioned segments with joints). Not a precise skeleton (person: overkill). A real skull
  scan, if used, is a measuring reference for fitting this frame, not an import. The rig derives from the frame.
- L2 MUSCLE - the masses that give visible form (and later function): temporalis, masseter, neck, shoulder, limbs,
  trunk - again only as many as the form needs.
- L3 FAT, SKIN AND FEATURES - fat pads (whisker pads, cheeks), skin thickness, and the features as STRUCTURES:
  lids on the globe, nose leather with nostrils, lips tucked under the whisker pads, ear cartilage with its folds.
- L4 HAIR ROOTS AND FUR - the follicle palette and map (E6), growth directions from hair streams, density at real
  values, locks, strand rendering chosen by the fur swatch test.
- L5 PIGMENT - skin pigment (nose leather, pads, ear skin) and hair colour from the palette; markings are WHERE
  pigmented hair types grow, never paint on the skin under white fur.
- L6 RIG AND MOTION - from the frame; muscles may drive deformation.

Cat sections: head, neck, chest/shoulders, forelimbs, trunk, pelvis/hindlimbs, tail, paws.

One connected subject: each layer is a set of volumes; the skin is computed once from their union (signed distance
fields), so sections are never stitched or merged as meshes. Detail finer than the volume grid is added to that
single skin.

## Accuracy has two parts (person, 2026-10-17)
1. NUMERIC tolerances, set by what an error does downstream (a layer is accurate enough when nothing above it has to
   compensate) and by what can be measured (across the photo ~0.27 mm/px: millimetres; depth: agreement with the
   reference or the anatomical range, flagged as lower confidence); tightest where the eye judges "cat" (the face).
2. STRUCTURAL COMPLETENESS: every part listed for the region in the pack's structure inventory
   (`packs/felid/structure_inventory.json`) exists AS STRUCTURE and is visible in a colourless clay render.
A region passes only when both pass. Judging structure always uses solid clay, X-ray off, neutral light, front /
side / three-quarter + close-ups (X-ray only for a frame shown inside a model, labelled). Every new check must fail on
a known bad case first (A3) - e.g. the v37r frame with its trunk mid-body must fail the frame checks.
The NOSE and MOUTH are required as physical form before any fur or pigment work (person): the skull carries the
nasal aperture and the jaw line; the features layer builds nostrils opening into a nasal cavity with depth, the
leather/bridge crease, the philtrum groove, the mouth crease where the upper lips overlap the lower lip, and the
corner creases - checked in clay close-ups against the real nose and mouth photos.

## Acceptance (defined BEFORE building; measured; the engine moves on when they pass)
No accepted defects (J13, person 2026-10-17): a defect found in a layer is fixed at its root there or stays OPEN and
blocks the layer; "a later layer covers it" is never a reason to accept it.
Each layer x section passes when its checks pass AND the blind reviewer (REVIEWER.md, same rubric) finds nothing
structural in that section. Checks per layer (initial set; refine with the research files):
- L1: the VISIBLE BONY LANDMARKS measured in the photo (withers, point of shoulder, elbow, stifle, hock, tail root,
  orbits, nose position) are hit within ~3 mm across the image; depth within ~15 mm of the reference (flagged); bone
  proportions within 1 SD; left/right within 2 %; the spine follows the dorsal line at a soft-tissue offset; checked
  from a second angle against side references; the head inventory's L1 parts present (incl. nasal aperture, jaw line).
  (v37r frame lesson: paws-on-points + bones-inside-the-outline passed while the trunk sat mid-body.)
- L2: the envelope (frame + muscle + fat + fur depth) matches the photo outline where the photo sees it; no
  concavity where anatomy has none (e.g. temple); seam fairness; the clay turnaround shows muscle form, not blobs.
- L3: every feature is visible in a COLOURLESS clay render (E5); feature traces match the photo; lids sit on the globe;
  the closed mouth shows as the shadow under the overhanging lips, not a drawn line.
- L4: density and hair dimensions from real values per region; directions from hair streams (research) checked
  against the photo's trusted flow; locks visible at the review distance; the swatch metrics against fur close-ups;
  fur tips reach the measured envelope within the region's spread; re-run after every skin change (J16).
- L5: region colour against the photo; marking edges as crisp as the photo's; palette edits change hair colour
  without repainting.
- L6: the existing posed-frame checks.

## The person
Three milestones only: M1 form (L1 + L2 whole subject, clay), M2 skin and features (L3, clay), M3 fur and pigment
(L4 + L5). Between milestones the engine works autonomously; it asks only on a genuine tie (engine-grounding G3) or a
decision only the person can make. The person's notes are evidence like any other (G12): weighed, checked, and a
conflict is shown, never silently resolved either way.

## Tools by result
When two tools could do a layer, run the same small test with both and keep the better result (e.g. the fur swatch:
one patch at real scale, same camera and light, our groom vs Blender's hair tools, scored against close-up photos of
real fur).
