---
name: engine-grounding
description: >-
  Companion to recursive-improvement and to an engine's own skill; it supplements them and never replaces either.
  Keeps an engine's output grounded in evidence: where every value comes from and how sure it is, how reference or
  AI-made material is kept from deciding, how a change is shown not to break what already worked, and how every
  human note is accounted for. Use when an engine fills in what its inputs don't show, uses reference or generated
  material, is about to change code that already works, or receives a person's review.
---

# Engine grounding (companion, on trial)

**How it fits.** `recursive-improvement` owns the loop (rounds, checks, the ratchet, graduation). The engine's own
skill owns its domain. This skill owns provenance and proof: what a value rests on, and how we know a change helped
and broke nothing. Where they disagree, `recursive-improvement` and the engine's skill win. Nothing here replaces a
step of theirs; each item adds a practice they don't spell out.

**Switches.** Read `flags.json` first; an item whose flag is `false` is off. Roll back by setting it `false` and
logging why in the engine's `METHOD.md`. Where each item came from, how it was adapted and what was left out:
`references/source-map.md`.

## Where values come from

- **G1 · Concepts before the first example.** Before building from a first case, write one page: the ways inputs
  can vary (for an image engine: subject kind, pose, surface/coat, lighting, camera, occlusion) and the abilities
  that answer each. An engine already grown from one case writes it now and moves that case's specifics out of the
  core. Update the page when a case shows variation it doesn't list.
- **G2 · One record, every value with its source.** The record the engine builds from (a spec, a layout, a shot
  table) gives each value its source and a confidence: seen (measured in the input), inferred (constraint, cue or
  cited estimate), unsure (flagged). Nothing is built that isn't in the record.
- **G3 · Ranked evidence for what the input doesn't show.** Rank: (1) measured in the input; (2) constraints that must
  hold together (symmetry, a muscle fills its hollow, totals reconcile); (3) a good reference of the same subject
  given as input (another view, a 3-D model - AI-made included, see G5); (4) indirect cues (shading, perspective,
  formats, distributions); (5) domain estimates with cited sources, researched once and kept in the domain pack;
  (6) one plain question to the person. Weaker evidence never overrides stronger; a winner needs a clear margin;
  doubt becomes a flag with its evidence, never a silent guess.
- **G4 · Propose, pick, check.** Code proposes candidates, a model or a person picks, code checks the pick by
  measurement. A model never free-hands what code can measure.
- **G5 · References are evidence, not authority.** Person, 2026-10-17: "a reference is a reference, and if it is
  good, it should be usable" - AI-made included. A reference given as input may supply geometry once judged good:
  it agrees with the input where both can be seen (silhouette, landmarks) and with the constraints that must hold.
  Every value taken from it carries that source (G2), and the input wins wherever it sees the thing (G3). Material
  given only for scoring (an answer key), or under other terms, stays within those terms. A generator never adds
  what the record doesn't hold.

## Proving a change

- **G6 · A baseline before changing working code.** Snapshot what the pipeline produces today as measured values
  (counts, gate values, scores, region measures), re-run it once to learn the run-to-run tolerances, and compare
  after each change. The comparison is advisory; it never blocks building. An intended difference goes in a
  corrections register with its reason; re-baseline only with the person's OK. A baseline is not an approval of
  quality - a failing build can be one. Not byte-exact where renders or other outputs vary.
- **G7 · Tuned values carry their case.** A value fitted to one case is labelled with that case. It becomes a
  default only after it holds on a case it wasn't fitted on.
- **G8 · Contamination audit.** Record who saw which answer key or reference, and when, against the decisions made
  after. Disclose overlap; a contaminated case stays a development case, never blind proof.
- **G9 · An AI critic supports; it never decides.** Count a critic's finding only after checking it against the
  output itself; grade again with the critic off; disclose when the critic shares the builder's model family.
- **G10 · Cheap before expensive.** Settle a question at the cheapest stage that can show it (a lab render, clay, a
  still) before paying for the expensive one (a full build, fur, motion).

## The person's input

- **G11 · Account for every note.** Every point in a person's review, annotation or message gets a row: done (with
  where), deferred (with reason), or asked. Nothing is silently dropped.
- **G12 · A person's input is evidence, not authority.** Person, 2026-10-17: "even my input, like my lines guiding the
  fur direction, should be treated as suspect. The result is what matters." Weigh their marks and notes like any
  other source, check them against structure and data, and show a conflict instead of resolving it silently either
  way. Their decisions about goals, scope and approvals are theirs; their observations are evidence.

## Done

The item's practice was applied where it applies, the engine's `METHOD.md` records any flag switched off and why,
and nothing in this skill was used to skip or weaken a step of `recursive-improvement` or the engine's skill.
