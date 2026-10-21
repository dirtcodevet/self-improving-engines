# Lesson reporter - design spec (v0.1, draft for the maintainer's decisions)

Status: **design + local prototype.** The prototype (`plugins/lesson-reporter/`) builds redacted packages in a
local outbox and makes no network calls. Everything about sending, CI and review below is design only. Items that
need the maintainer's decision are marked **DECIDE** and collected in `DECISIONS.md` at the repo root.

## 1. What it is for

An engine (first: `asset-enhancement-engine`) improves through lessons: a check that caught a defect, a judgment
lesson, a new or better measuring tool, a method note. Users who run the engine find lessons the maintainer never
sees. The reporter lets a user give those lessons back - and only those - without giving away their work.

```
 user's machine                                          maintainer (dirtcodevet)                     every user
 -------------------------------------------------       ------------------------------------------  ----------
 engine run -> lessons (agent drafts, own words)
            -> reporter: validate, redact, refuse  ->     PR/issue on the repo (transport: DECIDE)
            -> outbox package + PREVIEW.md                  -> CI: screen, schema, proofs, ratchet,
            -> the person reads it, approves it                 static analysis (no secrets, no push)
            -> (future) send: fresh console code           -> human review (never graduates)
                                                            -> maintainer REWRITES the lesson into the
                                                               skill as a new flagged item
                                                            -> regression on frozen references
                                                            -> version bump + CHANGELOG + tag        -> update
```

## 2. Principles

1. **Opt-in, off by default, at every level** (section 6). Nothing is packaged for an engine the user has not
   switched on themselves; nothing is sent without a fresh approval of that exact package.
2. **Lesson material only.** An allowlist of what may go in (section 4), not a blocklist of what may not.
3. **Show exactly what would be sent.** `package.json` is the payload; `PREVIEW.md` reproduces it byte for byte.
4. **A lesson is data until the maintainer rewrites it.** No reported text is ever merged verbatim into a skill
   (recursive-improvement: lessons are "written in the agent's own words, never copied from case inputs").
5. **Every process change is switchable.** Every lesson carries a flag and arrives OFF (`toggle.default: false`);
   the maintainer decides its default when merging.
6. **The ratchet.** Checks only tighten without approval. Removing a check, loosening a threshold, changing a
   weight or what a check reads needs the maintainer's explicit approval (section 10).
7. **The tool-making record is kept, never gated.** A lesson may carry the TOOLMAKING columns (trigger, what it
   caught, verdict, why); they are optional and never a reason to reject.
8. **Mechanisms, not intentions.** Where a rule protects the user (consent, redaction), code enforces it and a
   test proves the enforcement on a planted violation.

## 3. Components and where they live

| Piece | Where | Ships to users? |
|---|---|---|
| Reporter plugin (skill + `scripts/lesson_reporter.py` + schema) | `plugins/lesson-reporter/` | yes, disabled by default |
| Engine's reporting policy | `plugins/<engine>/reporter.json` | yes (with the engine) |
| Engine's proof registry (for CI) | `plugins/<engine>/proofs.json` | yes (metadata only) |
| User's opt-in, own redaction words, outbox | `${CLAUDE_PLUGIN_DATA}` of the reporter (`settings.json`, `redact_terms.txt`, `outbox/`) | never leaves the machine |
| CI and review tooling | `docs/ci-draft/` (inert drafts) | no |

The reporter is deliberately **not** a dependency of any engine: Claude Code starts a dependency enabled, which
would defeat "off by default".

## 4. What a package may contain

