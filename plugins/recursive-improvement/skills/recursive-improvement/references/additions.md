# Additions on trial: evidence, cost, conflicts, rollback

Origin: the cat engine (photo -> rigged Blender creature), rounds R2-R3d, 2026-10-17; evidence rows are in that
engine's `engine/log/METHOD.md`. The person reviewed every item (their feedback is quoted where it changed the item).
Flags: `../flags.json` (keyed by the addition's number). Each item is written so it holds outside 3-D work; the
examples come from the cat because that is where the evidence is.

What was deliberately NOT added:
- Scheduled skill reviews. Person: schedules force rigidity that breaks the skill.
- The risk mitigations listed during the review (label fitted values, assert invariants, small batches, ...) as
  rules of their own. Person: new rules from mitigations may break the skill. Where one survives, it is inside an
  item below or in the companion `engine-grounding`, under its own flag.

## A1 - A knob that doesn't move the output means a broken path
- Evidence: R3d #63 (ear fur length ignored every setting: a later head-wide default overwrote it); R3d #64 (ear
  texture ignored every tuft setting: the renderer's denoiser erased it). Both were found only when tuning stalled.
- Outside 3-D: an importer mapping rule that changes nothing (a later normalisation overwrites it); a CSS rule
  overridden by a later one; a prompt edit hidden by a cache hit; a hard-coded value where a formula should be.
- Cost: none; it shortens tuning. Conflicts: none.

## A2 - Stages check their own output
- Evidence: R3d #59 (the nose leather was unpainted for 5 builds; the log printed `nose 0` and nothing checked it);
  R3d #63 (ear lengths overwritten since v35). One of my own asserts encoded a guessed value and stopped a valid build
  - hence "what must always hold, not guessed values".
- Relation to the original: "Self-review before anyone looks" and "Every defect becomes a check" cover defects after
  they are seen; A2 covers silent failures nobody has seen yet.
- Cost: a line per stage. Risk: over-asserting makes builds brittle; assert emptiness and ownership, not values.

## A3 - Know what a measure measures
- Person's feedback: the first version ("validate every instrument, with noise floors") was too strict and too
  Blender-flavoured; this is the lighter, general form. It matches the person's own lesson from an earlier project "a self-test that
  couldn't fail".
- Evidence: six measuring tools were wrong at first in R3a-R3c (tracer leaks, an outline that measured the shoulder,
  paint colour read instead of the render, a coarse baseline, an exempt zone that hid a seam) and the denoiser bias in
  R3d #64. "Does the texture score drop when I blur the photo?" would have caught the last one on day one.
- Relation to the original: "Check the checks" plants defects for CHECKS; A3 covers measurements that steer fixes.
- Cost: one quick test per new measure.

## A4 - Inner loop
- Evidence: R3d #65 - the ear lab (`engine/review/ear_lab.sh`: one region, the review's own region metric) ran 14
  variants in about 15 minutes, ~30 s each, versus 25-40 min per full build, and exposed three bugs on the way.
- Guard: a loop result counts only after a full run reproduces it (the lab skipped the rig binding, for example).
- Cost: building a loop per area; saves far more than it costs once an area needs more than two tries.

## A5 - Replay every human review
- Evidence: R3b acceptance - the review stack was scored against the person's v27d review (9/9 points found by the
  instruments, ~8/9 by the blind reviewer, ~20 extra findings). That one replay is what showed the review was worth
  trusting; it was done once, not as a habit.
- Feeds the original's Graduation: "corrections reach zero" per dimension needs exactly this count.
- Cost: one review run per human review.

## A6 - Fill unknowns from ranked evidence
- Person's question that shaped it: "how, then, does the skill/AI/engine figure out HOW to fill in the gaps?"
- Evidence: GAP_ANALYSIS (one frontal photo cannot see depth; every unseen dimension had been a primitive's default:
  flat face, temple dent, tube jaw, ball pads, box torso); R3c #50 (muzzle 3x too flat); R3c #58 (a derived ratio
  beat a directly registered landmark and made the ears too short).
- The ranking is the person's own engine-proof rule ("rank the evidence; weak evidence supports, never decides";
  "never guess: doubt becomes a flag; a genuine tie becomes one plain question") extended to dimensions the input does
  not contain at all. The procedure lives in the companion `engine-grounding` (G2, G3) so it is written once.
