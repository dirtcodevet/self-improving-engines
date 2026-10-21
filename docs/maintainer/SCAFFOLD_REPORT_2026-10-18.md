# Status report - local scaffold, 2026-10-18

Local git repo only: no GitHub repo created, nothing pushed, no network service called. The originals in the
project folder were only read.

## Ready

- **Marketplace + 4 plugins** in Claude Code's plugin format (checked against the current docs at
  code.claude.com; `claude plugin validate --strict` passes for the marketplace and each plugin):
  `recursive-improvement`, `engine-grounding` (depends on recursive-improvement), `asset-enhancement-engine`
  (depends on both), `lesson-reporter` (`defaultEnabled: false`, deliberately not a dependency of anything, since
  dependencies start enabled).
- **Byte-identical copies** of the two method skills (with SKILL.original.md and flags) and the whole engine
  folder; `SOURCES.json` + `tools/verify_copies.py` prove it (197 files, 0 copies differ) and list what the
  project changed since the snapshot.
- **incoming/** with the 38 `tripo_rebuild/*.py` tools + `LOG.md` + `LOG_paws.md`, marked UNREVIEWED, outside every
  plugin (never installed). The paws/rebuild work is still running: `verify_copies.py` already shows 5 of those
  sources changed after the 09:00 UTC snapshot.
- **Reporter spec** `docs/lesson-reporter/SPEC.md`: lesson schema, allowlist, redaction and refusal rules, the
  consent switches, transport options, the review gate, CI (proofs before review), the ratchet in CI, a 13-item
  threat model with prompt-injection and supply-chain risk, toggles, findings.
- **Outbox prototype** `plugins/lesson-reporter/scripts/lesson_reporter.py` (stdlib only) + JSON Schema + example
  + **49 passing tests**: consent off by default; paths, user/host names, git identity, e-mails, IPs, case names
  and the user's own words redacted; pictures, meshes, scenes, arrays, binaries, `cases/`/`eval/`, secrets (never
  echoed), invisible characters, quoted conversation, AI-addressed text, markup and data refused; package only in
  the outbox; approval bound to the package hash; no network or process imports; `send` disabled.
- **CI draft** `docs/ci-draft/lesson-intake.yml.draft` (inert file name) and an engine `proofs.json` registry.

## Findings worth knowing (SPEC section 14)

- **F1 - the first consent gate was bypassable by an agent.** It trusted `stdin.isatty()`; on Windows that is
  True for the NUL device an agent's shell uses, and `enable` succeeded from my own shell. Replaced by a
  one-time code shown on, and read from, the console device itself. The bypass was reproduced on the old code; two
  tests now run the real CLI the way an agent would. Limit: a process that can write files can still forge the
  local records - so the future `send` must ask for a fresh code and trust no file as consent.
- **F2 - JSON escapes hid characters from the screen** (an escaped token or zero-width character passed). Every
  decoded string is now screened too, on both sides.
- **Proofs can't run in public CI yet:** every check's planted-defect proof needs a build or reference made from
  the private case (and the Tripo/Rodin meshes can never be published). Synthetic generated fixtures are the
  blocking piece for CI.

## Needs your decisions (details: `DECISIONS.md`)

License (D1; note the CC BY-SA skull data and the Grok illustrations) - repo/marketplace names (D2; working name
`self-improving-engines`) - versioning (D3; set to 0.1.0 / reporter 0.0.1 for now) - transport: manual, issue,
own-account PR or relay (D4) - whether reports are public (D5) - default of a merged lesson (D6) - binary packs,
93 MB (D7; kept out of git for now) - packaging `engine-proof`/`generative-pipeline` (D8) - reporter opt-in
mechanism (D9) - moving the repo out of OneDrive (D10) - publishing personal content (D11).

## Waits for your lessons assessment (before anything is published)

- Which RI additions A1-A9, grounding items G1-G12 and engine items (E/J flags) ship, and in what wording.
- Engine content: case-specific text (`cat1`), the person's quotes, `NOTES_LEDGER.md`, the METHOD/TOOLMAKING
  logs; the `../skills/...` path references in the engine SKILL.md (they need to name the plugins instead); two
  personal paths left in copied files (`tools/views.py`, `references/cat-standing-posture.md`).
- The uploading tools (`tools/trellis_space.py`, `tools/rodin_ref.py`) - per-use consent, maybe an OFF flag.
- Every `incoming/` tool: what enters the engine, parameterised to take its reference as input instead of the
  fixed `tripo_welded.npz`, writing outputs to the case folder.
- Which tool-making reasoning travels with each tool (kept as a record, never a gate).

**Before the first push:** the local history contains everything copied today (images included, binaries
excluded). Anything the assessment drops should leave the history too - simplest is to publish from a fresh,
squashed history.

## Verified here / not verified

Verified: `claude plugin validate --strict` (marketplace + 4 plugins: passed; advice only about install lines
naming a real repo); `python -m unittest discover -s plugins/lesson-reporter/tests` (49 OK); `verify_copies.py`
(0 copies differ); the example lessons through the real `prepare` with this machine's identity (paths redacted;
the console step was simulated in that demo).
Not verified: installing the plugins through `/plugin` (the same skills are already installed here as junctions,
so it would load them twice); the engine's tools running from the plugin layout; the console gate typed by a
person in a real terminal (the code path with a FakeConsole is tested; the real console path is only tested for
refusing); POSIX `/dev/tty` path (written, not run - this machine is Windows).
