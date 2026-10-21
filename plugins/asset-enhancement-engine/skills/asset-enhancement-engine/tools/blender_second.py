"""Blender-side launcher: run the Blender MCP add-on on its OWN port in a second Blender, so a second case can be
built and shown live beside the first without sharing its scene, save file, view or undo (woman2, 2026-10-19).

  blender --factory-startup --python engine/tools/blender_second.py -- <port> <instance>
  then: BMCP_PORT=<port> python engine/tools/bmcp.py ping

Why it exists: the add-on auto-starts its server on 9876 whenever it registers at startup, and it binds with
SO_REUSEADDR, which on Windows lets a second Blender share 9876 with the first; commands then land in either one.
--factory-startup keeps the user's add-ons off, so that auto-start never runs. This file imports the add-on by path,
pre-sets its server on <port> and registers it. It marks the instance in bpy.app.driver_namespace['bmcp_instance']:
every Blender-side script for that case asserts the mark first, so a command sent to the wrong port fails instead of
editing the other scene. It turns preference auto-save off first, so this window never writes the user's preferences.
"""
import importlib.util
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
port, name = int(argv[0]), argv[1]
assert port != 9876, "9876 belongs to the first Blender"

prefs = bpy.context.preferences
prefs.use_preferences_save = False          # first: nothing below may reach the user's userpref.blend
prefs.edit.undo_steps = 16                  # 16 GB machine (feedback: cap undo, autosave)
prefs.filepaths.use_auto_save_temporary_files = True
prefs.filepaths.auto_save_time = 2

path = os.path.join(bpy.utils.resource_path('USER'), "scripts", "addons", "blender_mcp.py")
spec = importlib.util.spec_from_file_location("blender_mcp", path)
mod = importlib.util.module_from_spec(spec)
sys.modules["blender_mcp"] = mod
spec.loader.exec_module(mod)
bpy.types.blendermcp_server = mod.BlenderMCPServer(port=port)   # register() reuses a server that already exists
mod.register()
if not bpy.types.blendermcp_server.running:
    bpy.types.blendermcp_server.start()
bpy.context.scene.blendermcp_port = port
bpy.app.driver_namespace["bmcp_instance"] = name
print(f"blender_second: '{name}' on port {port}, running={bpy.types.blendermcp_server.running}")