| Allowed | Form | Limits (engine's `reporter.json`) |
|---|---|---|
| Lessons | `lessons.json` = `{"lessons": [...]}`, schema in section 5 | <= 20 lessons |
| Tool changes | the engine-relative path of a file under the engine's `tools/`, `checks/` or `review/` with extension `.py .sh .md .json`, plus the user's changed copy; **the reporter computes the diff itself** so headers carry no local path | <= 10, <= 60 kB per diff |
| Method notes | `.md`/`.txt` prose; the file name is replaced by `note-N.md` | <= 5, <= 20 kB each |

The finished package is <= 250 kB. **Never**, whatever the folder: images, renders, photos, meshes, scenes,
arrays, archives, media, documents, executables (extension list in `FORBIDDEN_EXTENSIONS`), anything binary or
not UTF-8, anything under `cases/` or `eval/`, anything outside the engine.

## 5. Lesson schema (`lesson-report/0.1`)

JSON Schema: `plugins/lesson-reporter/schema/lesson.schema.json`; the prototype enforces the same rules in code and
a test keeps the two in step. Unknown fields are refused.

| Field | Req. | Rule |
|---|---|---|
| `id` | yes | sender-local id (`METHOD-92`, `TM-frame_fit`), `[A-Za-z0-9._#-]`, <= 64 |
| `kind` | yes | `check`, `judgment`, `tool`, `method_note` |
| `target` | yes | one of the engine's `lesson_targets`: the engine, `recursive-improvement`, `engine-grounding` |
| `title` / `statement` | yes | <= 120 / <= 1500 characters, the agent's own words |
| `evidence[]` | yes, 1-10 | `log_ref` (e.g. `METHOD.md#92`), `summary` <= 500, optional `measured` {metric, before, after, unit} - numbers, not data |
| `toggle` | yes | `{flag: "J14_short_name", default: false}` - **always false** |
| `ratchet` | yes | `{loosens: bool, what: "..."}`; `what` required when it loosens |
| `proof` | for `check`/`tool` | `{planted_defect, command, expect: "fails_on_planted"}`; command = one `python|bash <engine tool> args`, no pipes, chaining, quotes or outside paths |
| `replaces` | no | ids of lessons this one supersedes |
| `tool_change` | no | the path of a tool change in the same package |
| `toolmaking` | no, never required | `{trigger, caught, verdict: good|superseded|flawed, why}` |

The package (`package.json`) adds: `schema`, `reporter_version`, `engine`, `engine_version`, `created` (date only),
`tool_diffs[] {path, change, diff}`, `notes[] {name, text}`, `links[]` (plain source links found in the prose),
`attention[]` (risky code constructs found in diffs, for the reviewer) and `redactions` (counts per category -
never the values). **DECIDE**: schema versioning rule (proposal: minor = additive, major = breaking; the
maintainer's CI accepts the current and previous minor).

## 6. Consent

Four switches; each is independently off:

| # | Switch | Default | Who | Mechanism |
|---|---|---|---|---|
| 1 | Reporter plugin enabled | OFF (`defaultEnabled: false`) | user | Claude Code `/plugin` |
| 2 | Engine accepts reports | per engine (`reporter.json accepts_reports`) | maintainer | shipped config |
| 3 | Reporting ON for this engine | OFF (no entry in `settings.json` = OFF; unreadable = OFF) | user | `enable`: one-time code at the console |
| 4 | This package approved | not approved | user | `approve`: one-time code at the console, bound to the package sha256 |
| 5 | (future) Send | - | user | `send`: a *fresh* code at the console, re-verify, re-screen |

**The console gate.** `enable` and `approve` print a random one-time code on the console device (`CONOUT$` on
Windows, `/dev/tty` elsewhere) and read the answer from the console's own keystrokes - never from stdin. An
agent's shell has no person at that console: the prompt times out (default 300 s) and nothing changes. Switching
OFF (`disable`) never needs confirmation. The approval records the package's sha256; any later change to
`package.json` voids it (`verify`).

**Limits, stated honestly.** The console gate stops an agent from switching reporting on or approving *through
the reporter*. It cannot stop a process that can write files from editing `settings.json` or writing
`APPROVAL.json` by hand. That is why the step that matters - sending - must ask for its own fresh console code at
send time and must not trust any file on disk as consent (section 8).

**Withdraw:** delete the package folder. **Stop:** `disable`, or disable the plugin; uninstalling the plugin
deletes its data folder (Claude Code removes `${CLAUDE_PLUGIN_DATA}` on uninstall).

## 7. Redaction and refusal

Order (prototype `prepare`): read input -> refuse forbidden types / binary / oversize -> **screen the raw text and
every decoded JSON string** (secrets, invisible characters) -> validate the schema -> **redact** -> screen the
redacted text -> **leak check** of the finished package -> write the outbox. Any problem refuses the whole package
and nothing is written.

**Redacted (replaced):**

| Category | Detected by | Becomes |
|---|---|---|
| Paths inside the engine | absolute path that starts with the installed engine folder | `<engine>/tools/x.py` (kept: it is lesson context) |
| Any other absolute path | drive paths `C:\..`/`C:/..` (also `\\` doubled inside source code), UNC `\\host\share`, `/c/..`, `/home/..`, `/Users/..` and other POSIX roots, `~/..`, `%USERPROFILE%..`, `$HOME/..`, `file://` | `<path>` |
| Case folder names | `cases/<name>` | `cases/<case>` |
| E-mail, IPv4 | patterns | `<email>`, `<ip>` |
| The user's own identity | home-folder name, `USERNAME`/`USER`/`LOGNAME`, `COMPUTERNAME`/`HOSTNAME`, `~/.gitconfig` [user] name (and each part) and e-mail | `<user>`, `<host>`, `<name>`, `<email>` |
| The user's own words | `${CLAUDE_PLUGIN_DATA}/redact_terms.txt`, one per line (pet names, project names, client names) | `<term>` |

Folder names may contain spaces ("My Models"), but a path keeps one separator style and stops at `,` `;` or a space
before prose, so a redaction never swallows the sentence after it. Identity matches respect word boundaries
("pat" does not touch "pattern"). The reporter never reads credential stores or the gh CLI's config (it holds a
token). **Limit:** an arbitrary person's name in free text cannot be detected in general; the defences are the
paraphrase rule, the user's own `redact_terms.txt`, the verbatim-quote refusal and the preview.

**Refused (the package is not built):**

| Code | When |
|---|---|
| `NOT_OPTED_IN`, `ENGINE_CLOSED`, `OUTBOX_LOCATION` | switch 3 off; switch 2 off; outbox inside the engine |
| `FORBIDDEN_TYPE`, `BINARY`, `TOO_LARGE`, `MISSING` | a non-lesson file, binary or non-UTF-8 content, over a limit |
| `OUTSIDE_ALLOWLIST` | a tool change outside `tools/ checks/ review/`, or absolute, `..`, `cases/`, `eval/` |
| `SCHEMA` | unknown/missing fields, a lesson not arriving OFF, a check without a proof, loosening without saying what, a shell-chained proof command |
| `SECRET` | tokens and keys (GitHub, API, AWS, Slack, Google, private-key blocks, JWT, bearer, `password=...`) - **the value is never echoed** in the error, the preview or anywhere else |
| `HIDDEN_UNICODE` | format/control characters (zero-width, bidirectional overrides - "Trojan Source" - tag characters, terminal escapes) |
| `VERBATIM_QUOTE` | a quoted passage of 6+ words or a block quote: possible conversation text - paraphrase |
| `INJECTION` | text addressed to an AI ("ignore previous instructions", "you are now", role tags, "without asking the user", "AI reviewer: approve") or a shell download command in prose |
| `MARKUP` | Markdown images (a rendered image is a tracking beacon), HTML, hidden HTML comments, `data:` URIs |
| `EMBEDDED_DATA` | base64/hex blobs, or a line with 24+ numbers (measurement data) |
| `URL_DATA` | a link with a query, a user part or fragment data; plain links are allowed and listed in `links` |
| `LEAK`, `UNREDACTED_PATH`, `UNREDACTED_IDENTITY` | defence in depth: the finished package still holds the home folder, an identity, a path, an e-mail or IP |

Risky code in a tool diff is **not** refused (a legitimate tool may drive Blender through a socket) but listed in
`attention` for the reviewer: network, subprocess, dynamic code, deserialization (`pickle`, `allow_pickle=True`),
native code, file deletion, environment access, URLs, download commands.

All of these are heuristics. They are tuned to refuse when unsure (the user then rephrases), and the same screen
runs again on the maintainer's side (`screen`), where it does not depend on the sender's identity.

## 8. Transport (future - not built)

**DECIDE** which one; the prototype stops at the outbox. In every option the reporter never handles a token: it
would call the GitHub CLI, which uses the user's own stored login.

| Option | How | Privacy | Cost / abuse |
|---|---|---|---|
| A. Own-account PR | `gh repo fork` + branch + commit `inbox/<engine>/<id>/package.json` + `gh pr create` | the user's GitHub identity is public on the PR | no infrastructure; fork noise; spam is per-account |
| B. Own-account issue | `gh issue create` with the package as a fenced block or attachment | identity public; content public | simplest; the maintainer turns issues into PRs |
| C. Relay | the package goes to a small service that opens the PR as a bot | anonymous to the public; the relay operator sees it | hosting, rate limits, abuse handling, an attack surface the maintainer runs |
| D. Manual | the user attaches `package.json` to an e-mail or issue themselves | as the user chooses | nothing to build |

Suggested order: D now (it works with the prototype as is), then B or A, a relay only if anonymity turns out to
matter to users. Also **DECIDE**: whether packages and PRs are public (a public repo makes them public).

Whatever the option, `send` must: re-verify the sha256 against the approval; re-run the full screen; show the
exact command and the destination; ask for a **fresh** console code; send only `package.json`; record the result
(PR/issue link) in the package folder; never retry silently.

## 9. The maintainer's review gate

1. **Intake.** A package arrives as `inbox/<engine>/<id>/package.json` in a PR (or is copied there from an issue).
   Nothing in `inbox/` is ever loaded by a plugin.
2. **CI first** (section 11). A PR whose proofs, screen or ratchet check fail is not reviewed until fixed.
3. **Human review - mandatory, never graduates.** Merged lessons become instructions that other people's agents
   follow, and publishing is public and hard to reverse: recursive-improvement's "never graduates, by policy". An
   AI reviewer may assist (engine-grounding G9: it supports, never decides; run it read-only, with no secrets, and
   disclose its model family).
4. **Rewrite, never paste.** The maintainer writes the lesson into the skill in their own words, as a new item
   with its own flag (`Jn`, `An`, `Gn`, `En`) and its evidence, citing the package id. Diffs to tools are
   re-applied by hand or with `git apply --3way` (context lines were redacted, so they may need fuzz) and get a
   TOOLMAKING row.
5. **Regression.** Re-run the frozen reference cases (re-execute; don't compare files). The proofs must still pass.
6. **Release.** Bump the plugin's `version` (users stay on a pinned version until it changes), write the
   CHANGELOG entry (what changed, which flag, default ON/OFF, which package it came from), tag the release.
   **DECIDE** the versioning scheme.
7. **Users update** with `/plugin marketplace update` (auto-update is off by default for third-party
   marketplaces; the README tells users how to turn it on if they want it).

## 10. The ratchet in CI

A change **loosens** when it: deletes a check or a planted defect from a proof; removes or weakens an assertion;
moves a threshold in the permissive direction; changes a severity weight or a demotion threshold; changes what a
check reads or the answer key's format; switches a check's flag from `true` to `false`; removes an entry from
`proofs.json`.

Mechanism (design): a `ratchet` job compares the PR's base and head for (a) files deleted under `checks/`;
(b) `proofs.json` entries and their `plants` lists; (c) threshold files (`checks/proportion_priors.json`,
`priors.json` ranges) - a range that widens is a loosening; (d) numeric constants in `checks/*.py` via an AST diff,
each reported for a person to classify (direction cannot be inferred in general); (e) `flags.json` true -> false.
Any loosening fails the job unless (1) the reported lesson declared `ratchet.loosens: true` with `what`, and
(2) the maintainer applied a `ratchet-approved` label (only CODEOWNERS can). The approval and its reason go into
the CHANGELOG. A loosening never travels in the same PR as unrelated changes.

## 11. CI design (draft workflow: `docs/ci-draft/lesson-intake.yml.draft`, inert until renamed)

Trigger `pull_request` (never `pull_request_target`), `permissions: contents: read`, no secrets, actions pinned to
full commit SHAs, each job switchable. Jobs, in order:

| Job | What | Runs now? |
|---|---|---|
| `screen` | `lesson_reporter.py screen` on every `inbox/**/package.json`; schema, refusals, leak check | yes (stdlib Python) |
| `reporter-tests` | the reporter's own tests | yes |
| `manifests` | `claude plugin validate . --strict` and each plugin | yes (needs the Claude Code CLI installed in the job) |
| `skill-lint` | skill files: no hidden unicode, no fetch/download commands, no URLs outside an allowlist, no instructions aimed at disabling checks, flags.json and SKILL.md items in step | to build |
| `static` | for tool diffs: new imports and dependencies, the `attention` constructs, binary files; a hit needs a `code-reviewed` label | to build |
| `proofs` | **each touched check's own planted-defect proof** from `proofs.json` (reference passes, every planted defect caught), then all proofs | blocked: needs public fixtures |
| `ratchet` | section 10 | to build |
| `blender-proofs` | proofs that need Blender, headless in a container | later |

**Why proofs run before review:** the reviewer's time goes only to lessons whose checks demonstrably catch their
defect - recursive-improvement's "every defect becomes a check that fails on the output from before the fix".

**The fixture gap (blocking).** Every current proof needs a build or a 3-D reference made from the private photo
case (and one reference is an AI generator's output under its own terms, another an answer key). None can be
published. CI needs **synthetic, redistributable fixtures**: generated cases whose answer is known by
construction (recursive-improvement Round 0: "a generator whose made-up cases are the answer key"). Until they
exist the `proofs` job reports "not runnable here" rather than pretending to pass.

## 12. Threat model

Assets: the users' private work (photos, meshes, names, paths); the integrity of the skills and tools every user's
agent runs; the maintainer's account and repo; users' machines (tools run as Python with full access, often
inside Blender).

Trust boundaries: (1) the user's machine -> the package; (2) the package -> the maintainer's CI and reviewer;
(3) the maintainer's merge -> every user's agent and machine. Boundary 3 is the critical one: **after a merge, a
lesson is an instruction other people's agents follow and a tool is code they run.**

| # | Threat | Mitigations | Residual risk |
|---|---|---|---|
| T1 | Prompt injection in lesson text, aimed at the maintainer's reviewer agent or, after merge, at every user's agent | refusal patterns on both sides; lessons are data, rewritten by the maintainer, never pasted; human review mandatory; skill-lint; merged items arrive behind flags | novel phrasings pass heuristics - the human rewrite is the real control |
| T2 | Malicious code in a tool diff (runs in CI and later on every user's machine) | CI with no secrets and read-only token; `attention` + `static` job; human review; no auto-merge; reviewers read diffs with hidden unicode refused | a subtle malicious change can pass review - keep diffs small, one concern per PR |
| T3 | Supply chain: maintainer account or token compromised; a bad release reaches users | 2FA, branch protection, CODEOWNERS, signed tags; version pinning (users update only on a version change); auto-update off by default; CHANGELOG per release | an account takeover is still severe: users should update deliberately |
| T4 | Impersonation: a look-alike marketplace or plugin name | publish one canonical repo URL; the README states the only source; releases are signed tags | users can still add a fake marketplace |
| T5 | Dependency confusion: a lesson adds a pip/npm dependency | `static` job flags any new import or dependency file; dependencies pinned by hash when added | - |
| T6 | Privacy leak from the user | allowlist of content; redaction; leak check; preview; per-package approval; maintainer-side re-screen | free-text names; a user who approves without reading |
| T7 | Consent bypass by an agent | console one-time code (not stdin - see Findings); fresh code at send time; files on disk never count as consent to send | a process with file-write access can forge local records, which is why send asks again |
| T8 | Check poisoning: a "lesson" that loosens a check or removes a planted defect | the ratchet job + `ratchet-approved` label; lessons must declare loosening | - |
| T9 | Data poisoning: subtly wrong priors or pack numbers that degrade output | engine-grounding G2/G7 (every value carries its source; a tuned value carries its case); pack changes need cited sources; regression on frozen references | slow drift - watch the regression numbers per release |
| T10 | Exfiltration through rendered Markdown (image beacons, hidden comments) when the maintainer views a PR | `MARKUP` refusal both sides | - |
| T11 | Unsafe deserialization (`pickle`, `allow_pickle=True`) | binaries refused; `deserialization` attention flag | existing engine tools already load .npz files: keep `allow_pickle` off |
| T12 | The reporter itself turned hostile by an update (it is the code that reads user files) | it has no network code (a test fails on any network or process import); transport kept separate and opt-in; reporter changes get the strictest review | the transport, once built, is the sensitive part |
| T13 | Spam / denial of service on the maintainer | per-account PRs (A/B) or relay rate limits (C); CI cheap jobs first | - |

## 13. Toggles

Every process piece can be switched off on its own: the reporter plugin (`/plugin`), reporting per engine
(`disable`), an engine's intake (`accepts_reports`), each merged lesson (its flag), each CI job (job-level `if:`
on a repository variable), and the transport (absent in the prototype).

## 14. Findings while building the prototype (kept in the spirit of the tool-making record)

| # | What happened | How it was found | Fix | Test |
|---|---|---|---|---|
| F1 | The first gate trusted `sys.stdin.isatty()`. On Windows the NUL device is a character device, so `isatty()` is True for an agent's shell, and `enable` **succeeded from the agent's own shell**. | smoke-testing the CLI from the agent shell before calling it done | one-time code on the console device, keystrokes read from the console, never stdin; timeout | the bypass was reproduced against the old code first (stdin = NUL -> "reporting ON"); `test_enable_from_an_agent_shell_is_refused` and `test_approval_from_an_agent_shell_is_refused` run the real CLI with stdin = NUL and with stdin piped |
| F2 | The raw-text screen ran on the JSON file; `json.dumps` writes `\u200b` as an escape, so invisible characters - and a token written with a `\u` escape - passed. | a test failing for an unexpected reason | screen every decoded string too, on both sides | `test_secret_hidden_behind_a_json_escape_is_refused`, `test_hidden_unicode_is_refused` (both fail on the pre-fix code) |
| F3 | Allowing spaces in folder names let one path run on through ", \\host..., and ~/..." and swallow the prose between three paths. | the three-path test counted 2 | one separator style per path; folders may not start with a space or hold `,` `;` | `test_git_bash_unc_and_tilde_paths_are_redacted` |
| F4 | The redactor's own `<user>` placeholder tripped the role-tag injection pattern. | test failure | screen with the placeholders neutralised | `test_user_host_and_git_identity_are_redacted` |

## 15. Not built yet

Transport; the CI jobs other than what the draft workflow shows; skill-lint; the ratchet job; synthetic fixtures;
a maintainer-side `apply` helper that turns a package into a draft PR description (lesson text quoted as data,
with the rewrite left to the maintainer); localisation of the refusal messages.
