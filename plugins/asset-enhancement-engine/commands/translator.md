---
description: Open the Translator - your model broken into parts, ready to pick the spots you mean and send them to your AI
argument-hint: "[a model file, or the name of one you've opened before]"
---
Open the Translator for the person, fast, and do nothing else.

The engine's tools are in this plugin's skill folder: `skills/asset-enhancement-engine/` inside the plugin's install
folder (`${CLAUDE_PLUGIN_ROOT}`). Each model's Translator pages live in a `language/` folder in that model's case
folder: `object.html` (the whole model, coloured by part), `index.html` (its list of parts) and one page per part.
The pages open straight from disk; no server is needed.

1. If "$ARGUMENTS" is a 3-D model (`.glb .gltf .fbx .blend .obj .ply .stl .dae`) or a picture (`.png .jpg`) that has
   no Translator pages yet, make them:
   `python "<skill folder>/tools/language.py" auto "<the file>" --case "<full path of a new folder next to the file, named after it>" --pack <kind>`
   with `--pack generic` unless the model is a creature (`creature`) or masonry (`masonry`). Give `--case` as a full
   path. Formats other than `.obj .ply .stl` and pictures are read through Blender, which must be installed.
2. Otherwise find the existing pages: `language/` folders holding an `object.html` or `index.html` under the current
   project. Pick the one that best matches "$ARGUMENTS", or the newest when it's empty.
3. Open its `object.html`, or its `index.html` when there's no whole model: in the Claude desktop app's built-in
   browser when it has one, otherwise in the person's browser with `python -m webbrowser -t "file:///<full path>"`.
4. Reply in one line: what's open and where it lives on disk.
