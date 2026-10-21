"""BLENDER-SIDE (background): export one mesh object's EVALUATED geometry (modifiers applied, e.g. a multires sculpt at
a chosen level) to an npz that numpy tools read without Blender. Created 2026-10-20 (woman2 build 09, part frames:
the hand comes from a .blend whose sculpt detail lives in a multires modifier, so the base mesh alone is not the form).

Usage:
  blender -b --factory-startup FILE.blend --python bl_export_mesh.py -- OBJECT OUT.npz [LEVEL] [world|local]
LEVEL: multires level to evaluate (default: the modifier's render level). world|local: coordinates in the world or the
object's own frame (default local: the object's origin and axes, so a body laid out beside others keeps its midline).
Writes: v (float32, n x 3, metres), f (int32, triangles; n-gons fan-triangulated by Blender's loop triangles),
f_poly (int32, the source polygon of each triangle), face_set (int32 per triangle, when the mesh has sculpt face sets),
note (what, from where, level, frame). Reads the file, never saves it.
"""
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
OBJ, OUT = a[0], a[1]
LEVEL = int(a[2]) if len(a) > 2 and a[2] not in ("", "-") else None
FRAME = a[3] if len(a) > 3 else "local"

ob = bpy.data.objects[OBJ]
lv = None
for m in ob.modifiers:
    if m.type == 'MULTIRES':
        lv = m.render_levels if LEVEL is None else min(LEVEL, m.total_levels)
        m.levels = m.sculpt_levels = m.render_levels = lv
    elif m.type == 'SUBSURF' and LEVEL is not None:
        m.levels = m.render_levels = LEVEL
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
oe = ob.evaluated_get(dg)
me = oe.to_mesh()
n = len(me.vertices)
v = np.empty(n * 3, np.float64); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
if FRAME == "world":
    M = np.array(ob.matrix_world)
    v = v @ M[:3, :3].T + M[:3, 3]
me.calc_loop_triangles()
nt = len(me.loop_triangles)
tri = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
poly = np.empty(nt, np.int32); me.loop_triangles.foreach_get("polygon_index", poly)
out = {"v": v.astype(np.float32), "f": tri.reshape(-1, 3), "f_poly": poly}
fs = me.attributes.get(".sculpt_face_set")
if fs is not None and fs.domain == 'FACE':
    s = np.empty(len(me.polygons), np.int32); fs.data.foreach_get("value", s); out["face_set"] = s[poly]
out["note"] = np.array(f"{bpy.data.filepath} :: {OBJ}, evaluated (multires level {lv}), {FRAME} coordinates, metres; "
                       f"{n} vertices, {nt} triangles (bl_export_mesh.py)")
oe.to_mesh_clear()
np.savez_compressed(OUT, **out)
print("EXPORTED", OBJ, n, "verts", nt, "tris ->", OUT)