- Cost: a list and a citation per unknown; research once per domain, reused through the pack (A9).

## A7 - Build in the subject's own layers
- Person: "every area, every hair type, every colour/shade of hair comes from a surface on the cat, and grows in its
  own specified way"; and "the actual layers of whatever is being built ... (though the engine is a different type
  of layered system with its own unique structure)".
- Evidence: R2 #1 (blob trunk and limbs), R3b #49 (pads, jaw, tail root and ear bases got worse when blended wider:
  the parts were wrong), R3d #65-#66 (hair without an origin made halos and fringes past the ear's edge).
- Guard against dogma: only as deep as the defects require; each domain's layers are its own.

## A8 - Fresh builders
- Evidence: the contamination disclosure (cat engine METHOD.md, 2026-10-17): one agent orchestrated, built and
  scored in one conversation, read two AI-made answer keys, and used one of them as a depth source beyond the
  person's "measuring stick only" approval. The person also named drift in long sessions.
- The original already has the three roles and "a run that saw answers is recorded as not blind"; A8 makes the
  shared-session case explicit.
- Cost: more agent runs, and slower first rounds while the skill catches up with what the long session knew - which
  is the point: a fresh builder that fails shows what the skill is missing. Where one heavy tool is shared (one
  Blender on a 16 GB machine), builders run one at a time.

## A9 - Domain knowledge in packs
- Person: "are we building in such a way that it's methodology and principle rather than 'we're making a cat'?"
- Evidence: a vocabulary scan of the cat engine's core (2026-10-17): the shape builder holds 87 cat-anatomy terms,
  the groom 79, the rig 59; the coat-marking tool tests for purple, one cat's lilac. The original's "no case names in
  the toolkit" was kept, but the first case's KIND leaked in - the person's own lesson from an earlier project "the first example
  leaks in".
- Cost: moving knowledge out of the core is a refactor; do it in small steps against a baseline snapshot
  (`engine-grounding` G6).

