# Publishing checklist (maintainer)

The repo went public on 2026-10-21 (release v0.2.0). This list records what was settled before that and what is
still open. Open decisions are in [DECISIONS.md](DECISIONS.md).

| # | Item | State |
|---|---|---|
| 1 | **License** (D1). Without one, a public repo is "all rights reserved". | done 2026-10-21: Apache-2.0 (`LICENSE`, `NOTICE`, every plugin manifest) |
| 2 | **Personal content** (D11). The skills and `log/METHOD.md` quote the maintainer and name the test cases (`cat1`, `woman2`). Keep, paraphrase, or keep some private. | done 2026-10-21: quotes and case names kept; folder paths and the other project's name rewritten on publish |
| 3 | **Path references.** The engine's `SKILL.md` points at `../skills/recursive-improvement/` and `../skills/engine-grounding/` (the project layout); in a plugin install those are separate plugins. `references/builder-primer.md` names the project folder's absolute path. Four absolute paths remain in the copies in all. | done 2026-10-21: rewritten on publish |
| 4 | **Uploading tools.** `tools/trellis_space.py` uploads a photo to a hosted TRELLIS space and `tools/rodin_ref.py` to Hyper3D Rodin; `tools/fetch_refs.py` downloads reference photos. For other users they must stay behind explicit per-use consent (the skill says so; consider an off-by-default flag too). | met: the skill's rule and each tool's own note require approval per use; a code switch stays optional |
| 5 | **Third-party material.** `references/illustrations/` are AI-made (Grok) cards; check the generator's terms. `packs/felid/skull/` derives from a CC BY-SA 4.0 photo (its binaries are not committed). The images in `docs/images/` are the project's own renders and screenshots; the cat reference image is AI-made (Grok). | done 2026-10-21: listed in `NOTICE` |
| 6 | **Binary packs** (D7): Git LFS, release assets, or regenerate. `BINARIES.md` lists them. | deferred: not in the first public release; ship as release assets once the MakeHuman data's licence is checked |
| 7 | **Public proof fixtures.** The checks' proofs need builds made from the private cases (`proofs.json`). | deferred: `proofs.json` says so; public fixtures come later |
| 8 | **Generalized contents.** Samples, case work, run logs and the unreviewed cat-rebuild tools are out; `tools/publish_rules.json` keeps them out on every refresh. | done 2026-10-21 |
| 9 | **Engine name.** The plugin id is still `asset-enhancement-engine`; the pages call it the asset enhancement engine. | done 2026-10-21: published as `asset-enhancement-engine` |
| 10 | **Sponsor button.** `.github/FUNDING.yml` is in place but commented out until a GitHub Sponsors profile exists. | open |
| 11 | **Git history.** The commits pushed on 2026-10-18 still hold `log/NOTES_LEDGER.md` (the maintainer's own notes) and the unreviewed cat-rebuild tools, which the current tree no longer has. Before going public, publish from a fresh history or rewrite it. | done 2026-10-21: this repo starts from one fresh commit; the old one is private as `self-improving-engines-archive` |

## Release steps (fresh history), done 2026-10-21

Decided 2026-10-21: the public repo starts from one clean commit in a new repository, so the old history (with
`log/NOTES_LEDGER.md` and the unreviewed cat-rebuild tools) is never public.

1. Locally, an orphan branch `public` holds today's tree as its only commit ("First public release"), authored with
   the maintainer's GitHub no-reply address.
2. One check of that tree: no personal paths, notes ledger or binaries; the marketplace validates; the reporter's
   tests pass.
3. On the maintainer's go: rename `dirtcodevet/self-improving-engines` to `self-improving-engines-archive`. It stays
   private, full history intact.
4. Create a new public `dirtcodevet/self-improving-engines`, push `public` as its `main`, and set the description
   and topics. The install line stays the same.
5. Tag `v0.2.0` (the first public release; `CHANGELOG.md`) and publish a GitHub release (no binaries yet, item 6).
6. Locally, `origin` points at the new repo and `archive` at the old one. `main` follows the public history from
   then on; the old history stays on `archive-main`.
