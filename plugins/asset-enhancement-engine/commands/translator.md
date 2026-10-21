---
description: Open the Translator - your model broken into parts, ready to pick the spots you mean and send them to your AI
argument-hint: "[a model file, or the name of a model or part you've opened before, e.g. \"brick\" or \"left hand\"]"
---
Open the Translator for the person, fast, and do nothing else.

The engine's tools are in this plugin's skill folder: `skills/asset-enhancement-engine/` inside the plugin's install
folder (`${CLAUDE_PLUGIN_ROOT}`). Keep the Translator's pages in a folder of the person's own: pass `--home <folder>`
(or set `TRANSLATOR_HOME`), for example a `translator` folder in the current project, so they don't land inside the
plugin's install folder.

1. If "$ARGUMENTS" is a 3-D model (`.glb .gltf .fbx .blend .obj .ply .stl .dae`) or a picture (`.png .jpg`) with no
   Translator pages yet, make them and open them:
   `python "<skill folder>/tools/language.py" auto "<the file>" --case "<home>/<a name for it>" --pack <kind> --open`
   with `--pack generic` unless the model is a person (`human`), a creature (`creature`) or masonry (`masonry`). Formats
   other than `.obj .ply .stl` and pictures are read through Blender, which must be installed.
2. Otherwise run `python "<skill folder>/tools/language.py" open "$ARGUMENTS" --home "<home>"`. With nothing after
   `open` it opens the Translator's home page, which lists every model; a name like "brick" or "left hand" opens that
   view. In the Claude desktop app, open the printed page in the built-in browser instead (add `--print` to get its
   `url`).
3. Reply in one line: what's open and where it lives on disk.
