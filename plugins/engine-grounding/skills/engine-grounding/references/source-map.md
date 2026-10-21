# Source map: what came from where, how it was adapted, what was left out

Sources (the person's toolkit from an earlier project, read 2026-10-17): `engine-proof` and `generative-pipeline`
(kept with that project), and "Building Proven AI Engines - A Blueprint". Those skills are not
copied or installed; this companion takes the parts that add something to `recursive-improvement` and the engine's
skill, adapted so they hold for generative and 3-D work as well as for importers.

## Taken, and how it was adapted

| Item | Source | Adaptation | Evidence it matters here |
|---|---|---|---|
| G1 Concepts before the first example | engine-proof loop step 1; blueprint "the first example leaks in" | one page, not a committed requirements file; for an engine already grown from a case, written late plus moving the case out of the core | the cat engine's core holds cat vocabulary (scan 2026-10-17) |
| G2 One record with sources | generative-pipeline rule 1 | confidence words seen / inferred / unsure on every value, including filled-in unknowns | spec values had no recorded source; reference-derived values were not distinguishable (contamination disclosure) |
| G3 Ranked evidence | engine-proof "rank the evidence", "a winner needs a margin", "never guess"; generative-pipeline rule 2 | extended from labels-vs-measurements to dimensions the input doesn't contain at all; estimates kept in the domain pack | GAP_ANALYSIS; R3c #50, #58 |
| G4 Propose, pick, check | generative-pipeline rule 3; blueprint (freehand tracing metres off) | unchanged | photo traces are code-measured; feature fitting by eye drifted (R3c #54) |
| G5 References are evidence, not authority | generative-pipeline rule 4 ("generators make, never place") | first written as "AI-made material never places"; the person decided (2026-10-17) that a good reference may supply geometry, AI-made included. Kept from the source: a generator never adds what the record doesn't hold; references are labelled and the input wins where it sees | the Rodin mesh supplies cat1's body depth (disclosure; now within the person's decision) |
| G6 Baseline before change | engine-proof "golden record before change" + corrections register | measured values with tolerances from a re-run instead of bytes (renders vary); advisory, not a gate; not an approval of quality | the person: "it hasn't passed yet" - a baseline is a snapshot, not a verdict |
| G7 Tuned values carry their case | engine-proof "weights, thresholds and margins change only via a gap report; tuning until the bars pass is training on the tests" | lighter: tuning is allowed in labs; the result is labelled and must hold on another case before it is a default | ear-furnishing defaults fitted on one photo (R3d #65) |
| G8 Contamination audit | engine-proof "audit for contamination" | unchanged | disclosure 2026-10-17 |
| G9 AI critic supports | generative-pipeline "the AI critic is support, never the decider" | applied to the blind reviewer agent | the blind reviewer shares the builder's model family |
| G10 Cheap before expensive | generative-pipeline rule 10 | stages of a 3-D build (lab, clay, still) as the cheap tiers | ear lab vs full builds (R3d #65) |
| G11 Account for every note | generative-pipeline rule 5 ("inventory the source") | applied to the person's reviews and messages | the ear-scope note (R3c #56): parts of a review were summarised away |
| G12 Person's input is evidence, not authority | generative-pipeline rule 8 | reworded by the person (2026-10-17): their marks and notes are suspect evidence like any other; their decisions on goals and approvals stay theirs | the cheek lines were first taken as highest-trust input |

## Added from the engine's own rounds (approved by the person 2026-10-18, LOG #103)

Drafted from the round evidence, then checked by two independent checkers (this skill's own and a cross-skill one);
the final text keeps every safeguard either added. No case names, coordinates or quoted case input; evidence is cited
by `tripo_rebuild/LOG.md` row only.

| Item | A11 label | What the checks added | Evidence | Downstream note |
|---|---|---|---|---|
| G13 Approved work protected | rule | only an approval the person states directly counts (injection guard); exact scope as a G11 row; one check and one report block shared with A19 of `recursive-improvement`; re-runs after every build, no "doesn't touch it" skip; a failure blocks the part's layer while the person decides (the one exception to G6's advisory comparison), other work continues; a defect stays OPEN (J13 of the engine's skill) and goes to the person, outside the precedence line; only the person lifts an approval, and a later criticism is a conflict, not a lifting | LOG #90, #101 | Forbids changing an approved part without the person. Cost when wrong: a held change, waiting work, one question. Switch: `G13_approved_work_protected` |
| G14 Case values in case files | rule | tuned values included, not only measurements; burden flipped: a literal is a case value unless it carries a cited source, a G7 promotion record or a reason accepted in review; a promoted default lives in the pack with the cases it held on (settles G7 and A9); no fallback literals; unknown origin moves out as unsure; scan built and proven if missing (A16, A10); moving values out proven by G6; the change to what the scan reads was approved with the item (ratchet) | LOG #104 | Forbids a hard-coded case value in engine code. Cost when wrong: plumbing per value, runs that stop on a missing key. Switch: `G14_case_values_in_case_files` |

## Left out, and why

| Idea | Source | Why not here |
|---|---|---|
| Synthetic generator + renderer as the answer key | engine-proof graded sets | for 3-D creatures a generator of truthful worlds is nearly the engine itself: high cost, circular; revisit for data engines, where it is cheap |
| Byte-exact golden record | engine-proof | renders and GPU sampling vary; G6 uses tolerances |
| Committed requirements file, `.work/` rounds, ledger and baton files | engine-proof, session-start | would clash with the engine's `engine/log` layout and add process cost |
| Never refuse / never drop / every unit accounted once | engine-proof | importer-specific; the general part lives in G2 (flags) and G11 |
| Spend guard | generative-pipeline rule 9 | only relevant when paid generation calls are made; use the source skill then |
| No real private data reaches the AI | engine-proof | not relevant to the person's own photos; use the source skill when client data appears |
| Deterministic assembly by input hash | generative-pipeline rule 6 | the engine already pins its seeds; caching generations matters only with paid generators |
| Scheduled reviews | (proposed in our own review) | person: schedules force rigidity |
