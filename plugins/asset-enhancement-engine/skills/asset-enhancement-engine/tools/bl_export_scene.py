"""BLENDER-SIDE (background): every mesh object of a file Blender can open or import, evaluated (modifiers applied), in
world coordinates, merged into one npz for engine/tools/language.py (build L1, 2026-10-21: the language tool ingests
formats numpy does not read). Per triangle: the index of its object and of its material, with their names (an
object's own parts - eyes, teeth, wings modelled as separate objects - become the language tool's file labels).

Usage:
  blender -b --factory-startup --python bl_export_scene.py -- MODEL OUT.npz
MODEL: .blend (opened), .glb / .gltf / .fbx / .obj / .dae / .stl / .ply / .abc / .usd* (imported into an empty scene).
Writes: v (float64, metres as the file has them), f (int32 triangles), face_object, object_names, face_material,
material_names, colour (per vertex, when the mesh has a colour attribute), note. Reads the file, never saves it.
"""
import os
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(a[0]), os.path.abspath(a[1])
ext = os.path.splitext(SRC)[1].lower()
if ext == ".blend":
    bpy.ops.wm.open_mainfile(filepath=SRC)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    imp = {".glb": lambda p: bpy.ops.import_scene.gltf(filepath=p), ".gltf": lambda p: bpy.ops.import_scene.gltf(filepath=p),
           ".fbx": lambda p: bpy.ops.import_scene.fbx(filepath=p), ".obj": lambda p: bpy.ops.wm.obj_import(filepath=p),
           ".dae": lambda p: bpy.ops.wm.collada_import(filepath=p), ".stl": lambda p: bpy.ops.wm.stl_import(filepath=p),
           ".ply": lambda p: bpy.ops.wm.ply_import(filepath=p), ".abc": lambda p: bpy.ops.wm.alembic_import(filepath=p),
           ".usd": lambda p: bpy.ops.wm.usd_import(filepath=p), ".usdz": lambda p: bpy.ops.wm.usd_import(filepath=p),
           ".usdc": lambda p: bpy.ops.wm.usd_import(filepath=p), ".usda": lambda p: bpy.ops.wm.usd_import(filepath=p)}
    if ext not in imp:
        raise SystemExit(f"bl_export_scene: no importer for {ext}")
    imp[ext](SRC)
dg = bpy.context.evaluated_depsgraph_get()
Vs, Fs, fo, fm, cols, onames, mnames = [], [], [], [], [], [], []
off = 0
for ob in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    oe = ob.evaluated_get(dg); me = oe.to_mesh()
    n = len(me.vertices)
    if n == 0:
        oe.to_mesh_clear(); continue
    v = np.empty(n * 3, np.float64); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
    M = np.array(ob.matrix_world); v = v @ M[:3, :3].T + M[:3, 3]
    me.calc_loop_triangles(); nt = len(me.loop_triangles)
    tri = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
    mat = np.empty(nt, np.int32); me.loop_triangles.foreach_get("material_index", mat)
    names = [s.material.name if s.material else "(none)" for s in ob.material_slots] or ["(none)"]
    gm = [mnames.index(nm) if nm in mnames else (mnames.append(nm) or len(mnames) - 1) for nm in names]
    c = np.full((n, 3), np.nan, np.float32)
    ca = me.color_attributes.active_color if hasattr(me, "color_attributes") else None
    if ca is not None and ca.domain == 'POINT':
        cc = np.empty(n * 4, np.float32); ca.data.foreach_get("color", cc); c = cc.reshape(-1, 4)[:, :3]
    Vs.append(v); Fs.append(tri.reshape(-1, 3) + off); fo += [len(onames)] * nt
    fm += [gm[min(i, len(gm) - 1)] for i in mat]; cols.append(c); onames.append(ob.name); off += n
    oe.to_mesh_clear()
if not Vs:
    raise SystemExit("bl_export_scene: no mesh objects")
out = {"v": np.concatenate(Vs), "f": np.concatenate(Fs).astype(np.int32), "face_object": np.array(fo, np.int32),
       "object_names": np.array(onames), "face_material": np.array(fm, np.int32), "material_names": np.array(mnames),
       "note": np.array(f"{SRC}: {len(onames)} mesh objects, evaluated, world coordinates (bl_export_scene.py)")}
C = np.concatenate(cols)
if np.isfinite(C).all():
    out["colour"] = C
np.savez_compressed(OUT, **out)
print("EXPORTED", len(onames), "objects", off, "vertices ->", OUT)
