# Open decisions (the maintainer's)

## Decided (the maintainer, 2026-10-21, for the public release)

- **D1 License:** Apache-2.0 for the repo (`LICENSE`); third-party pieces keep their own terms (`NOTICE`).
- **D11 Personal content:** keep the maintainer's quotes as they are ("the person", dated), as the evidence behind
  each lesson, and keep the case names. Personal folder paths and the name of the maintainer's other project are
  rewritten when the copies are published (`tools/publish_rules.json`, "rewrite").
- **Engine name:** the engine is published as `asset-enhancement-engine` (it was `photo-to-blender-creature`); the
  project keeps its old skill name, and the rename is one of the publish rewrites.
- **Fresh history:** the public repo starts from one clean commit in a new repository; today's repository is renamed
  `self-improving-engines-archive` and stays private with its full history.
- **D10 Repo location:** settled; the repo now lives in the maintainer's Projects folder, not OneDrive.

## Still open

Where there is a suggestion it is marked as one.

| # | Decision | Options | Notes / suggestion |
|---|---|---|---|
| D1 | **License** | one license for all (e.g. Apache-2.0 or MIT); or code under Apache-2.0/MIT and skills + docs under CC BY 4.0 | No LICENSE file was added: a public repo without one is "all rights reserved". Two constraints: `packs/felid/skull/` derives from a CC BY-SA 4.0 photo (ShareAlike may bind that data), and `references/illustrations/` are AI-made (Grok) - check the generator's terms. |
| D2 | **Repo and marketplace names** | one repo = one marketplace with all plugins (as scaffolded); or one repo per plugin plus a marketplace repo that points at them (`github` sources) | Working name `self-improving-engines` (folder, marketplace `name`). Plugin names may not start with `claude-`/`anthropic-`. One repo is simpler until there are several engines with separate release cycles. |
| D3 | **Versioning** | (a) `version` in each plugin.json, bumped per release (set now: 0.1.0, reporter 0.0.1); (b) no `version`, users track commits | Claude Code keeps users on a pinned version until it changes, which fits "I review and publish updates". Suggestion: (a), semver per plugin, tags `<plugin>-vX.Y.Z`, a CHANGELOG entry naming each lesson's flag and default. Also: the lesson schema's version rule (SPEC 5). |
| D4 | **Transport** | D manual attach / B issue from the user's account / A PR from the user's account / C relay bot | SPEC 8. Own-account PRs and issues make the reporter's GitHub identity public; a relay hides it but is a service to run and defend. Suggestion: D now, then B or A; C only if anonymity matters to users. |
| D5 | **Are reports public?** | public repo (reports visible to all) / reports to a private intake repo, published only after rewrite | Affects D4 and what users are told before they approve. |
| D6 | **Default of a merged lesson** | arrives OFF (trial) and is switched ON in a later release / maintainer decides per lesson | Reported lessons always arrive with `default: false`; the merged default is the maintainer's call. |
| D7 | **Binary packs** (93 MB, `skull.npz` 69 MB) | Git LFS / release assets downloaded on demand / regenerate from JSON | Kept out of git for now (`plugins/asset-enhancement-engine/BINARIES.md`). Every install would carry them. |
| D8 | **`engine-proof` / `generative-pipeline`** | package them too / point recursive-improvement's Round 0 at engine-grounding | recursive-improvement names them; they are not in this marketplace. |
| D9 | **Opt-in mechanism for the reporter** | settings file in the plugin's data folder + console code (built) / Claude Code `userConfig` boolean (prompted in `/plugin`) | userConfig is a UI the user drives, but a value in settings.json is also just a file; the console code is the stronger human check. |
| D10 | **Repo location** | keep it in OneDrive next to the project (as asked) / move to a non-synced folder | OneDrive syncing a `.git` folder can lock files or conflict during commits; fine for a small repo, worth moving before heavy use. |
| D11 | **Publishing personal content** | publish the method logs as they are / paraphrase / keep some private | The skills and logs quote the person and name the case (`cat1`); `NOTES_LEDGER.md` is the person's own notes. |
