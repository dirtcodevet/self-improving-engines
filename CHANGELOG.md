# Changelog

Versions are per plugin (`plugins/*/.claude-plugin/plugin.json`). Lessons on trial are listed with their flag.

## 0.2.0 (2026-10-21): first public release

- **License.** Apache-2.0 (`LICENSE`); third-party pieces keep their own terms (`NOTICE`).
- **The engine is now `asset-enhancement-engine`** (it was `photo-to-blender-creature`). If you installed the old
  name, install the new one.
- **The Translator** works on any object (a dragon, a brick, a street lantern, a whole human body), with a page on how
  to open it, move around, and pick and send spots.
- **Published copies are cleaned on the way out:** personal folder paths and the project layout's skill paths are
  rewritten (`tools/publish_rules.json`, "rewrite").
- **Repo generalized.** The repo now holds the skills, the tools and the foundation (domain packs, references,
  checks), not the samples, case work and run logs. `tools/publish_rules.json` says what is published, and
  `tools/refresh_copies.py` applies it on every refresh. The unreviewed cat-rebuild tools left the repo.
- **New pages.** A landing page, one page per plugin, and a page for the Translator, with images and diagrams.
- **Asset enhancement engine.** Reframed as 3-D asset enhancement (it starts from a 3-D asset). Adds the Translator (`tools/part_frame.py`, `tools/part_frame_view.html`), the target loop (`loop/`), pose-study tools, and a
  loader for optional third-party tools (`tools/vendor.py`, [VENDOR.md](plugins/asset-enhancement-engine/VENDOR.md)).
- **Recursive improvement.** Additions A19–A29 on trial (flags in `flags.json`).
- **Engine grounding.** G13 (approved work is protected) and G14 (case values live in the case's files) on trial.

## 0.1.0 (2026-10-18)

- First private snapshot: recursive-improvement (A1–A18), engine-grounding (G1–G12), the cat engine, and the
  lesson reporter prototype (0.0.1, off by default).
