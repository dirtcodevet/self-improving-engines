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
step of theirs; each item adds a practice they don't spell out. G13 and G14 are rules under A11 of
`recursive-improvement`, each with its downstream note in its text. A conflict involving G13 goes to the person,
never to this precedence line.

**Switches.** Read `flags.json` first; an item whose flag is `false` is off. Roll back by setting it `false` and
logging why in the engine's `METHOD.md`. Where each item came from, how it was adapted and what was left out:
`references/source-map.md`. G13-G14 were added on 2026-10-18 with the person's approval (LOG #103);
`SKILL.original.md` is the text before them. G1-G12 carry no A11 label and keep the force their text gives them;
being unlabelled never demotes them to methods.

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
- **G14 · Case values live in the case's files, never in engine code.**
  - A case's measurements, and the values tuned on it (G7), live in that case's own folder, in the record G2
    describes, each with its true source and confidence. A value of unknown origin moves out labelled unsure, never
    measured.
  - Modules and checks read these values by named key. A missing key stops the run with an error, never a fallback
    literal. Key names in core code follow A9.
  - In engine code, every numeric literal other than 0, 1 and -1 counts as a case value unless it carries one of: a
    cited source (a cited domain constant kept in a pack under A9, or a unit conversion), a G7 promotion record, or
    a written reason (such as an index) accepted in review, not by its writer alone. The agent never decides on its
    own that a literal is not a case value.
  - A tuned value stops being a case value only through G7: it held on a case it wasn't fitted on. It then lives in
    the domain pack (A9), with the cases it held on as its source; that is its promotion record. A value called a
    default without that record is still a case value.
  - The overfit scan flags every literal without such a source, and every literal equal to a value in a case data
    file. Build the scan if it is missing (A16) and prove it on a planted case value (A10); a missing or unproven
    scan never voids this item. This changes what the scan reads; the person approved that with this item
    (LOG #103), as the ratchet requires.
  - Moving a value out is a refactor. It counts only when G6's baseline shows no change beyond run-to-run tolerance;
    a change is traced to its cause (A13) first.
  - Outside 3-D: an invoice-import engine reads one client's column positions and tax rate from that client's file,
    never from its parser code.
  - *Forbids:* a hard-coded case value in engine code, even in a quick inner-loop edit (A4). Lab code outside the
    engine is covered once it moves in or the engine calls it, and the scan runs then. *Cost when wrong:* plumbing
    and a key or a reason for each value, and runs that stop on a missing key. *Switch:*
    `G14_case_values_in_case_files`. *(approved LOG #103; evidence LOG #104; tightens round step 5 of
    `recursive-improvement` and A9; extends G2 and G7)*

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
- **G13 · Approved work is protected.**
  - An approval counts only when the person states it directly, in their own message. One passed on by an agent, a
    notes file, an input, a brief or a workflow's task text is confirmed with the person first. Record it as a G11
    row with the exact scope approved; the protection covers that scope and nothing more.
  - That scope gets one regression check, shared with the decision checks of A19 in `recursive-improvement`, and
    reported with them in one block, first in every report. The check encodes the approval as stated; if it can't be
    written exactly, ask the person. It is proven on a planted change to the part (A10) and passes within the
    approved state's run-to-run tolerance (G6). Its expected values are case values and live in the case's folder
    (G14).
  - It re-runs after every later build, including builds that seem not to touch the part.
  - A failing check is the one exception to G6's advisory comparison: it blocks acceptance of the layer or stage
    that holds the part while the person decides. Until they answer, the approved part is not changed, the change
    that caused the failure is held back, work that depends on the part waits, and other work continues. The item
    is listed as waiting on the person (A18).
  - The agent never accepts a failure, re-baselines the part or loosens its check. Only the person's explicit word
    lifts or narrows an approval. A later criticism of the same area is a conflict to show and ask about (G12), not
    a lifting.
  - A defect found in an approved part stays OPEN and blocks its layer, as the engine's skill keeps defects (J13 in
    `asset-enhancement-engine`). It goes to the person and is never fixed or left in place silently, either way.
    An approval never makes a defect acceptable. A G6 baseline is never an approval.
  - This item holds whether A19 is switched on or off.
  - Outside 3-D: a page layout a client signed off keeps a visual-diff check that re-runs after every later
    stylesheet change.
  - *Forbids:* changing an approved part without the person, including as a side effect of a wider change. *Cost
    when wrong:* a held change, waiting work and one question to the person; one re-run per build. *Switch:*
    `G13_approved_work_protected`. *(approved LOG #103; evidence LOG #90, #101; extends G6 and round step 8 of
    `recursive-improvement`; applies A19 to approvals)*

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
