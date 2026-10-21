# Security

Please report security problems privately to [@dirtcodevet](https://github.com/dirtcodevet) through GitHub's
private vulnerability reporting on this repo, not in a public issue.

Worth knowing:

- **The lesson reporter** is off by default and makes no network calls. Turning it on for an engine, and
  approving a package, both need the person at their own console; an agent's shell cannot do either. Its threat
  model is in [docs/lesson-reporter/SPEC.md](docs/lesson-reporter/SPEC.md).
- **The engine can call outside services.** Two tools upload a photo to hosted 3-D generators
  (`tools/trellis_space.py`, `tools/rodin_ref.py`), and one downloads reference photos (`tools/fetch_refs.py`).
  The engine's skill requires the person's consent before any upload.
- **Third-party Blender add-ons** the engine can load are not shipped here and load only in a Blender started with
  `-b --factory-startup`, so your own Blender setup is never changed ([VENDOR.md](plugins/asset-enhancement-engine/VENDOR.md)).