## A10 - Prove a check against the failure it exists for
- Approved by the person 2026-10-18 (proposal R5 in the cat engine's `engine/log/RI_REFINEMENTS_PROPOSAL.md`).
- Evidence (cat engine, `tripo_rebuild/LOG.md`):
  - #43: a closest-point routine had a one-token bug that made 11-38% of distances too small. Its self-check sampled only points where the distance is zero, so it could not see the bug. Testing against brute force found it.
  - #57: a sign self-test skipped exactly the near-surface points where its bug lived. It passed with the bug present. Re-creating the old bug on purpose exposed it.
  - #81: a one-point plant tested a property the measure's definition does not claim. The 0.15 mm pass mark had been picked.
  - #82: a reviewer's plant set was written for one detector and outlived it. After the definition changed, the plants could no longer test it.
  - REVIEW_nose: a "correction" of a measured depth was itself wrong, because it had no proof.
- Outside 3-D:
  - A date-parser test that never hits the leap-day case the fix was for.
  - A dedupe check proven with exact duplicates when the bug is near-duplicates.
  - A regression test written against v1 of a function that still passes after v2 changed what the function returns.
  - A link checker tested on a missing page when the failure was a redirect loop.
- Relation to the original:
  - "Check the checks" asks that checks catch planted defects.
  - A3 asks for one quick test of a measure.
  - A10 says what makes that test count: it targets the failure the check exists for, its pass mark has a reason, and it is redone when the definition changes.
- Cost: proofs take longer to design. That cost is paid early, instead of late after decisions have rested on a wrong number.
- Risk: a proof programme for every throwaway number. The item names checks and measures; a value nobody acts on needs none.

## A10 - downstream note (A10 is a rule under A11)
- **Forbids:** trusting a check or measure whose proof did not target the failure it exists for.
- **Cost when wrong:** proofs take longer to design for checks that would have been fine. A10 applies only to checks and measures that something acts on.

---
A11-A18 were approved by the person on 2026-10-18. The source is the cat engine's `engine/log/RI_REFINEMENTS_PROPOSAL.md`, revision 2. The person held every item to one test: it must hold outside the domain it came from.

Two proposals did not come in:
- **Proposal R3 was REJECTED.** It read: "every defect that matters where it's used becomes a check". The person's reason: it needs an interpretive layer that lets an agent decide something doesn't matter, and skip it.
- **Proposal R7 moved.** "Measure in a thing's own frame" went to the 3-D engine's skill as its J14, not here.

## A11 - Rules and methods
- **Origin:** person, LOG #80. Prefer processes and methodologies to rules. Rules are handcuffs; some are necessary, but a binding rule can break the skill's effectiveness, so judge each one for what it does down the line.
- **Evidence:** two sensible rules combined into a blocker nobody intended. "Every defect becomes a check" plus an engine's "no accepted defects" turned every artefact of a reference into a blocker, until the person stepped in (LOG #79).
- **Adopted as LABELS only.** No original text was moved or reworded.
- **Outside 3-D:** in any engine, the ratchet is a rule, and running cases in waves of five is a method. The label tells a builder which one it may adapt to the case.
- **Helps:** keeps the skill adaptive in new domains.
- **Misleads:** a method can be skipped when inconvenient. A5 (replay every human review) shows what a skipped method cost.
- **Downstream note:**
  - Forbids: adding a rule without a written downstream note.
  - Cost when wrong: a needed rule waits for its note.

## A12 - Round 0 builds and proves the kit
- **Evidence:** the cat engine's Phase 1 (tripo_rebuild LOG #27-#82). About 50 log entries of building and proving measuring tools ran with no structure, exit criterion or budget, because the original skill's round assumes a working pipeline. The exit, "measured and mapped" (#79), was found late.
- **Person's wording for the tool sentence:** use standard or available tools when they exist, but always build additional tools whenever needed to help with analysis, measuring, planning and testing, so the work builds toward the highest standard set by the targeted outcome.
- **Outside 3-D:**
  - A website engine's kit is mostly off the shelf: a test runner, an accessibility checker, a link checker, screenshots at set widths compared with the design, and a performance budget. Plant one violation per check and confirm it fires. Add a tool wherever those can't see a criterion (for example, the copy matching the brief).
  - An import engine's kit is source-to-record reconciliation, schema checks, and generated answer-key files (`engine-proof`).
- **Downstream note:**
  - Forbids: starting blind rounds while any acceptance criterion lacks a proven check.
  - Cost when wrong: incomplete criteria end Round 0 too early. A5 turns each later human finding into a check.

## A13 - When something surprises you, find the cause before changing anything
- **Evidence:**
  - TOOLMAKING moves M1 (locate), M2 (measure the source), M5 (two methods) and M6 (what can't it see).
  - Every flawed measuring tool in that record missed at least one of three things: validation, measuring the source, measuring in both directions (§3).
  - The person's rule: "don't patch: measure what went wrong, rebuild, retest".
- **Relation:** widens A1. A1 stays, as one case of this.
- **Outside 3-D:**
  - A failing import: find which file, record and field before touching the mapper.
  - A broken layout: find which component, and at which width.
  - A wrong total: recompute it from the source rows, not from an intermediate table.
- **Helps:** turns "don't patch" from a prohibition into a procedure.
- **Misleads:** on a trivial surprise it is overhead, though the steps are quick there.

## A14 - Give a result its range
- **Evidence:**
  - The cat's nose v1: nostril size and depth moved with two guessed settings (REVIEW_nose).
  - Mouth v4 (LOG #82): over 14 runs, each one step either side on one setting, the left corner was stable to about 0.6 mm. Two named settings inflated the range, which is why the spread is reported with the outlier settings named.
- **Outside 3-D:** a dedupe similarity cutoff, a classifier threshold, a retry timeout, a cache size. Report the result across one step either side.
- **Not adopted: the proposal's "noise floor" half.** A3 already asks for a measure to be shown moving on a known difference (the input against itself), and the person found a noise-floor version of A3 too strict on 2026-10-17.
- **Helps:** ends debates over guessed settings.
- **Misleads:** a one-step range can miss a jump further out. Name the settings that move the result a lot.

## A15 - Narrow, parallel reviews with one standing question
- **Evidence:**
  - A broad review took about 33 minutes while work waited (person, LOG #53).
  - The independent reviewers found the cat engine's worst tool bugs (REVIEW_v3 B1, B2).
  - The standing question, "what can this not see, and was it tested on the failure it exists for?", would have caught all three classes of flawed tool (TOOLMAKING §3).
- **Outside 3-D:** one reviewer per API endpoint, per parser, or per claim in a report.
- **Helps:** reviews return in minutes, and several run side by side.
- **Misleads:** narrow reviews miss interactions between parts. Hence one whole-pipeline review at the end of each wave, plus the frozen regression (round step 8).

## A16 - Tools: reuse, make or alter, prove, record
- **Origin:** person, LOG #80. The tool library is good, but it must not be the only tools. Altering or creating a tool has improved effectiveness a great deal, as long as the tool is proven. The person also asked that tool-making never be mandated at a gate (TOOLMAKING header).
- **Evidence:** the cat engine wrote 106 measuring and checking scripts. A parallel session's tools transferred to another feature with small, measured changes.
- **Outside 3-D:** scripts, test helpers, parsers, fixture generators, checkers. Reuse the team's linter config before writing one; write a custom check when no linter rule sees the problem.
- **Helps:** keeps the tool-making that drove most of the progress, without a quota.
- **Misleads:** sprawl, and copies of one definition drifting apart. A formula used by several tools lives in one module, and the index shows what already exists.

## A17 - Show the person labelled, whole results
- **Evidence:**
  - The cat engine showed toe and nose markers with no label, and they misled the person twice.
  - A curve joined from separately measured points went through air, although every point lay on the surface (LOG #71).
  - Two claims were later retracted (LOG #63, #73).
- **Outside 3-D:**
  - **Website:** "screenshots at 375/768/1280 px: layout checks pass; copy and colours unchecked". Each component can pass its own tests while the assembled page overlaps at one width.
  - **Importer:** "20 sample records: totals reconcile; the date column is inferred from its format, unchecked". Every file can reconcile alone while the merged table double-counts the overlap.
  - **Report:** "figures checked against the source table; summary paragraph unchecked".
- **Helps:** the person's review time goes to real questions.
- **Misleads:** over-labelling clutters. One label per item is enough.
- **Downstream note:**
  - Forbids: showing results with no status, and showing an assembly that was checked only piece by piece.
  - Cost when wrong: a few words per item shown.

## A18 - A current-state block
- **Evidence:** the person had to ask "how are we doing", "I don't see you doing anything" and "how much of this is running through the engine?" (2026-10-18). Until they asked, there was no way to see how much of the work was being run by hand rather than through the skill.
- **Outside 3-D:** any engine, in any domain.
- **Helps:** the person never has to ask, and a drift away from the skill shows as it happens.
- **Misleads:** it goes stale if refreshed only on request, so it is refreshed whenever a round step, tool or review finishes.

## A8 - downstream note (A8 is a rule under A11)
- **Forbids:** counting work done in one shared session (orchestrating, building and scoring together) as blind.
- **Cost when wrong:** small tasks pay for a fresh agent. Work done in one session is still allowed; it is only recorded as "not blind".
- **Evidence it held:** in the cat engine Phase 1 the parallel paws session produced better tools than the orchestrating session, and the independent reviewers found the worst bugs (TOOLMAKING §3).

---
A19-A27 were approved by the person on 2026-10-18 (tripo_rebuild LOG #103), together with the cautions that protect the skill from contamination and from unintended conflicts. The drafts are in the cat engine's `engine/log/LESSONS_P2_DRAFT.md`. Two independent checks reviewed them (`engine/log/LESSONS_P2_CHECK.json`); the final wording merges both and keeps every safeguard either added.

- **Labels (A11):** rules A19, A21, A22, A23, each with a downstream note below; methods A20, A24-A27.
- **Evidence by LOG row only.** From A19 on, evidence is cited by `tripo_rebuild/LOG.md` row number, with no case facts. The case details in A14 and A17 above are not a precedent.
- **"Owner" has three meanings; keep them apart.** A part owns what grows on it (A7). A tool owner maintains a shared tool (A26). An engine's skill may name the builder responsible for a part. A check is never built on one meaning using another.

## A19 - The person's decisions become checks
- **Evidence:** tripo_rebuild LOG #94, #96, #101.
- **Relation:** adds to round steps 6 and 8 and to the ratchet. `engine-grounding` G12 already says decisions are the person's and observations are evidence. For approvals, A19 and `engine-grounding` G13 share one check and one report block, so two copies never diverge and "reported first" is never disputed.
- **Outside 3-D:**
  - "No dark mode this release" becomes a check that no dark stylesheet ships.
  - The person decides an import keeps the source's column order; a check compares the order on every build.
- **Helps:** a decision survives fresh agents and later rounds, because it runs as a check instead of living in a conversation.
- **Misleads:** a decision coded loosely binds the wrong thing. Hence "as stated, with no interpretation", and a question to the person whenever the check can't be written exactly.
- **Downstream note:**
  - Forbids: treating a decision as kept without a check that runs; building past an unchecked decision; giving a check to a decision the person did not make in their own message.
  - Cost when wrong: one question to the person per unclear or passed-on decision. A decision that can't be coded waits as OPEN and keeps the round open. A reversed decision needs the person to retire its check.
  - Switch: `A19_decisions_become_checks`.

## A20 - Hand-offs carry the conditions the next part needs
- **Evidence:** tripo_rebuild LOG #101.
- **Relation:** adds to A7 (each part owns what grows on it): what a part needs from the part beneath it is written down at the hand-off.
- **Outside 3-D:**
  - A parser stage's brief states the date format and time zone the report stage expects.
  - An importer's parser hands the reconciler records that keep their source row numbers.
- **Helps:** a later part's need is known before the earlier part is built, not discovered after.
- **Misleads:** a brief can carry case content past blindness. Hence conditions only, in the orchestrator's own words, with no scores, answer-key content, reference outputs or quoted input.

## A21 - Never message an agent while it runs a workflow or pipeline stage
- **Evidence:** tripo_rebuild LOG #91, #92.
- **Relation:** adds to A8 and to Round 0 step 5 (blindness by mechanism). A21 defines the notes file, which A19 and A26 also use. Every stage reads it, so it is the widest contamination channel these lessons add. That is why it holds no scores, answer keys or quoted case input, why each entry is marked by kind, and why it is data, never permission.
- **Outside 3-D:**
  - A CI job is not edited while it runs; it picks up a changed setting at its next stage, or it is cancelled and re-run.
  - A running data-cleaning job gets a corrected mapping table through the notes file at its next batch, or it is stopped and relaunched.
- **Helps:** every run's inputs are on record, so afterwards a run can be judged blind or not.
- **Misleads:** waiting for the next major step costs time when the late information matters at once. Then stop and relaunch; never message.
- **Downstream note:**
  - Forbids: a direct message to a running agent, and late information reaching a running stage by any route other than the notes file at its recorded read points or a relaunch.
  - Cost when wrong: a relaunch and the time the stopped run had spent, or a wait until the next major step. It does not apply to an agent that is idle or waiting for input.
  - Switch: `A21_no_midrun_messages`.

## A22 - Plant a failure on every side
- **Evidence:** tripo_rebuild LOG #100.
- **Relation:** tightens A10 and never loosens it. It uses A17's labels (checked, estimated, unchecked) and adds no fourth status.
- **Outside 3-D:**
  - A dedupe check proven on missed duplicates is also planted with a false merge.
  - A timeout check gets one value too short and one too long.
  - A stock-level alert is planted with one count too low and one too high.
- **Helps:** a check that sees only one side can no longer report a fix it cannot see.
- **Misleads:** planting both sides of a measure that truly fails one way only is wasted work. The written reason in the proof record covers that case; "unlikely" or "minor" is not such a reason.
- **Downstream note:**
  - Forbids: marking a defect fixed, or a result checked, from a one-sided proof.
  - Cost when wrong: one extra planted failure per check.
  - Switch: `A22_plant_both_sides`.

## A23 - Validate every fitted input on data it was not fitted to
- **Evidence:** tripo_rebuild LOG #93, #99.
- **Relation:** extends A12 to the fitted inputs that criteria rest on. It keeps Round 0 step 1's hold-out set and A6's answer key unspent. A case with a single input may have nothing to hold out. The fallback is the "estimated, unvalidated" marking with its results reported unchecked, so Round 0 can still end, nothing is passed off as validated, and A17 keeps its three statuses.
- **Outside 3-D:**
  - A column mapping inferred from sample files is checked on a file it was not inferred from.
  - A currency table or a schema is checked on records it was not built from.
  - A threshold tuned on past cases is checked on later ones.
- **Helps:** a fit that agrees only with its own data is caught before any criterion rests on it.
- **Misleads:** data set aside for validation is not used for fitting, so the fit can be a little weaker.
- **Downstream note:**
  - Forbids: a criterion resting on a fit checked only against its own data, and reporting such a criterion as checked.
  - Cost when wrong: the data held out from the fit. Where nothing can be held out: results labelled unchecked, and a question to the person.
  - Switch: `A23_validate_fitted_inputs`.

## A24 - Measure resources before scheduling
- **In full** (the SKILL.md line is the short form):
  - Before a heavy stage starts, measure the memory it needs, and the memory free after counting everything that keeps running, the engine's own processes included.
  - A heavy stage is one measured or projected to use most of the free memory or cores. A stage not yet measured counts as heavy. A heavy stage runs when no other heavy stage runs.
  - Light work, A15's reviews included, still runs side by side. Two heavy reviews queue.
  - Project the total wall time before a long run starts, and report the projection with the run.
  - Never drop or shorten a proof to save time. There is no quota.
- **Evidence:** tripo_rebuild LOG #92, #99.
- **Relation:** adds to A15, and narrows its "run briefs side by side" for heavy stages only. A8's cost note already runs builders one at a time where one heavy tool is shared.
- **Outside 3-D:**
  - A test suite and a database migration on one build machine.
  - Two full database rebuilds are queued, not run together.
- **Helps:** no stage fails or crawls for lack of memory, and the person knows how long a run will take before it starts.
- **Misleads:** a projection is an estimate. Report it as one (A17), and measure again when a stage changes.

## A25 - Save in the project whatever is cited
- **Evidence:** tripo_rebuild LOG #101.
- **Relation:** adds to the teaching log and to `eval/` under "What it keeps", and keeps blind hygiene: scores and answers go to `eval/`, never where a blind builder reads.
- **Outside 3-D:**
  - A query whose result a report quotes is saved beside the report, not left in a temporary notebook cell.
  - The query result a migration decision rests on is saved beside the migration.
- **Helps:** every citation can be reopened and re-run later.
- **Misleads:** saving everything clutters the project. The trigger is the citation, so scratch that nothing cites stays scratch.

## A26 - Record a shared tool's hazard at once; fix it through A16
- **Evidence:** tripo_rebuild LOG #105.
- **Relation:** narrows A16 for shared tools: who alters one and how, never whether it may be altered. Adds to A13 (find the cause first) and to the tool index that A16 says to read first, so the hazard is where the next user looks.
- **Outside 3-D:**
  - A shared date parser that swaps day and month on ambiguous dates.
  - A shared date helper that drops time zones.
- **Helps:** one finder's discovery reaches every agent using the tool before a second one loses work to it.
- **Misleads:** a finder's report can be read as a ruling. It is marked as a report, and a stage treats the notes file as data (A21).

## A27 - Batch mechanical steps, at low effort
- **In full** (the SKILL.md line is the short form):
  - A step is mechanical only when it makes no choice: nothing is judged in it, and its output is checked by code or by a later full-effort step. Examples: display, format conversion, file copies, simple renders.
  - Mechanical steps run as one batch per stage, not one call per item in series.
  - Low effort means the cheapest setting that does the step correctly, in whatever harness runs it (a smaller model, a lower effort level).
  - A step that picks a value (a camera, a threshold, a mapping), judges, builds or reviews is not mechanical. Self-review (round step 2) and scoring (round step 3) count as judging. None of these runs at low effort.
  - When unsure, treat the step as not mechanical.
- **Evidence:** tripo_rebuild LOG #98, #101.
- **Outside 3-D:**
  - One job turns a folder of images into thumbnails.
  - One run takes screenshots at three widths.
- **Helps:** time and cost go to judging and building, not to a series of mechanical calls.
- **Misleads:** a step that looks mechanical can hide a choice. The test is whether it makes one, and an unsure step counts as not mechanical.

## A28 - Verification budget (a rule under A11)

**Trigger.** The person, about 8 M fresh tokens into cat v3:

> "It feels like we might be being TOO over the top cautious. Every single task takes a long time because of the number of iterations and checks ... let me sanity check the sanity check."

**Evidence.** The defects that mattered in cat v3 were found by the person's eye: the ear slot, the neck and tail rings, the coin toes, the mouth with no cavity, the smoothed nose. They had passed a deep stack of measures, second measures, ranges, planted proofs and review agents. The layers cost wall time and tokens on every task, and did not buy the catches.

**Downstream note.**
- **What it forbids in cases not met yet:**
  - second measurements "just in case";
  - a review agent before a human review;
  - reviews of reviews and re-proofs;
  - whole-output re-scans after a local fix.
- **What it keeps:**
  - the never-graduate areas, with their full human approval;
  - the decision checks that protect approvals (A19);
  - existing automated checks, run once per change.
- **Cost when wrong.** A defect that an extra layer would have caught reaches the person's review. That costs one round.
- **Switch.** `A28_verification_budget` in flags.json.

**Item 9 (approved by the person 2026-10-21).** The person, watching build 13a: "every check is checking every surface
area ... he just edited 1 area, he should be checking only that area". Measured from 13a's transcript: 24 whole-body
mesh checks (13.1 s each) and 18 whole-body crossing checks (8.4 s each), about 7.8 minutes of its 38 tool-minutes, on
a mesh where 21,853 of 686,162 vertices (3.2 %) had changed. One vertex diff against the base, 0.15 s, proves the rest
unchanged. The checks also re-found, every round, faults that were already in the base body outside the edit (787
folds past 90°, 6,876 crossing pairs: identical on the base alone). The person's wording for those: "recorded once as
known and fixed and remeasured independently", so that a baseline never becomes "oh yea, we already know about that,
it's fine" (`cases/woman2/KNOWN_FAULTS.md`). Items 6 and 8 already said to scope checks; 13a never read them, because
builders read the engine's skill and its builder primer, not this skill. The primer now points here.
- **What it adds:** the diff that makes scoping safe; whole-output checks once per accepted stage and before showing;
  known faults outside the change get their own fix and re-measure, never acceptance.
- **Cost when wrong:** a change that leaks outside its part is caught by the diff, not by a check, so the part is
  widened; a fault outside the part waits for its own fix job instead of blocking the current one.

**Across domains.**
- Website engine: "the part" is the page or component, and "the look" is viewing it.
- Data import: "the part" is the table touched, and "the look" is reading sample rows.

## A29 - Compare against a known good base by stacking (a method under A11)

**What.** When a known good base model (a reference) is compared with generated models to judge fit, quality or
measurements, all of them are stacked at one fixed position, the same place, orientation and size, and compared there.
The position comes from evidence both share (a camera, landmarks, one shape-neutral anchor) before anything is
measured.

**Evidence (cases/woman2/LOG.md, rounds 3b-3d, 2026-10-19).**
- Two torsos were scored against the person's 3-D references with averaged two-sided distances, each after its own
  fitted depth shift. The shift slid the torso with almost no breast volume forward until its averages looked fine,
  and the ranking came out opposite to the person's review.
- With everything stacked at one fixed position (the photo's camera for width and height, the waist section's centre
  for depth), the overlays and cross-sections agreed with the person at once: 56 mm missing at the nipple against
  11 mm for the other torso. The same overlay also exposed a defect nobody had listed (nipple forms showing through on
  the back).

**When it helps.** Any comparison with a reference: shapes, renders, layouts, reports, data exports.
**When it misleads.** If the fixed position itself rests on a feature that differs between the two (an anchor on the
breasts or the buttocks would bias the comparison), the stack inherits that bias. Choose an anchor the difference
being judged does not move.
**What it leaves open.** Which tools compare the stack is not fixed: the builder picks the tool that shows the
difference best (A16), and keeps a tool that has matched the person's eye.
**Cost.** One alignment step before measuring; nothing else.
