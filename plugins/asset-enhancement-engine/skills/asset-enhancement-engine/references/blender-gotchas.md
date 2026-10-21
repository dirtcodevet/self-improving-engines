# Blender / tooling gotchas met while building (each cost at least one failed run)

| Symptom | Cause | Fix |
|---|---|---|
| QuadriFlow: "mesh needs to be manifold" on a manifold mesh | real-world scale: sub-mm edges in metres | scale x100, remesh, scale back - but prefer voxel remesh + decimate for thin parts |
| QuadriFlow output loses an ear | quad size > thin-part thickness | fidelity check vs the hi-res surface; use voxel+decimate |
| Silhouette IoU changes with raster resolution (0.78 -> 0.47) | `cv2.fillPoly(list_of_tris)` uses even-odd fill | per-triangle `cv2.fillConvexPoly` |
| Render shows a ghost rest-pose head | a tool restored an object's `hide_render` to a default, not its prior value | save/restore exact state of everything touched |
| Copied object invisible in render | `obj.copy()` inherits `hide_render` from earlier runs | set visibility explicitly after copying |
| `NoneType has no attribute hide_render` iterating a collection | transient `None` entries after deletions in the same session | filter `None` |
| Material vanished (teeth) | `orphans_purge` deletes not-yet-assigned materials | `use_fake_user = True` for engine materials |
| Node link failed / index out of range (Blender 5) | type-dependent sockets on Random Value / Compare | pick sockets by `enabled and type`, never by index |
| `bpy_struct[key] = val: id properties not supported` on a GN modifier | Blender 5 modifier inputs are not ID props | set the interface socket's `default_value` |
| Half-built node group reused after a failed run (all fur deleted) | "get or create" reused a stale datablock | always rebuild generated datablocks |
| Eyes at the world origin after rigging | `matrix_world` set before the new armature's pose evaluated | explicit bone-tail `matrix_parent_inverse` from landmarks |
| Eyes off after re-import | importer set `location` in bone space of an old rig | clear parent before placing |
| Probe landmarks off by 12 px | animation active: frame 1 is posed | `pose_position = 'REST'` while scoring |
| EEVEE fur dark grey, eyes black | Principled Hair / transmissive cornea unsupported | separate EEVEE material outputs; render hero/anim in Cycles |
| Build script continued after a Python error | `set -e` + pipe to grep | `set -eo pipefail` |
| Undo stack ate 6 GB | full mesh copies per operator | cap undo memory, checkpoint, purge |
| Close-up camera renders an empty frame | camera nearer than the default clip_start (0.1 m) | `views.py` sets `clip_start = min(0.1, size*0.2)` |
| Edited shared module has no effect in Blender | Blender keeps imported modules for the session | `import mouth_geom as MG; importlib.reload(MG)`; `build_all.sh run()` puts `engine/tools` on `sys.path` |
| A script's saved-state tuple overwritten by an exec'd tool | tools exec'd into the same globals reuse names (`saved`) | prefix caller-side state (`_my_saved`) |

## Two Blenders at once (woman2, 2026-10-19)
- The Blender MCP add-on binds its port with SO_REUSEADDR and auto-starts on 9876 whenever it registers at startup.
  On Windows a second Blender started normally can share 9876 with the first, and commands then reach either one.
  Start a second Blender with `blender --factory-startup --python engine/tools/blender_second.py -- <port> <name>`
  and talk to it with `BMCP_PORT=<port> python engine/tools/bmcp.py ...`; every Blender-side payload for that case
  first asserts `bpy.app.driver_namespace.get("bmcp_instance") == "<name>"`.
- Rigify in Blender 5.2 registers properly only when enabled with `addon_utils.enable("rigify", default_set=True)`.
  With `default_set=False` its `register()` fails on the missing preferences entry, leaving its rig parameters
  unregistered. Generation then fails with "'RigifyParameters' object has no attribute ...". Re-enabling in the same
  session doesn't recover it: restart Blender. A second Blender started with `blender_second.py` never saves
  preferences, so `default_set=True` is safe there. Don't pin `active_object` in a context override around
  `rigify_generate`: Rigify makes its new rig active itself and asserts that it is.
- Transforming every edit bone in one loop (`b.head = f(b.head); b.tail = f(b.tail)`) applies the transform more than
  once to connected chains. Setting a parent's tail also moves its connected child's head, which the loop then
  transforms again. A Rigify metarig fitted this way had its spine and legs metres off the body (woman2 rig test,
  2026-10-20). Read all heads and tails first, then write them.

## Vendored add-ons (woman2 build 15, 2026-10-21; `engine/tools/vendor.py`)
- Load them only through `vendor.enable(name)` in `blender -b --factory-startup`: it refuses any other session, so the
  live Blenders and the person's preferences and add-on list stay unchanged (checked: userpref.blend untouched).
- Pose Shape Keys' auto driver (`posekey_magic_driver`) builds its ramps from the pose's Euler values but reads
  swing-twist channels. On a 115 deg compound arm raise the twist read -0.19 rad where the ramp expected +0.41, so the
  key stayed at 0 in the pose. Write the driver yourself (e.g. on the arm's angle from rest); the Push itself is exact.
- Robust Weight Transfer accepts flipped normals as matches by default (`flip_vertex_normal`, for open or inverted
  meshes). On a closed skin that lets a vertex take the weights of the facing sheet of a fold (v12's armpit slit gave
  0 / 1 / 0 on one triangle). Set it False on our skins. Its inpainting also leaves weight sums off 1 (up to 0.08).
