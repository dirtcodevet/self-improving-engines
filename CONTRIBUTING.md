# Contributing

Thanks for your interest. This repo packages skills and an engine that are developed in a separate working
project and copied here, so contributions work a little differently from a typical code repo.

## Ways to help

- **Report a problem** with a skill, a tool or a page: open an issue with what you ran, what you expected, and what
  happened. For the engine, include your Blender and Python versions.
- **Share a lesson.** If running an engine taught you something general (a check that caught a defect, a measure
  that misled, a step that wasted time), open an issue with the evidence. Lessons enter a skill only with cited
  evidence and the maintainer's approval, and they arrive switched off, on trial, with a flag in `flags.json`.
- **Propose a tool or a fix.** Pull requests are welcome for `tools/` in this repo and for the engine's `tools/`,
  `checks/` and `loop/`. A new or changed tool needs a short proof that it works (for a check, a planted copy of the
  defect it exists to catch) and a docstring that says why it exists.

## What we keep to

- **Measure before asserting.** A claim about a model comes with its measurement.
- **Checks only tighten.** Removing a check, loosening a threshold or changing a weight needs the maintainer's
  approval (the ratchet).
- **No case facts in engine code.** Values that belong to one subject live in that subject's case files; what is
  particular to a kind of object lives in a data pack.
- **Every process change is switchable.** A new lesson comes with its flag and its rollback.

## Copies and sources

The skill folders under `plugins/*/skills/` are byte-identical copies of the working project. `SOURCES.json`
records each copy's hash, `tools/verify_copies.py` proves the copies still match, and `tools/publish_rules.json`
says what is published. A pull request against a copied file is folded back into the project first, then copied
here again.

By contributing you agree that your contribution is published under the repo's license, [Apache-2.0](LICENSE).
